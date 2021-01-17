#!/usr/bin/env python3
# Copyright (c) 2020 oatsu
"""
Sinsyの出力と音素数が一致するかだけをチェックする。
チェックに通過したら mono_label フォルダから mono_dtwフォルダにコピーする。

Shirani さんのレシピでは fastdtw を使って、
DB同梱のモノラベルをSinsy出力の音素と一致させる。
"""
from glob import glob
from os import makedirs
from os.path import basename
from shutil import copy
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
        'Sinsyの出力({})とDBのモノラベル({})の音素数が一致しません。'.format(
        path_mono_label, path_sinsy_mono
    )
    assert [phoneme.symbol for phoneme in mono_label] == [
        phoneme.symbol for phoneme in sinsy_mono], \
        'Sinsyの出力({})とDBのモノラベル({})の音素記号が一致しません。'.format(
        path_mono_label, path_sinsy_mono
    )


def main(path_config_yaml):
    """
    全体の処理をやる。
    """
    with open(path_config_yaml, 'r') as fy:
        config = yaml.load(fy, Loader=yaml.FullLoader)
    out_dir = config['out_dir']
    makedirs(f'{out_dir}/mono_dtw', exist_ok=True)
    mono_label_files = sorted(glob(f'{out_dir}/mono_label_round/*.lab'))
    sinsy_mono_files = sorted(glob(f'{out_dir}/sinsy_mono_round/*.lab'))

    # 音素数と音素記号が一致するか確認する。
    print('Comparing mono label from DB and Sinsy')
    for path_mono_label, path_sinsy_mono in zip(tqdm(mono_label_files), sinsy_mono_files):
        compare_lab_file(path_mono_label, path_sinsy_mono)
        # ファイル名に多少のミスがあってもいいようにMusicXMLのファイル名をもとにする。
        path_out = f'{out_dir}/mono_dtw/{basename(path_sinsy_mono)}'
        copy(path_mono_label, path_out)


if __name__ == '__main__':
    print('------------------------------------------------------------------------')
    print('[ Stage 0 ] [ Step 2 ] Check mono_label files and copy them to mono_dtw.')
    print('------------------------------------------------------------------------')
    main(argv[1])
