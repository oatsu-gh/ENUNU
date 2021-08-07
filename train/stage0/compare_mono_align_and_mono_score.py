#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
"""
Sinsyの出力と音素数が一致するかだけをチェックする。
チェックに通過したら mono_label フォルダから mono_dtwフォルダにコピーする。

Shirani さんのレシピでは fastdtw を使って、
DB同梱のモノラベルをSinsy出力の音素と一致させる。
"""
import logging
from glob import glob
# from os import makedirs
from os.path import basename
from sys import argv
from typing import Union

import utaupy as up
import yaml
from natsort import natsorted
from tqdm import tqdm


def phoneme_is_ok(path_mono_align_lab, path_mono_score_lab):
    """
    音素数と音素記号が一致するかチェックする。
    """
    mono_align_label = up.label.load(path_mono_align_lab)
    mono_score_label = up.label.load(path_mono_score_lab)
    # assert len(mono_label) == len(sinsy_mono), \
    #     'DB同梱のラベル({}, {})と楽譜から生成したラベル({}, {})の音素数が一致しません。'.format(
    #     len(mono_label), path_mono_label, len(sinsy_mono), path_sinsy_mono
    # )
    for mono_align_phoneme, mono_score_phoneme in zip(mono_align_label, mono_score_label):
        if mono_align_phoneme.symbol != mono_score_phoneme.symbol:
            error_message = '\n'.join([
                f'DB同梱のラベルと楽譜から生成したラベルの音素記号が一致しません。({basename(path_mono_align_lab)})',
                f'  DB同梱のラベル  : {mono_align_phoneme}\t({path_mono_align_lab})',
                f'  楽譜からのラベル: {mono_align_phoneme}\t({path_mono_align_lab})'
            ])
            logging.error(error_message)
            return False
    # 全音素記号が一致したらTrueを返す
    return True


def force_start_with_zero(path_mono_align_lab):
    """
    最初の音素(pau)の開始時刻を0にする。
    LABの元のiniの、左ブランクとか先行発声が動かされてると0ではなくなってしまうため。
    """
    mono_align_label = up.label.load(path_mono_align_lab)
    if mono_align_label[0].start != 0:
        warning_message = 'DB同梱のラベルの最初の音素開始時刻が0ではありません。0に修正して処理を続行します。({})'.format(
            basename(path_mono_align_lab))
        logging.warning(warning_message)
        mono_align_label[0].start = 0
        mono_align_label.write(path_mono_align_lab)


def offet_is_ok(path_mono_align_lab,
                path_mono_score_lab,
                threshold: Union[int, float] = 1) -> bool:
    """
    最初の音素の長さを比較して、閾値以上ずれていたらエラーを返す。
    """
    # 単位換算して100nsにする
    threshold_100ns = threshold * 10000000
    # labファイルを読み込む
    mono_align_label = up.label.load(path_mono_align_lab)
    mono_score_label = up.label.load(path_mono_score_lab)
    # 設定した閾値以上差があるか調べる
    if abs(mono_align_label[0].end - mono_score_label[0].end) >= threshold_100ns:
        warning_message = 'DB同梱のラベルと楽譜から生成したラベルの歌いだしの位置が {} 秒以上異なります。({})'.format(
            threshold, basename(path_mono_align_lab))
        logging.warning(warning_message)
        return False
    # 問題なければTrueを返す
    return True


def main(path_config_yaml):
    """
    全体の処理をやる。
    """
    with open(path_config_yaml, 'r') as fy:
        config = yaml.load(fy, Loader=yaml.FullLoader)
    out_dir = config['out_dir']
    mono_align_files = natsorted(glob(f'{out_dir}/mono_align_round/*.lab'))
    mono_score_files = natsorted(glob(f'{out_dir}/mono_score_round/*.lab'))

    # mono_align_labの最初の音素が時刻0から始まるようにする。
    print('Overwriting mono-align-LAB so that it starts with zero.')
    for path_mono_align in tqdm(mono_align_files):
        force_start_with_zero(path_mono_align)

    # 音素記号や最初の休符の長さが一致するか確認する。
    print('Comparing mono-align-LAB and mono-score-LAB')
    invalid_basenames = []
    for path_mono_align, path_mono_score in zip(tqdm(mono_align_files), mono_score_files):
        if not phoneme_is_ok(path_mono_align, path_mono_score):
            invalid_basenames.append(basename(path_mono_align))
    for path_mono_align, path_mono_score in zip(tqdm(mono_align_files), mono_score_files):
        if not offet_is_ok(path_mono_align, path_mono_score):
            invalid_basenames.append(basename(path_mono_align))
    if len(invalid_basenames) > 0:
        raise Exception('DBから生成したラベルと楽譜から生成したラベルに不整合があります。'
                        'ログファイルを参照して修正して下さい。')


if __name__ == '__main__':
    main(argv[1].strip('"'))
