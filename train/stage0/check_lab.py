#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
"""
歌唱DBに含まれるモノラベルに不具合がないか点検する。

- 極端に短い音素(5ms以下)がないか
- 時刻の順序が逆転しているラベルがないか
"""
import logging
import sys
from glob import glob
from os.path import dirname, expanduser, join
from pprint import pprint

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
    if len(invalid_lab_files) != threshold:
        print('LABファイルの発声時刻に不具合があります。以下のファイルを点検してください。')
        pprint(invalid_lab_files)
        raise Exception


def repair_too_short_phoneme(lab_dir, threshold=5) -> None:
    """
    LABファイルの中の発声時刻が短すぎる音素(5ms未満の時とか)を修正する。
    直前の音素の長さを削る。
    一番最初の音素が短い場合のみ修正できない。
    """
    mono_lab_files = glob(f'{lab_dir}/*.lab')
    threshold_100ns = threshold * 10000
    for path_mono in tqdm(mono_lab_files):
        # LABファイルを読み取る
        label = up.label.load(path_mono)
        # 短い音素が一つもない場合はスルー
        if all(phoneme.duration >= threshold_100ns for phoneme in label):
            continue
        # 短い音素が連続しても不具合が起こらないように逆向きにループする
        if label[0].duration < threshold_100ns:  # pylint: disable=no-member
            raise ValueError(f'最初の音素が短いです。修正できません。: {label[0]} ({path_mono})')
        for i, phoneme in enumerate(reversed(label)):
            # 発声時間が閾値より短い場合
            if phoneme.duration < threshold_100ns:
                logging.info('短い音素を修正します。: %s (%s)', phoneme, path_mono)
                # 閾値との差分を計算する。この分だけずらす。
                delta_t = threshold_100ns - phoneme.duration
                # 対象の音素の開始時刻をずらして、発生時間を伸ばす。
                phoneme.start -= delta_t
                # 直前の音素の終了時刻もずらす。
                # label[-(i + 1) - 1]
                label[-i - 2].end -= delta_t
            # 修正済みデータで上書き保存
            label.write(path_mono)


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
    repair_too_short_phoneme(lab_dir)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        main('config.yaml')
    else:
        main(sys.argv[1].strip('"'))
