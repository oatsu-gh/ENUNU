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
from os.path import relpath, splitext

import utaupy as up
from hts2json import hts2json
from hts2wav import hts2wav
from hydra.experimental import compose, initialize
from ust2hts import ust2hts


def get_project_path(utauplugin: up.utauplugin.UtauPlugin):
    """
    キャッシュパスとプロジェクトパスを取得する。
    """
    # ustのパス
    path_ust = utauplugin.setting.get_by_key['Project']
    # 音源フォルダ
    voice_dir = utauplugin.setting.get_by_key['VoiceDir']
    # 音声キャッシュのフォルダ(LABとJSONを設置する)
    cache_dir = utauplugin.setting.get_by_key['CacheDir']

    return path_ust, voice_dir, cache_dir


def main(plugin: up.utauplugin.UtauPlugin):
    """
    UtauPluginオブジェクトから音声ファイルを作る
    """
    str_now = datetime.now().strftime('%Y%m%d%h%M%S')
    path_ust, voice_dir, chache_dir = get_project_path(plugin)
    # 使用するモデルの設定
    enuconfig_name = 'enuconfig'
    # configファイルを読み取る
    initialize(config_path=relpath(voice_dir))
    cfg = compose(config_name=enuconfig_name, overrides=[f'+config_path={voice_dir}'])
    # 使用する
    path_lab = f'{chache_dir}/temp.lab'
    path_json = path_lab.replace('.lab', '.json')
    path_wav = f'{splitext(path_ust)[0]}__{str_now}.wav'
    # 変換テーブルのパス
    path_table = f'{voice_dir}/{cfg.table_path}'
    # ファイル処理
    ust2hts(path_ust, path_lab, path_table)
    hts2json(path_lab, path_json)
    hts2wav(cfg, path_lab, path_wav)


if __name__ == '__main__':
    up.utauplugin.run(main)
