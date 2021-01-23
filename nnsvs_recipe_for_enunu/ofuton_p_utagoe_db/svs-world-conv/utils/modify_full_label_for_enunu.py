#!/usr/bin/env python3
# Copyright (c) 2020 oatsu
"""
学習データをENUNU最適化するスクリプト【簡易版】

学習用のフルラベルをutaupyでロードしてから再出力することで、
UST→フルラベル の変換時に生成されるフルラベルの仕様と一致させる。
"""
from glob import glob
from os.path import dirname
from sys import argv

import utaupy as up
import yaml
from tqdm import tqdm


def glob_all_full_label(data_dir) -> list:
    """
    編集すべきフルラベルファイルを
    data_dir: config.yaml 中で out_dir で指定されているフォルダ。LABファイルがありそうなところ。
    """
    full_label_files = glob(f'{data_dir}/**/*.lab', recursive=True)
    full_label_files = [path for path in full_label_files if 'full' in dirname(path)]
    return full_label_files


def modify_full_label(path_full_in, path_full_out):
    """
    フルラベルをutaupy仕様で出力する。
    変更がないところはそのままになるが、
    UST→フルラベル のときに生成できるコンテキストであるとは限らない。
    """
    full_label = up.hts.load(path_full_in)
    full_label.song.write(path_full_out, strict_sinsy_style=False, label_type='full')


def main(path_config_yaml):
    """
    configをもとに処理対象フォルダを決定して、全体の処理を実行する。
    """
    with open(path_config_yaml, 'r') as fy:
        config = yaml.load(fy, Loader=yaml.FullLoader)
    out_dir = config['out_dir']

    full_label_files = glob_all_full_label(out_dir)

    for path_full in tqdm(full_label_files):
        up.utils.hts2json(path_full, path_full.replace('.lab', '.json'))
        print(path_full)
        modify_full_label(path_full, path_full)


if __name__ == '__main__':
    if len(argv) < 2:
        main(input('select config.yaml file\n>>> ').strip('"'))
    else:
        main(argv[1])
