#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
"""
モノラベルを休符周辺で切断する。
pau の直前で切断する。休符がすべて結合されていると考えて実行する。
"""
from glob import glob
from os import makedirs
from os.path import basename, splitext
from sys import argv
from typing import List, Union

import utaupy as up
import yaml
from tqdm import tqdm
from utaupy.hts import HTSFullLabel
from utaupy.label import Label


def all_phonemes_are_rest(label) -> bool:
    """
    フルラベル中に休符しかないかどうか判定
    """
    rests = ('pau', 'sil')
    # モノラベルのとき
    if isinstance(label, Label):
        for phoneme in label:
            if phoneme.symbol not in rests:
                return False
        return True
    # フルラベルのとき
    if isinstance(label, HTSFullLabel):
        for oneline in label:
            if oneline.phoneme.identity not in rests:
                return False
        return True
    # フルラベルでもモノラベルでもないとき
    raise ValueError("Argument 'label' must be Label object or HTSFullLabel object.")


def split_mono_label_short(label: Label) -> list:
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


def split_mono_label_long(label: Label) -> list:
    """
    モノラベルを分割する。分割後の複数のLabelからなるリストを返す。
    [pau][pau], [pau][sil] のいずれかの並びで切断する。
    """
    new_label = Label()
    result = [new_label]

    new_label.append(label[0])
    for i, current_phoneme in enumerate(label[1:-1]):
        previous_phoneme = label[i - 1]
        if (previous_phoneme.symbol, current_phoneme.symbol) in [('pau', 'sil'), ('pau', 'pau')]:
            new_label = Label()
            result.append(new_label)
        new_label.append(current_phoneme)
    # 最後の音素を追加
    new_label.append(label[-1])
    return result


def split_full_label_short(full_label: HTSFullLabel) -> list:
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
    # 休符だけの後奏部分があった場合は直前のラベルにまとめる。
    if len(result) >= 2 and all_phonemes_are_rest(result[-1]):
        result[-2] += result[-1]
        del result[-1]
    return result


def split_full_label_long(full_label: HTSFullLabel) -> list:
    """
    フルラベルを分割する。
    できるだけコンテキストを保持するため、SongではなくHTSFullLabelで処理する。

    split_full_label_short ではうまく学習できなかった。
    そこで、全部の休符で切ったらさすがに短かったので長めにとる。
    [pau][pau], [pau][sil] のいずれかの並びで切断する。
    """
    new_label = HTSFullLabel()
    new_label.append(full_label[0])
    result = [new_label]

    for oneline in full_label[1:-1]:
        if ((oneline.previous_phoneme.identity, oneline.phoneme.identity)
                in [('pau', 'sil'), ('pau', 'pau')]):
            print(oneline.previous_phoneme.identity, oneline.phoneme.identity)
            new_label = HTSFullLabel()
            result.append(new_label)
        new_label.append(oneline)
    # 最後の行を追加
    new_label.append(full_label[-1])

    # 休符だけの後奏部分があった場合は直前のラベルにまとめる。
    if len(result) >= 2 and all_phonemes_are_rest(result[-1]):
        result[-2] += result[-1]
        del result[-1]
    return result


def split_label(label: Union[Label, HTSFullLabel], mode: str) -> List[Union[Label, HTSFullLabel]]:
    """
    ラベルを分割してリストにして返す。フルラベルとモノラベルを自動で使い分ける。
    mode: 'short' か 'long' のいずれか
    """
    if mode not in ('short', 'long'):
        raise ValueError('Argument "mode" must be "short" or "long".')

    if isinstance(label, Label):
        if mode == 'short':
            result = split_mono_label_short(label)
        elif mode == 'long':
            result = split_mono_label_long(label)
    elif isinstance(label, HTSFullLabel):
        if mode == 'short':
            result = split_full_label_short(label)
        elif mode == 'long':
            result = split_full_label_long(label)
    return result


def main(path_config_yaml, mode='short'):
    """
    ラベルファイルを取得して分割する。
    """
    with open(path_config_yaml, 'r') as fy:
        config = yaml.load(fy, Loader=yaml.FullLoader)
    out_dir = config['out_dir']

    full_score_round_files = sorted(glob(f'{out_dir}/full_score_round/*.lab'))
    mono_score_round_files = sorted(glob(f'{out_dir}/mono_score_round/*.lab'))
    full_align_round_files = sorted(glob(f'{out_dir}/full_align_round/*.lab'))
    mono_align_round_files = sorted(glob(f'{out_dir}/mono_align_round/*.lab'))

    makedirs(f'{out_dir}/full_score_round_seg', exist_ok=True)
    makedirs(f'{out_dir}/full_align_round_seg', exist_ok=True)
    makedirs(f'{out_dir}/mono_score_round_seg', exist_ok=True)
    makedirs(f'{out_dir}/mono_align_round_seg', exist_ok=True)

    print('Segmenting full_score_round label files')
    for path in tqdm(full_score_round_files):
        songname = splitext(basename(path))[0]
        label = up.hts.load(path)
        label_segments = split_label(label, mode)
        for idx, segment in enumerate(label_segments):
            segment.write(f'{out_dir}/full_score_round_seg/{songname}_seg{idx}.lab',
                          strict_sinsy_style=False)

    print('Segmenting full_align_round label files')
    for path in tqdm(full_align_round_files):
        songname = splitext(basename(path))[0]
        label = up.hts.load(path)
        label_segments = split_label(label, mode)
        for idx, segment in enumerate(label_segments):
            segment.write(f'{out_dir}/full_align_round_seg/{songname}_seg{idx}.lab',
                          strict_sinsy_style=False)

    print('Segmenting mono_score_round label files')
    for path in tqdm(mono_score_round_files):
        songname = splitext(basename(path))[0]
        label = up.label.load(path)
        label_segments = split_label(label, mode)
        for idx, segment in enumerate(label_segments):
            segment.write(f'{out_dir}/mono_score_round_seg/{songname}_seg{idx}.lab')

    print('Segmenting mono_align_round label files')
    # NOTE: ここだけ出力フォルダ名が 入力フォルダ名_seg ではないので注意
    for path in tqdm(mono_align_round_files):
        songname = splitext(basename(path))[0]
        label = up.label.load(path)
        label_segments = split_label(label, mode)
        for idx, segment in enumerate(label_segments):
            segment.write(f'{out_dir}/mono_align_round_seg/{songname}_seg{idx}.lab')


def test_full():
    """
    単独のフルラベルを休符で分割する。
    """
    path_in = input('path_in: ')
    label = up.hts.load(path_in)
    split_result = split_label(label, mode='short')
    for i, full_label in enumerate(split_result):
        path_out = path_in.replace('.lab', f'_split_{str(i).zfill(6)}.lab')
        full_label.write(path_out, strict_sinsy_style=False)


def test_mono():
    """
    単独のモノラベルを休符で分割する。
    """
    path_in = input('path_in: ')
    split_result = split_mono_label_long(up.label.load(path_in))
    for i, mono_label in enumerate(split_result):
        path_out = path_in.replace('.lab', f'_split_{str(i).zfill(6)}.lab')
        mono_label.write(path_out)


if __name__ == '__main__':
    # test_full()
    # test_mono()
    print('----------------------------------------------------------------------------------')
    print('[ Stage 0 ] [ Step 3b ] ')
    print('Segment labels in full_align_round, mono_align, full_score_round, mono_score_round.')
    print('----------------------------------------------------------------------------------')
    main(argv[1])
