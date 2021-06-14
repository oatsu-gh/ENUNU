#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
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


def copy_mono_align_time_to_full(path_mono_in, path_full_in, path_full_out):
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
    full_align_dir = f'{out_dir}/full_align_round'
    makedirs(full_align_dir, exist_ok=True)

    # 時刻のもとになるモノラベルファイル一覧
    mono_align_files = sorted(glob(f'{out_dir}/mono_align_round/*.lab'))
    # コンテキストのもとになるフルラベルファイル一覧
    full_score_files = sorted(glob(f'{out_dir}/full_score_round/*.lab'))

    print('Copying times of mono-LAB (mono_align_round) to full-LAB (full_score_round) and save into full_align_round')
    for path_mono_align, path_full_score in zip(tqdm(mono_align_files), full_score_files):
        path_full_align = f'{full_align_dir}/{basename(path_full_score)}'
        copy_mono_align_time_to_full(path_mono_align, path_full_score, path_full_align)


if __name__ == '__main__':
    print('----------------------------------------------------------------------------------')
    print('[ Stage 0 ] [ Step 3a ]')
    print('Copy mono_align phonemes to full_score and save in full_align.')
    print('----------------------------------------------------------------------------------')
    main(argv[1])
