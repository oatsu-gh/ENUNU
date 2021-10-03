#! /usr/bin/env python3
# coding: utf-8
# Copyright (c) 2020 oatsu
"""
フルラベルと、タイミング補正済みモノラベルからWAVファイルを生成する。
モデルは…？
"""
import logging
# from copy import deepcopy
from datetime import datetime
from os import chdir, makedirs, startfile
from os.path import basename, dirname, exists, join, splitext
from sys import argv
from tempfile import mkdtemp

import utaupy
from omegaconf import DictConfig, OmegaConf
from tqdm import tqdm
from utaupy.utils import hts2json, ustobj2songobj

try:
    from hts2wav import hts2wav
except ModuleNotFoundError:
    print('----------------------------------------------------------')
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


def get_project_path(utauplugin: utaupy.utauplugin.UtauPlugin):
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
    plugin = utaupy.utauplugin.load(path_plugin_in)
    # 変換テーブルを読み取る
    table = utaupy.table.load(path_table, encoding='utf-8')

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
    full_label = utaupy.hts.HTSFullLabel()
    full_label.song = song
    full_label.fill_contexts_from_songobj()

    # [#PREV] と [#NEXT] を消す前の状態での休符周辺のコンテキストを調整する
    if prev_exists or next_exists:
        full_label = utaupy.hts.adjust_pau_contexts(full_label, strict=strict_sinsy_style)

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


def repair_too_short_phoneme(label, threshold=5) -> None:
    """
    LABファイルの中の発声時刻が短すぎる音素(5ms未満の時とか)を修正する。
    直前の音素の長さを削る。
    一番最初の音素が短い場合のみ修正できない。
    """
    threshold_100ns = threshold * 10000
    # 短い音素が一つもない場合はスルー
    if all(phoneme.duration >= threshold_100ns for phoneme in label):
        return None
    # 短い音素が連続しても不具合が起こらないように逆向きにループする
    if label[0].duration < threshold_100ns:
        raise ValueError(f'最初の音素が短いです。修正できません。: {label[0]}')
    for i, phoneme in enumerate(reversed(label)):
        # 発声時間が閾値より短い場合
        if phoneme.duration < threshold_100ns:
            logging.warning('短い音素を修正します。: %s', phoneme)
            # 閾値との差分を計算する。この分だけずらす。
            delta_t = threshold_100ns - phoneme.duration
            # 対象の音素の開始時刻をずらして、発生時間を伸ばす。
            phoneme.start -= delta_t
            # 直前の音素の終了時刻もずらす。
            # label[-(i + 1) - 1]
            label[-i - 2].end -= delta_t
    return None


def generate_full_align_lab(path_mono_align_lab_in,
                            path_full_score_lab_in,
                            path_full_align_lab_out):
    """
    タイミング補正済みのものラベルと、
    タイミング補正前のフルラベルから、
    タイミング補正済みのフルラベルを作る。
    """
    mono_align_lab = utaupy.label.load(path_mono_align_lab_in)
    full_score_lab = utaupy.label.load(path_full_score_lab_in)
    mono_align_lab.is_valid(threshold=0)
    repair_too_short_phoneme(mono_align_lab)
    assert len(mono_align_lab) == len(full_score_lab)
    full_align_lab = utaupy.label.Label()
    # タイミング補正をフルラベルに適用したLabelオブジェクトを作る。ｓ
    for mono_align_phoneme, full_score_phoneme in zip(tqdm(mono_align_lab), full_score_lab):
        phoneme = utaupy.label.Phoneme()
        phoneme.start = mono_align_phoneme.start
        phoneme.end = mono_align_phoneme.end
        phoneme.symbol = full_score_phoneme.symbol
        full_align_lab.append(phoneme)
    # ファイル出力
    full_align_lab.write(path_full_align_lab_out)


def main_as_plugin(path_plugin: str) -> str:
    """
    UtauPluginオブジェクトから音声ファイルを作る
    """
    print(f'{datetime.now()} : reading setting in ust')
    # UTAUの一時ファイルに書いてある設定を読み取る
    plugin = utaupy.utauplugin.load(path_plugin)
    path_ust, voice_dir, _ = get_project_path(plugin)

    path_enuconfig = join(voice_dir, 'enuconfig.yaml')
    if not exists(path_enuconfig):
        raise Exception(
            '音源フォルダに enuconfig.yaml が見つかりません。'
            'UTAU音源選択でENUNU用モデルを指定してください。'
        )

    # NOTE: ここGTS追加機能
    path_mono_align_lab = input('タイミング補正済みの LABファイル (timing) を指定してください。\n>>> ')
    path_full_score_lab = input('タイミング補正前の LABファイル (full_score) を指定してください。\n>>> ')

    # カレントディレクトリを音源フォルダに変更する
    chdir(voice_dir)
    # configファイルを読み取る
    print(f'{datetime.now()} : reading enuconfig')
    config = DictConfig(OmegaConf.load(path_enuconfig))

    # 入出力パスを設定する
    str_now = datetime.now().strftime('%Y%m%d%H%M%S')
    if path_ust is not None:
        songname = f'{splitext(basename(path_ust))[0]}__{str_now}'
        out_dir = join(dirname(path_ust), songname)
    # USTが未保存の場合
    else:
        print('USTが保存されていないので一時フォルダにWAV出力します。')
        songname = f'temp__{str_now}'
        out_dir = mkdtemp(prefix='enunu-')

    # 出力フォルダがなければつくる
    makedirs(out_dir, exist_ok=True)

    # 各種出力ファイルのパスを設定
    path_full_align_lab = join(out_dir, f'{songname}_full_align.lab')
    # path_mono_score_lab = join(out_dir, f'{songname}_mono_score.lab')
    # path_json = join(out_dir, f'{songname}_full_score.json')
    path_wav = join(out_dir, f'{songname}.wav')
    # path_ust_out = join(out_dir, f'{songname}.ust')
    path_json = join(out_dir, f'{songname}_full_align.json')

    # TODO: ここ英語にする
    # NOTE: ここGTD追加機能
    # タイミング補正済みのフルラベルを生成
    print(f'{datetime.now()} : タイミング補正済みの LABファイル (full_align) を生成します。')
    generate_full_align_lab(path_mono_align_lab, path_full_score_lab, path_full_align_lab)
    config.ground_truth_duration = True

    print(f'{datetime.now()} : converting LAB (full_align) to JSON')
    hts2json(path_full_align_lab, path_json)
    print(f'{datetime.now()} : converting LAB (full_align) to WAV')
    hts2wav(config, path_full_align_lab, path_wav)
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
    print('_____ξ ・ヮ・)ξ < ENUNU v0.2.5 ________')
    print('_____ξ ＾ω＾)ξ < Ground Truth Duration (20211003-5) ________')
    print(f'argv: {argv}')
    if len(argv) == 2:
        path_utauplugin = argv[1]
    elif len(argv) == 1:
        path_utauplugin = \
            input('Input file path of TMP(plugin)\n>>> ').strip('"')
    main(path_utauplugin)
