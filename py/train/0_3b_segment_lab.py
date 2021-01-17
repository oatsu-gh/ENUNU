#!/usr/bin/env python3
# Copyright (c) 2020 oatsu
"""
モノラベルを休符周辺で切断する。
pau の直前で切断する。休符がすべて結合されていると考えて実行する。
"""
from glob import glob
from os import makedirs
from os.path import basename, splitext
from sys import argv

import utaupy as up
import yaml
from tqdm import tqdm
from utaupy.hts import HTSFullLabel
from utaupy.label import Label


def split_mono_label(label: Label) -> list:
    """
    モノラベルを分割する。分割後の複数のLabelからなるリストを返す。
    """
    new_label = Label()
    result = [new_label]

    new_label.append(label[0])
    for phoneme in label[1:-1]:
        if phoneme.symbol == 'pau':
            new_label = Label()
            result.append(new_label)
        new_label.append(phoneme)
    # 最後の音素を追加
    new_label.append(label[-1])

    return result


def split_full_label(full_label: HTSFullLabel) -> list:
    """
    フルラベルを分割する。
    できるだけコンテキストを保持するため、SongではなくHTSFullLabelで処理する。
    """
    new_label = HTSFullLabel()
    new_label.append(full_label[0])
    result = [new_label]

    for oneline in full_label[1:-1]:
        if oneline.phoneme.identity == 'pau':
            new_label = HTSFullLabel()
            result.append(new_label)
        new_label.append(oneline)
    # 最後の行を追加
    new_label.append(full_label[-1])

    return result


def main(path_config_yaml):
    """
    ラベルファイルを取得して分割する。
    """
    with open(path_config_yaml, 'r') as fy:
        config = yaml.load(fy, Loader=yaml.FullLoader)
    out_dir = config['out_dir']

    sinsy_full_round_files = sorted(glob(f'{out_dir}/sinsy_full_round/*.lab'))
    sinsy_mono_round_files = sorted(glob(f'{out_dir}/sinsy_mono_round/*.lab'))
    full_dtw_files = sorted(glob(f'{out_dir}/full_dtw/*.lab'))
    mono_dtw_files = sorted(glob(f'{out_dir}/mono_dtw/*.lab'))

    makedirs(f'{out_dir}/sinsy_full_round_seg', exist_ok=True)
    makedirs(f'{out_dir}/full_dtw_seg', exist_ok=True)
    makedirs(f'{out_dir}/sinsy_mono_round_seg', exist_ok=True)
    makedirs(f'{out_dir}/mono_label_round_seg', exist_ok=True)

    print('Segmenting sinsy_full_round label files')
    for path in tqdm(sinsy_full_round_files):
        songname = splitext(basename(path))[0]
        full_label = up.hts.load(path)
        label_segments = split_full_label(full_label)
        for idx, segment in enumerate(label_segments):
            segment.write(f'{out_dir}/sinsy_full_round_seg/{songname}_seg{idx}.lab',
                          strict_sinsy_style=False)

    print('Segmenting full_dtw label files')
    for path in tqdm(full_dtw_files):
        songname = splitext(basename(path))[0]
        full_label = up.hts.load(path)
        label_segments = split_full_label(full_label)
        for idx, segment in enumerate(label_segments):
            segment.write(f'{out_dir}/full_dtw_seg/{songname}_seg{idx}.lab',
                          strict_sinsy_style=False)

    print('Segmenting sinsy_mono_round label files')
    for path in tqdm(sinsy_mono_round_files):
        songname = splitext(basename(path))[0]
        mono_label = up.label.load(path)
        label_segments = split_mono_label(mono_label)
        for idx, segment in enumerate(label_segments):
            segment.write(f'{out_dir}/sinsy_mono_round_seg/{songname}_seg{idx}.lab')

    print('Segmenting mono_dtw label files')
    # NOTE: ここだけ出力フォルダ名が 入力フォルダ名_seg ではないので注意
    for path in tqdm(mono_dtw_files):
        songname = splitext(basename(path))[0]
        mono_label = up.label.load(path)
        label_segments = split_mono_label(mono_label)
        for idx, segment in enumerate(label_segments):
            segment.write(f'{out_dir}/mono_label_round_seg/{songname}_seg{idx}.lab')


def test_full():
    """
    単独のフルラベルを休符で分割する。
    """
    path_in = input('path_in: ')
    split_result = split_full_label(up.hts.load(path_in))
    for i, full_label in enumerate(split_result):
        path_out = path_in.replace('.lab', f'_split_{str(i).zfill(6)}.lab')
        full_label.write(path_out, strict_sinsy_style=False)


def test_mono():
    """
    単独のフルラベルを休符で分割する。
    """
    path_in = input('path_in: ')
    split_result = split_mono_label(up.label.load(path_in))
    for i, mono_label in enumerate(split_result):
        path_out = path_in.replace('.lab', f'_split_{str(i).zfill(6)}.lab')
        mono_label.write(path_out)


if __name__ == '__main__':
    # test_full()
    # test_mono()
    print('----------------------------------------------------------------------------------')
    print('[ Stage 0 ] [ Step 3b ] ')
    print('Segment labels in full_dtw, mono_dtw, sinsy_full_round, sinsy_mono_round.')
    print('----------------------------------------------------------------------------------')
    main(argv[1])
