#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
"""
フルラベルを読み取ってモノラベルにして保存する。
"""
from glob import glob
from os import makedirs
from os.path import basename, join
from sys import argv

import utaupy as up
import yaml
from tqdm import tqdm


def full_files_to_mono_files(full_lab_dir, mono_lab_dir):
    """
    指定されたフォルダのフルラベルを読み取って、
    モノラベルとして他のフォルダに保存する。
    """
    full_labels = glob(f'{full_lab_dir}/*.lab')
    makedirs(mono_lab_dir, exist_ok=True)
    for path_full in tqdm(full_labels):
        full_label_obj = up.hts.load(path_full)
        full_label_obj.as_mono().write(join(mono_lab_dir, basename(path_full)))


def main(path_config_yaml):
    """
    configファイルからフォルダを指定して、全体の処理を実行する。
    """
    # 設定ファイルを読み取る
    with open(path_config_yaml, 'r') as fy:
        config = yaml.load(fy, Loader=yaml.FullLoader)
    out_dir = config['out_dir'].strip('"')

    full_score_dir = join(out_dir, 'full_score_round')
    mono_score_dir = join(out_dir, 'mono_score_round')
    print(f'Copying full-score-LAB an mono-score-LAB into {mono_score_dir}')
    full_files_to_mono_files(full_score_dir, mono_score_dir)


if __name__ == '__main__':
    main(argv[1].strip('"'))
