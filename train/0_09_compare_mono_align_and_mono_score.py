#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
"""
Sinsyの出力と音素数が一致するかだけをチェックする。
チェックに通過したら mono_label フォルダから mono_dtwフォルダにコピーする。

Shirani さんのレシピでは fastdtw を使って、
DB同梱のモノラベルをSinsy出力の音素と一致させる。
"""
from glob import glob
from os import makedirs
from sys import argv

import utaupy as up
import yaml
from tqdm import tqdm


def compare_lab_file(path_mono_label, path_sinsy_mono):
    """
    音素数と音素記号が一致するかチェックする。
    """
    mono_label = up.label.load(path_mono_label)
    sinsy_mono = up.label.load(path_sinsy_mono)
    assert len(mono_label) == len(sinsy_mono), \
        'DB同梱のラベル({}, {})と楽譜から生成したラベル({}, {})の音素数が一致しません。'.format(
        len(mono_label), path_mono_label, len(sinsy_mono), path_sinsy_mono
    )
    for mono_align_phoneme, mono_score_phoneme in zip(mono_label, sinsy_mono):
        assert mono_align_phoneme.symbol == mono_score_phoneme.symbol, \
            'DB同梱のラベル("{}", {})と楽譜から生成したラベル("{}", {})の音素記号が一致しません。'.format(
                mono_align_phoneme.symbol, path_mono_label,
                mono_score_phoneme.symbol, path_sinsy_mono
            )


def main(path_config_yaml):
    """
    全体の処理をやる。
    """
    with open(path_config_yaml, 'r') as fy:
        config = yaml.load(fy, Loader=yaml.FullLoader)
    out_dir = config['out_dir']
    mono_align_files = sorted(glob(f'{out_dir}/mono_align_round/*.lab'))
    mono_score_files = sorted(glob(f'{out_dir}/mono_score_round/*.lab'))

    # 音素数と音素記号が一致するか確認する。
    print('Comparing mono-align-LAB and mono-score-LAB')
    for path_mono_align, path_mono_score in zip(tqdm(mono_align_files), mono_score_files):
        compare_lab_file(path_mono_align, path_mono_score)


if __name__ == '__main__':
    if len(argv) == 1:
        main('config.yaml')
    else:
        main(argv[1].strip('"'))
