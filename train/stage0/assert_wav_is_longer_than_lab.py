#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
"""
WAVファイルが full_align_lab より長いことを確認する。
"""
from sys import argv
import sys
import warnings
from glob import glob
from logging import warning
from os.path import join

import utaupy
import yaml
from natsort import natsorted
from tqdm import tqdm

with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    from pydub import AudioSegment


def wav_is_longer_than_lab(path_wav: str, path_lab: str) -> bool:
    """
    1. wavの長さを取得する
    2. labの最後の音素の時刻を収録する
    3. 比較する
    """
    # LABファイルの最後の音素の時刻を取得する。[sec]
    label = utaupy.label.load(path_lab)
    lab_endtime_sec = label[-1].end / 10000000

    # WAVファイルの長さを取得する[sec]
    wav_length_sec = AudioSegment.from_file(path_wav, 'wav').duration_seconds

    # 長さを比較
    return wav_length_sec >= lab_endtime_sec


def compare_wav_files_and_lab_files(wav_dir_in, lab_dir_in):
    """
    フォルダを指定して、その中のファイルを比較
    """
    wav_files = natsorted(glob(f'{wav_dir_in}/*.wav'))
    lab_files = natsorted(glob(f'{lab_dir_in}/*.lab'))
    for path_wav, path_lab in zip(tqdm(wav_files), lab_files):
        if not wav_is_longer_than_lab(path_wav, path_lab):
            warning_message = f'WAV is shorter than LAB or score. ({path_wav}) ({path_lab})'
            warning(warning_message)


def main(path_config_yaml):
    """
    configを読み取ってフォルダを指定し、全体の処理を実行する。
    """
    print('Asserting WAV files are longer than full_align_round label files')
    with open(path_config_yaml, 'r') as fy:
        config = yaml.load(fy, Loader=yaml.FullLoader)
    out_dir = config['out_dir']

    # DBに同梱されていたLABファイルを丸める
    wav_dir_in = join(out_dir, 'wav')
    full_align_dir_in = join(out_dir, 'full_align_round')
    full_score_dir_in = join(out_dir, 'full_score_round')
    # 点検する
    print('Comparing length of LAB and WAV')
    compare_wav_files_and_lab_files(wav_dir_in, full_align_dir_in)
    print('Comparing length of score and WAV')
    compare_wav_files_and_lab_files(wav_dir_in, full_score_dir_in)


if __name__ == '__main__':
    if len(argv) == 1:
        main('config.yaml')
    else:
        main(argv[1].strip('"'))
