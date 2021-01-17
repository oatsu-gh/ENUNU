#!/usr/bin/env python3
# Copyright (c) 2020 oatsu
"""
DBのモノラベルの時刻をフルラベルに書き写して、
音声ファイルの発声時刻に合ったフルラベルを生成する。

音素数と音素が完全に一致している前提で処理する。
"""

from glob import glob
from os import makedirs
from os.path import basename
from sys import argv

import utaupy as up
import yaml
from tqdm import tqdm


def copy_mono_time_to_full(path_mono_in, path_full_in, path_full_out):
    """
    モノラベルの発声時刻をフルラベルにコピーする。
    """
    mono_label = up.label.load(path_mono_in)
    full_label = up.label.load(path_full_in)
    # ラベル内の各行を比較する。
    for ph_mono, ph_full in zip(mono_label, full_label):
        # 発声開始時刻を上書き
        ph_full.start = ph_mono.start
        # 発声終了時刻を上書き
        ph_full.end = ph_mono.end
    # ファイル出力
    full_label.write(path_full_out)


def main(path_config_yaml):
    """
    モノラベルとフルラベルのファイルを取得して処理を実行する。
    """
    with open(path_config_yaml, 'r') as fy:
        config = yaml.load(fy, Loader=yaml.FullLoader)
    out_dir = config['out_dir']

    # 出力先フォルダを作成
    full_dtw_dir = f'{out_dir}/full_dtw'
    makedirs(full_dtw_dir, exist_ok=True)

    # 時刻のもとになるモノラベルファイル一覧
    mono_dtw_files = sorted(glob(f'{out_dir}/mono_dtw/*.lab'))
    # コンテキストのもとになるフルラベルファイル一覧
    sinsy_mono_files = sorted(glob(f'{out_dir}/sinsy_full/*.lab'))

    print('Copying times in mono_dtw to sinsy_full and save in full_dtw')
    for path_mono_dtw, path_sinsy_full in zip(tqdm(mono_dtw_files), sinsy_mono_files):
        path_full_dtw = f'{full_dtw_dir}/{basename(path_sinsy_full)}'
        copy_mono_time_to_full(path_mono_dtw, path_sinsy_full, path_full_dtw)


if __name__ == '__main__':
    print('----------------------------------------------------------------------------------')
    print('[ Stage 0 ] [ Step 3a ]')
    print('Copy mono_dtw phonemes to sinsy_full and save in full_dtw.')
    print('----------------------------------------------------------------------------------')
    main(argv[1])
