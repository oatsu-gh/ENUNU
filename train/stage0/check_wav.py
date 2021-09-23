#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
"""
音声ファイルのフォーマットが適切か点検する。
- モノラル音声か
- 全部同じビット深度か
  - 16bit int または 32bit int か
- 全部同じサンプルレートか
  - config と対応しているか
"""

import logging
import warnings
from glob import glob
# from typing import List
from os.path import join
from statistics import mode
from sys import argv

import yaml
from natsort import natsorted

with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    from pydub import AudioSegment


def all_wav_files_are_mono(wav_dir_in) -> bool:
    """
    全音声がモノラルであるか点検する。
    """
    wav_files = natsorted(glob(f'{wav_dir_in}/*.wav'))
    all_channnels = [AudioSegment.from_file(path_wav).channels for path_wav in wav_files]
    # 全ファイルがモノラルのとき
    if all(channels == 1 for channels in all_channnels):
        return True
    # モノラルではないファイルが含まれるとき
    for path_wav, channels in zip(wav_files, all_channnels):
        if not channels == 1:
            logging.error('モノラル音声ではありません。: %s', path_wav)
    return False


def all_wav_files_are_same_sampling_rate(wav_dir_in) -> bool:
    """
    全音声のサンプリングレートが一致するか調べる
    """
    wav_files = natsorted(glob(f'{wav_dir_in}/*.wav'))
    all_frame_rates = [AudioSegment.from_file(path_wav).frame_rate for path_wav in wav_files]

    # 全ファイルのサンプルレートが一致した場合はTrueを返す
    if len(set(all_frame_rates)) == 1:
        return True

    # 全ファイルが一致しなかった場合
    # サンプリングレートの最頻値
    mode_frame_rate = mode(all_frame_rates)
    for path_wav, rate in zip(wav_files, all_frame_rates):
        if rate != mode_frame_rate:
            logging.error('サンプリングレートが他のファイルと一致しません。: %s', path_wav)
    return False


def all_wav_files_are_same_bit_depth(wav_dir_in) -> bool:
    """
    全音声のビット深度が一致するか調べる
    """
    wav_files = natsorted(glob(f'{wav_dir_in}/*.wav'))
    all_sample_widths = [AudioSegment.from_file(path_wav).sample_width for path_wav in wav_files]

    # 全ファイルのビット深度が一致した場合はTrueを返す
    if len(set(all_sample_widths)) == 1:
        return True

    # 一致しなかった場合
    # ビット深度の最頻値
    mode_bit_depth = mode(all_sample_widths)
    for path_wav, width in zip(wav_files, all_sample_widths):
        if width != mode_bit_depth:
            logging.error('ビット深度が他のファイルと一致しません。: %s', path_wav)
    return False


def main(path_config_yaml):
    """
    全体処理を実行する
    """
    print('Checking WAV files')
    with open(path_config_yaml, 'r') as fy:
        config = yaml.safe_load(fy)

    out_dir = config['out_dir']
    # wavファイル一覧を取得
    wav_dir_in = join(out_dir, 'wav')

    # 全ファイルがモノラルか確認する
    if not all_wav_files_are_mono(wav_dir_in):
        raise ValueError('モノラルではない音声ファイルがあります。ログを確認して修正して下さい。')
    if not all_wav_files_are_same_sampling_rate(wav_dir_in):
        raise ValueError('サンプリングレートが異なる音声ファイルがあります。ログを確認して修正して下さい。')
    if not all_wav_files_are_same_bit_depth(wav_dir_in):
        raise ValueError('ビット深度が異なる音声ファイルがあります。ログを確認して修正して下さい。')


if __name__ == '__main__':
    if len(argv) == 1:
        main('config.yaml')
    else:
        main(argv[1].strip('"'))
