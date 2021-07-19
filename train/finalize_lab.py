#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
#
"""
各種ラベルが正常かチェックして、
timelag とか duration とか acoustic の学習用フォルダにコピーする。
あと音声ファイルを切断する。

音声の offset_correction がよくわからんので実装できてない。
"""
from glob import glob
from os import makedirs
from os.path import basename, expanduser, splitext
from shutil import copy
from sys import argv

import utaupy as up
import yaml
from natsort import natsorted
from pydub import AudioSegment
from tqdm import tqdm


def lab_fix_offset(path_lab):
    """
    ラベルの開始時刻をゼロにする。(音声を切断したため。)
    ファイルは上書きする。
    """
    label = up.label.load(path_lab)
    offset = label[0].start
    for phoneme in label:
        phoneme.start -= offset
        phoneme.end -= offset
    label.write(path_lab)


def prepare_data_for_timelag_models(
        full_align_round_seg_files: list, full_score_round_seg_files: list, timelag_dir):
    """
    timilagモデル用にラベルファイルをコピーする

    Shiraniさんのレシピではoffset_correstionの工程が含まれるが、
    このプログラムでは実装していない。
    """
    label_phone_align_dir = f'{timelag_dir}/label_phone_align'
    label_phone_score_dir = f'{timelag_dir}/label_phone_score'

    makedirs(label_phone_align_dir, exist_ok=True)
    makedirs(label_phone_score_dir, exist_ok=True)

    # 手動設定したフルラベルファイルを複製
    print('Copying full_align_round_seg files')
    for path_lab in tqdm(full_align_round_seg_files):
        copy(path_lab, f'{label_phone_align_dir}/{basename(path_lab)}')

    # 楽譜から生成したフルラベルファイルを複製
    print('Copying full_score_round_seg files')
    for path_lab in tqdm(full_score_round_seg_files):
        copy(path_lab, f'{label_phone_score_dir}/{basename(path_lab)}')


def prepare_data_for_duration_models(full_align_round_seg_files: list, duration_dir):
    """
    durationモデル用にラベルファイルを複製する。
    """
    label_phone_align_dir = f'{duration_dir}/label_phone_align'
    makedirs(label_phone_align_dir, exist_ok=True)

    # 手動設定したフルラベルファイルを複製
    print('Copying full_align_round_seg files')
    for path_lab_in in tqdm(full_align_round_seg_files):
        path_lab_out = f'{label_phone_align_dir}/{basename(path_lab_in)}'
        copy(path_lab_in, path_lab_out)
        lab_fix_offset(path_lab_out)


def segment_wav(path_wav_in, acoustic_wav_dir, corresponding_full_align_round_seg_files: list):
    """
    音声ファイルを切り出して出力する。
    - pydubをつかうと16bitにされずに済みそう。(32bitになる)
    - pydubをつかうと入力にwav以外も使えそう。

    full_align_round_seg_files: full_align_round_seg の中にあるファイル(切断時刻のデータを持っている)
    """
    # TODO: 処理が遅いと思うので、並列実行できるようにする。
    # 音声ファイルを読み取る
    wav = AudioSegment.from_file(path_wav_in, format='wav')
    for path_lab in tqdm(corresponding_full_align_round_seg_files):
        label = up.label.load(path_lab)
        # 切断時刻を取得
        t_start_ms = round(label[0].start / 10000)
        t_end_ms = round(label[-1].end / 10000)
        # 切り出す
        wav_slice = wav[t_start_ms:t_end_ms]
        # outdir/songname_segx.wav
        path_wav_seg_out = f'{acoustic_wav_dir}/{splitext(basename(path_lab))[0]}.wav'
        wav_slice.export(path_wav_seg_out, format='wav')


def prepare_data_for_acoustic_models(
        full_align_round_seg_files: list, full_score_round_seg_files: list, wav_files: list, acoustic_dir):
    """
    acousticモデル用に音声ファイルとラベルファイルを複製する。
    """
    wav_dir = f'{acoustic_dir}/wav'
    label_phone_align_dir = f'{acoustic_dir}/label_phone_align'
    label_phone_score_dir = f'{acoustic_dir}/label_phone_score'
    # 出力先フォルダを作成
    makedirs(wav_dir, exist_ok=True)
    makedirs(label_phone_align_dir, exist_ok=True)
    makedirs(label_phone_score_dir, exist_ok=True)

    # wavファイルを分割して保存する
    print('Split wav files')
    for path_wav in tqdm(wav_files):
        songname = splitext(basename(path_wav))[0]
        corresponding_full_align_round_seg_files = [
            path for path in full_align_round_seg_files if f'{songname}_seg' in path
        ]
        segment_wav(path_wav, wav_dir, corresponding_full_align_round_seg_files)

    # 手動設定したフルラベルファイルを複製
    print('Copying full_align_round_seg files')
    for path_lab_in in tqdm(full_align_round_seg_files):
        path_lab_out = f'{label_phone_align_dir}/{basename(path_lab_in)}'
        copy(path_lab_in, path_lab_out)
        lab_fix_offset(path_lab_out)

    # 楽譜から生成したフルラベルファイルを複製
    print('Copying full_score_round_seg files')
    for path_lab_in in tqdm(full_score_round_seg_files):
        path_lab_out = f'{label_phone_score_dir}/{basename(path_lab_in)}'
        copy(path_lab_in, path_lab_out)
        lab_fix_offset(path_lab_out)


def main(path_config_yaml):
    """
    フォルダを指定して全体の処理をやる
    """
    with open(path_config_yaml, 'r') as fy:
        config = yaml.load(fy, Loader=yaml.FullLoader)
    out_dir = expanduser(config['out_dir'])

    full_align_round_seg_files = natsorted(glob(f'{out_dir}/full_align_round_seg/*.lab'))
    full_score_round_seg_files = natsorted(glob(f'{out_dir}/full_score_round_seg/*.lab'))
    wav_files = natsorted(glob(f'{out_dir}/wav/*.wav', recursive=True))

    # フルラベルをtimelag用のフォルダに保存する。
    print('Preparing data for time-lag models')
    timelag_dir = f'{out_dir}/timelag'
    prepare_data_for_timelag_models(full_align_round_seg_files,
                                    full_score_round_seg_files, timelag_dir)

    # フルラベルのオフセット修正をして、duration用のフォルダに保存する。
    print('Preparing data for acoustic models')
    duration_dir = f'{out_dir}/duration'
    prepare_data_for_duration_models(full_align_round_seg_files, duration_dir)

    # フルラベルのオフセット修正をして、acoustic用のフォルダに保存する。
    # wavファイルをlabファイルのセグメントに合わせて切断
    print('Preparing data for acoustic models')
    acoustic_dir = f'{out_dir}/acoustic'
    prepare_data_for_acoustic_models(
        full_align_round_seg_files, full_score_round_seg_files, wav_files, acoustic_dir)


if __name__ == '__main__':
    print('----------------------------------------------------------------------------------')
    print('[ Stage 0 ] [ Step 4 ] ')
    print('- Segment WAV files and save to acoustic model directory.')
    print('- Copy LAB files to each model directory.')
    print('- Fix offset of LAB files for acoustic and duration model.')
    print('----------------------------------------------------------------------------------')
    if len(argv) == 1:
        main('config.yaml')
    else:
        main(argv[1].strip('"'))
