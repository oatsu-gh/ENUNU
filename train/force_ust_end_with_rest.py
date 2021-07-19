#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
"""
USTファイルの最終ノートを休符にする。
"""
from glob import glob
from os.path import join
from sys import argv

import utaupy as up
import yaml
from tqdm import tqdm


def force_ust_files_end_with_rest(ust_dir):
    """
    フォルダを指定し、その中にあるUSTファイルが全て休符で終わるようにする。
    """
    ust_files = glob(f'{ust_dir}/*.ust')
    for path_ust in tqdm(ust_files):
        ust = up.ust.load(path_ust)
        ust.make_finalnote_R()
        ust.write(path_ust)


def main(path_config_yaml):
    """
    フォルダとかを指定
    """
    # 設定ファイルを読み取る
    with open(path_config_yaml, 'r') as fy:
        config = yaml.load(fy, Loader=yaml.FullLoader)
    # 処理対象のフォルダを指定
    out_dir = config['out_dir'].strip('"')
    ust_dir = join(out_dir, 'ust')
    # oto2kabの仕様に合わせて、USTが休符で終わるようにする。
    print('Overwriting UST file so that it end with rest note.')
    force_ust_files_end_with_rest(ust_dir)


if __name__ == '__main__':
    if len(argv) == 1:
        main('config.yaml')
    else:
        main(argv[1].strip('"'))
