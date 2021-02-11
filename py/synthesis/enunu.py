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

from datetime import datetime
from os import chdir, getcwd, makedirs
from os.path import relpath, splitdrive, splitext
# from os.path import abspath, dirname, exists
from subprocess import Popen
from sys import argv

import utaupy as up
from hydra.experimental import compose, initialize
from utaupy.utils import hts2json, ustobj2songobj

from hts2wav import hts2wav


def get_project_path(utauplugin: up.utauplugin.UtauPlugin):
    """
    キャッシュパスとプロジェクトパスを取得する。
    """
    # ustのパス
    path_ust = utauplugin.setting['Project']
    # 音源フォルダ
    voice_dir = utauplugin.setting['VoiceDir']
    # 音声キャッシュのフォルダ(LABとJSONを設置する)
    cache_dir = utauplugin.setting['CacheDir']

    return path_ust, voice_dir, cache_dir


def utauplugin2hts(path_plugin, path_hts, path_table, strict_sinsy_style=False):
    """
    USTじゃなくてUTAUプラグイン用に最適化する。
    ust2hts.py 中の ust2hts を改変して、
    [#PREV] と [#NEXT] に対応させている。
    """
    # 変換テーブルを読み取る
    table = up.table.load(path_table, encoding='utf-8')

    # プラグイン用一時ファイルを読み取る
    plugin = up.utauplugin.load(path_plugin)

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

    # デバッグ用
    # full_label.write(path_hts.replace('.lab', '途中.lab'),
    #                  encoding='utf-8',
    #                  strict_sinsy_style=strict_sinsy_style)
    # hts2json(path_hts.replace('.lab', '途中.lab'),
    #          path_hts.replace('.lab', '途中.json'))

    # [#PREV] と [#NEXT] を消す前の状態での休符周辺のコンテキストを調整する
    if any((prev_exists, next_exists)):
        full_label = up.hts.adjust_pau_contexts(full_label, strict=strict_sinsy_style)

    # [#PREV] のノート(の情報がある行)を削る
    if prev_exists:
        target_note = full_label[0].note
        while full_label[0].note is target_note:
            del full_label[0]
    # [#NEXT] のノート(の情報がある行)を削る
    if next_exists:
        target_note = full_label[-1].note
        while full_label[-1].note is target_note:
            del full_label[-1]

    # ファイル出力
    s = '\n'.join(list(map(str, full_label)))
    with open(path_hts, mode='w', encoding='utf-8') as f:
        f.write(s)


def main_as_plugin(path_plugin: str) -> str:
    """
    UtauPluginオブジェクトから音声ファイルを作る
    """
    print(f'{datetime.now()} : reading setting in ust')
    # UTAUの一時ファイルに書いてある設定を読み取って捨てる
    plugin = up.utauplugin.load(path_plugin)
    str_now = datetime.now().strftime('%Y%m%d%H%M%S')
    path_ust, voice_dir, cache_dir = get_project_path(plugin)
    del plugin

    print(f'{datetime.now()} : reading enuconfig')
    # 使用するモデルの設定
    enuconfig_name = 'enuconfig'
    # ドライブが違うとrelpathが使えないので、カレントディレクトリを変更する
    cwd = getcwd()
    if splitdrive(voice_dir)[0] != splitdrive(cwd)[0]:
        print(f'changed cwd :  {getcwd()} -> {voice_dir}')
        chdir(voice_dir)

    # configファイルを読み取る
    initialize(config_path=relpath(voice_dir))
    cfg = compose(config_name=enuconfig_name, overrides=[f'+config_path="{relpath(voice_dir)}"'])

    # 入出力パスを設定する
    path_lab = f'{cache_dir}/temp.lab'
    path_json = path_lab.replace('.lab', '.json')
    path_wav = f'{splitext(path_ust)[0]}__{str_now}.wav'.replace(' ', '_').replace('　', '_')
    # 変換テーブル(歌詞→音素)のパス
    path_table = f'{voice_dir}/{cfg.table_path}'

    # キャッシュフォルダがなければつくる
    makedirs(cache_dir, exist_ok=True)

    # ファイル処理
    strict_sinsy_style = not cfg.trained_for_enunu
    print(f'{datetime.now()} : converting TMP to LAB')
    utauplugin2hts(path_plugin, path_lab, path_table, strict_sinsy_style=strict_sinsy_style)
    print(f'{datetime.now()} : converting LAB to JSON')
    hts2json(path_lab, path_json)
    print(f'{datetime.now()} : converting LAB to WAV')
    hts2wav(cfg, path_lab, path_wav)
    print(f'{datetime.now()} : generated WAV ({path_wav})')
    # input('Press Enter.')
    Popen(['start', path_wav], shell=True)
    return path_wav


# def main_as_engine(path_tempbat: str) -> str:
#     """
#     UtauPluginオブジェクトから音声ファイルを作る
#     """
#     # temp.bat から ustファイルを生成する。
#     print(f'{datetime.now()} : converting BAT to UST')
#     temp_dir = dirname(abspath(path_tempbat))
#     path_ust = f'{temp_dir}/temp_enunu.ust'
#     path_lab = f'{temp_dir}/temp_enunu.lab'
#     path_json = f'{temp_dir}/temp_enunu.json'
#     bat2ust(path_tempbat, path_ust)
#
#     # 生成したustファイルから情報を取得して捨てる
#     print(f'{datetime.now()} : reading setting in ust')
#     ust = up.ust.load(path_ust)
#     voice_dir = ust.setting['VoiceDir']
#     path_wav = abspath(ust.setting['OutFile'])
#     del ust
#
#     # 使用するモデルの設定を取得する
#     print(f'{datetime.now()} : reading enuconfig')
#     enuconfig_name = 'enuconfig'
#     print(getcwd())
#     # ドライブが違うとrelpathが使えないので、カレントディレクトリを変更する
#     print(f'changed cwd :  {getcwd()} -> {voice_dir}')
#     chdir(voice_dir)
#
#     print(getcwd())
#     # configファイルを読み取る
#     print('voice_dir:', voice_dir)
#     print(exists(voice_dir))
#     print('voice_dir(rel):', relpath(voice_dir))
#     print(exists(relpath(voice_dir)))
#     initialize(config_path=relpath(voice_dir, getcwd()))
#     cfg = compose(config_name=enuconfig_name, overrides=[f'+config_path="{relpath(voice_dir)}"'])
#
#     # 変換の設定
#     path_table = f'{voice_dir}/{cfg.table_path}'
#     strict_sinsy_style = not cfg.trained_for_enunu
#     # ファイル処理
#     print(f'{datetime.now()} : converting UST to LAB')
#     ust2hts(path_ust, path_lab, path_table, strict_sinsy_style=strict_sinsy_style)
#     print(f'{datetime.now()} : converting LAB to JSON')
#     hts2json(path_lab, path_json)
#     print(f'{datetime.now()} : converting LAB to WAV')
#     hts2wav(cfg, path_lab, path_wav)
#     print(f'{datetime.now()} : generated WAV ({path_wav})')
#
#     # 一時ファイルを消す
#     remove(path_ust)
#     remove(path_lab)
#     remove(path_json)
#
#     return path_wav


def main(path: str):
    """
    入力ファイルによって処理を分岐する。
    """
    if path.endswith('.bat'):
        # main_as_engine(path)
        print('未実装です。')
    elif path.endswith('.tmp'):
        main_as_plugin(path)
    else:
        raise ValueError('Input file must be BAT(engine) or TMP(plugin).')


if __name__ == '__main__':
    print('_____ξ ・ヮ・)ξ < ENUNU v0.1.0 ________')
    print(f'argv: {argv}')
    if len(argv) == 2:
        main(argv[1])
    elif len(argv) == 1:
        path_utauplugin = input(
            'Input file path of BAT(engine) or TMP(plugin)\n>>> '
        ).strip('"')

        main(path_utauplugin)
