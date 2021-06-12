#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
"""
歌唱DBに含まれるモノラベルに不具合がないか点検する。

- 極端に短い音素(5ms以下)がないか
- 時刻の順序が逆転しているラベルがないか
"""
import sys
from glob import glob
from os.path import dirname, expanduser, join
from pprint import pprint

import utaupy as up
import yaml
from tqdm import tqdm


def check_lab_files(lab_dir):
    """
    時刻がちゃんとしてるか点検
    """
    mono_lab_files = sorted(glob(f'{lab_dir}/*.lab'))
    # 発声時間が短すぎないか点検
    invalid_lab_files = []
    for path_mono in tqdm(mono_lab_files):
        label = up.label.load(path_mono)
        if not label.is_valid(5):
            invalid_lab_files.append(path_mono)
    if len(invalid_lab_files) != 0:
        print('LABファイルの発声時刻に不具合があります。以下のファイルを点検してください。')
        pprint(invalid_lab_files)
        sys.exit(1)


def main(path_config_yaml):
    """
    config.yaml から歌唱DBのパスを取得して、
    そのDB中のLABファイルを点検する。
    """
    # 設定ファイルを読み取る
    with open(path_config_yaml, 'r') as fy:
        config = yaml.load(fy, Loader=yaml.FullLoader)
    # 歌唱DBのパスを取得する
    config_dir = dirname(path_config_yaml)
    out_dir = expanduser(join(config_dir, config['out_dir'])).strip('"')
    lab_dir = join(out_dir, 'lab')
    # LABファイルを点検する
    print(f'Checking LAB files in {lab_dir}')
    check_lab_files(lab_dir)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        main('config.yaml')
    else:
        main(sys.argv[1].strip('"'))
