#! /usr/bin/env python3
# coding: utf-8
# Copyright (c) 2020 oatsu
"""
1. UTAUプラグインのテキストファイルを読み取る。
  - 音源のフォルダを特定する。
  - プロジェクトもしくはUSTファイルのパスを特定する。
2. LABファイルを(一時的に)生成する
  - キャッシュフォルダでいいと思う。
3. LABファイル→WAVファイル
"""
from copy import deepcopy
from datetime import datetime
from os import chdir, makedirs, startfile
from os.path import exists, join, splitext
from sys import argv
from tempfile import mkdtemp

import utaupy as up
from omegaconf import DictConfig, OmegaConf
from utaupy.utils import hts2json, ustobj2songobj

try:
    from hts2wav import hts2wav
except ModuleNotFoundError:
    print('\n----------------------------------------------------------')
    print('初回起動ですね。')
    print('PC環境に合わせてPyTorchを自動インストールします。')
    print('インストール完了までしばらくお待ちください。')
    print('----------------------------------------------------------')
    from install_torch import pip_install_torch
    pip_install_torch(join('.', 'python-3.8.10-embed-amd64', 'python.exe'))
    print('----------------------------------------------------------')
    print('インストール成功しました。歌声合成を始めます。')
    print('----------------------------------------------------------\n')
    from hts2wav import hts2wav  # pylint: disable=ungrouped-imports


def get_project_path(utauplugin: up.utauplugin.UtauPlugin):
    """
    キャッシュパスとプロジェクトパスを取得する。
    """
    setting = utauplugin.setting
    # ustのパス
    path_ust = setting.get('Project')
    # 音源フォルダ
    voice_dir = setting['VoiceDir']
    # 音声キャッシュのフォルダ(LABとJSONを設置する)
    cache_dir = setting['CacheDir']

    return path_ust, voice_dir, cache_dir


def utauplugin2hts(path_plugin_in, path_table, path_full_out, path_mono_out=None,
                   strict_sinsy_style=False):
    """
    USTじゃなくてUTAUプラグイン用に最適化する。
    ust2hts.py 中の ust2hts を改変して、
    [#PREV] と [#NEXT] に対応させている。
    """
    # プラグイン用一時ファイルを読み取る
    plugin = up.utauplugin.load(path_plugin_in)
    # 変換テーブルを読み取る
    table = up.table.load(path_table, encoding='utf-8')

    # 2ノート以上選択されているかチェックする
    if len(plugin.notes) < 2:
        raise Exception('ENUNU requires at least 2 notes. / ENUNUを使うときは2ノート以上選択してください。')

    # 歌詞が無いか空白のノートを休符にする。
    for note in plugin.notes:
        if note.lyric.strip(' 　') == '':
            note.lyric = 'R'

    # [#PREV] や [#NEXT] が含まれているか判定
    prev_exists = not plugin.previous_note is None
    next_exists = not plugin.next_note is None
    if prev_exists:
        plugin.notes.insert(0, plugin.previous_note)
    if next_exists:
        plugin.notes.append(plugin.next_note)

    # Ust → HTSFullLabel
    song = ustobj2songobj(plugin, table)
    full_label = up.hts.HTSFullLabel()
    full_label.song = song
    full_label.fill_contexts_from_songobj()

    # [#PREV] と [#NEXT] を消す前の状態での休符周辺のコンテキストを調整する
    if prev_exists or next_exists:
        full_label = up.hts.adjust_pau_contexts(full_label, strict=strict_sinsy_style)

    # [#PREV] のノート(の情報がある行)を削る
    if prev_exists:
        target_note = full_label[0].note
        while full_label[0].note is target_note:
            del full_label[0]
        # PREVを消しても前のノート分ずれているので、最初の音素開始時刻が0になるようにする。
        # ずれを取得
        offset = full_label[0].start
        # 全音素の開始と終了時刻をずらす
        for oneline in full_label:
            oneline.start -= offset
            oneline.end -= offset
    # [#NEXT] のノート(の情報がある行)を削る
    if next_exists:
        target_note = full_label[-1].note
        while full_label[-1].note is target_note:
            del full_label[-1]

    # ファイル出力
    s = '\n'.join(list(map(str, full_label)))
    with open(path_full_out, mode='w', encoding='utf-8') as f:
        f.write(s)
    if path_mono_out is not None:
        full_label.as_mono().write(path_mono_out)


def main_as_plugin(path_plugin: str) -> str:
    """
    UtauPluginオブジェクトから音声ファイルを作る
    """
    print(f'{datetime.now()} : reading setting in ust')
    # UTAUの一時ファイルに書いてある設定を読み取る
    plugin = up.utauplugin.load(path_plugin)
    path_ust, voice_dir, _ = get_project_path(plugin)

    path_enuconfig = join(voice_dir, 'enuconfig.yaml')
    if not exists(path_enuconfig):
        raise Exception(
            '音源フォルダに enuconfig.yaml が見つかりません。'
            'UTAUの音源設定でENUNU用モデルを指定してください。'
        )

    # カレントディレクトリを音源フォルダに変更する
    chdir(voice_dir)
    # configファイルを読み取る
    print(f'{datetime.now()} : reading enuconfig')
    config = DictConfig(OmegaConf.load(path_enuconfig))

    # 入出力パスを設定する
    if path_ust is not None:
        songname = f"{splitext(path_ust)[0]}__{datetime.now().strftime('%Y%m%d%H%M%S')}"
        out_dir = songname
    # USTが未保存の場合
    else:
        print('USTが保存されていないので一時フォルダにWAV出力します。')
        songname = f"temp__{datetime.now().strftime('%Y%m%d%H%M%S')}"
        out_dir = mkdtemp(prefix='enunu')

    # 出力フォルダがなければつくる
    makedirs(out_dir, exist_ok=True)

    # 各種出力ファイルのパスを設定
    path_full_score_lab = join(out_dir, f'{songname}_full_score.lab')
    path_mono_score_lab = join(out_dir, f'{songname}_mono_score.lab')
    path_json = join(out_dir, f'{songname}_full_score.json')
    path_wav = join(out_dir, f'{songname}.wav')
    path_ust_out = join(out_dir, f'{songname}.ust')

    # フルラベル生成
    print(f'{datetime.now()} : converting TMP to LAB')
    utauplugin2hts(
        path_plugin,
        config.table_path,
        path_full_score_lab,
        path_mono_out=path_mono_score_lab,
        strict_sinsy_style=(not config.trained_for_enunu)
    )

    # ファイル処理
    # 選択範囲のUSTを出力(musicxml用)
    print(f'{datetime.now()} : exporting UST')
    new_ust = deepcopy(plugin)
    for note in new_ust.notes:
        # 基本情報以外を削除
        note.suppin()
        # 歌詞がないノートを休符にする
        if note.lyric.strip(' 　') == '':
            note.lyric = 'R'
    new_ust.write(path_ust_out)

    print(f'{datetime.now()} : converting LAB to JSON')
    hts2json(path_full_score_lab, path_json)
    print(f'{datetime.now()} : converting LAB to WAV')
    hts2wav(config, path_full_score_lab, path_wav)
    print(f'{datetime.now()} : generating WAV ({path_wav})')
    # Windowsの時は音声を再生する。
    startfile(path_wav)

    return path_wav


def main(path: str):
    """
    入力ファイルによって処理を分岐する。
    """
    # logging.basicConfig(level=logging.INFO)
    if path.endswith('.tmp'):
        main_as_plugin(path)
    else:
        raise ValueError('Input file must be TMP(plugin).')


if __name__ == '__main__':
    print('_____ξ ・ヮ・)ξ < ENUNU v0.2.3 ________')
    print(f'argv: {argv}')
    if len(argv) == 2:
        path_utauplugin = argv[1]
    elif len(argv) == 1:
        path_utauplugin = \
            input('Input file path of TMP(plugin)\n>>> ').strip('"')
    main(path_utauplugin)
