#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
"""
LABファイルの時刻丸めを行う。(5ms)
フルラベル・モノラベル問わず、
モノラベル用のutaupy.label.Labelオブジェクトとして処理する。

{out_dir}/lab/*.lab -> {out_dir}/mono_align_round/*.lab
{out_dir}/full_score/*.lab -> {out_dir}/full_score_round/*.lab
"""
from glob import glob
from os import makedirs
from os.path import basename, join
from sys import argv

import utaupy as up
import yaml
from tqdm import tqdm


def round_lab_files(lab_dir_in, lab_dir_out, step_size):
    """
    フォルダを指定し、そのフォルダ内のLABファイルの発声時刻を丸めて、新たなフォルダに保存する。
    """
    makedirs(lab_dir_out, exist_ok=True)
    lab_files = glob(f'{lab_dir_in}/*.lab')
    for path_lab in tqdm(lab_files):
        path_lab_round = join(lab_dir_out, basename(path_lab))
        label = up.label.load(path_lab)
        label.round(step_size)
        label.write(path_lab_round)


def main(path_config_yaml):
    """
    configを読み取ってフォルダを指定し、全体の処理を実行する。
    """
    with open(path_config_yaml, 'r') as fy:
        config = yaml.load(fy, Loader=yaml.FullLoader)
    out_dir = config['out_dir']

    # 時刻を丸める基準[100ns]
    step_size = 50000

    # DBに同梱されていたLABファイルを丸める
    lab_dir_in = join(out_dir, 'lab')
    lab_dir_out = join(out_dir, 'mono_align_round')
    print(f'Rounding mono-LAB files in {lab_dir_in}')
    round_lab_files(lab_dir_in, lab_dir_out, step_size=step_size)

    # 楽譜からつくったフルラベルを丸める
    lab_dir_in = join(out_dir, 'full_score')
    lab_dir_out = join(out_dir, 'full_score_round')
    print(f'Rounding full-LAB files in {lab_dir_in}')
    round_lab_files(lab_dir_in, lab_dir_out, step_size=step_size)


if __name__ == '__main__':
    main(argv[1].strip('"'))
