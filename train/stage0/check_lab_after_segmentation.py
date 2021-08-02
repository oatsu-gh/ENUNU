#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
"""
分割してroundした のあとに、各フォルダに設置したラベルファイルを点検する。
"""
from sys import argv
from glob import glob
import logging
from os.path import dirname, expanduser, join

import utaupy as up
import yaml
from tqdm import tqdm


def check_lab_files(lab_dir, threshold=0):
    """
    発声時間が負でないか点検する。
    """
    mono_lab_files = sorted(glob(f'{lab_dir}/*.lab'))
    invalid_lab_files = []
    for path_mono in tqdm(mono_lab_files):
        label = up.label.load(path_mono)
        if not label.is_valid(threshold):
            invalid_lab_files.append(path_mono)
            logging.error('LABファイルの発声時刻に不具合があります。(%s)', path_mono)
            print()
    if len(invalid_lab_files) != 0:
        message = '  \n'.join(['LABファイルの発声時刻に不具合があります。以下のファイルを点検してください。'] + invalid_lab_files)
        # logging.exception(message)
        raise Exception(message)


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
    for lab_dir in [f'{out_dir}/full_align_round_seg', f'{out_dir}/mono_align_round_seg']:
        print(f'Checking LAB files in {lab_dir}')
        check_lab_files(lab_dir)


if __name__ == '__main__':
    if len(argv) == 1:
        main('config.yaml')
    else:
        main(argv[1].strip('"'))
