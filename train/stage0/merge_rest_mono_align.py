#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
"""
DBに同梱されていたモノラベル中の休符を結合して上書きする。
いったんSongオブジェクトを経由するので、
utaupyの仕様に沿ったフルラベルになってしまうことに注意。
"""
from glob import glob
from os.path import join
from sys import argv

import utaupy as up
import yaml
from tqdm import tqdm
from utaupy.label import Label


def merge_rests_mono(label: Label):
    """
    モノラベルの休符を結合する。
    休符はすべてpauにする。
    """
    # 休符を全部pauにする
    for phoneme in label:
        if phoneme.symbol == 'sil':
            phoneme.symbol = 'pau'

    new_label = Label()
    prev_phoneme = label[0]
    new_label.append(prev_phoneme)
    for phoneme in label[1:]:
        if prev_phoneme.symbol == 'pau' and phoneme.symbol == 'pau':
            prev_phoneme.end += phoneme.end - phoneme.start
        else:
            new_label.append(phoneme)
            prev_phoneme = phoneme
    # 発声終了時刻を再計算(わずかにずれる可能性があるため)
    new_label.reload()

    return new_label


def merge_rests_mono_labfiles(mono_lab_dir):
    mono_lab_files = glob(f'{mono_lab_dir}/*.lab')
    for path_lab in tqdm(mono_lab_files):
        label = up.label.load(path_lab)
        label = merge_rests_mono(label)
        label.write(path_lab)


def main(path_config_yaml):
    with open(path_config_yaml, 'r') as fy:
        config = yaml.load(fy, Loader=yaml.FullLoader)
    out_dir = config['out_dir']
    mono_lab_dir = join(out_dir, 'lab')
    print(f'Merging rests of mono-LAB files in {mono_lab_dir}')
    merge_rests_mono_labfiles(mono_lab_dir)


if __name__ == '__main__':
    main(argv[1].strip('"'))
