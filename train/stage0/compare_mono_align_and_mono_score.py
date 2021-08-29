#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
"""
Sinsyの出力と音素数が一致するかだけをチェックする。
チェックに通過したら mono_label フォルダから mono_dtwフォルダにコピーする。

Shirani さんのレシピでは fastdtw を使って、
DB同梱のモノラベルをSinsy出力の音素と一致させる。
"""
import logging
import statistics
from glob import glob
from itertools import chain
# from os import makedirs
from os.path import basename
from sys import argv
from typing import List, Tuple, Union

import utaupy as up
import yaml
from natsort import natsorted
from tqdm import tqdm

VOWELS = {'a', 'i', 'u', 'e', 'o', 'A', 'I', 'U', 'E', 'O', 'N'}


def phoneme_is_ok(path_mono_align_lab, path_mono_score_lab):
    """
    音素数と音素記号が一致するかチェックする。
    """
    mono_align_label = up.label.load(path_mono_align_lab)
    mono_score_label = up.label.load(path_mono_score_lab)
    # 全音素記号が一致したらTrueを返す
    for mono_align_phoneme, mono_score_phoneme in zip(mono_align_label, mono_score_label):
        if mono_align_phoneme.symbol != mono_score_phoneme.symbol:
            error_message = '\n'.join([
                f'DB同梱のラベルと楽譜から生成したラベルの音素記号が一致しません。({basename(path_mono_align_lab)})',
                f'  DB同梱のラベル  : {mono_align_phoneme}\t({path_mono_align_lab})',
                f'  楽譜からのラベル: {mono_score_phoneme}\t({path_mono_score_lab})'
            ])
            logging.error(error_message)
            return False
    if len(mono_align_label) != len(mono_score_label):
        error_message = '\n'.join([
            f'DB同梱のラベルと楽譜から生成したラベルの音素数が一致しません。({basename(path_mono_align_lab)})',
            f'  DB同梱ラベルの音素数    : {len(mono_align_label)}\t({path_mono_align_lab})',
            f'  楽譜からのラベルの音素数: {len(mono_score_label)}\t({path_mono_score_lab})'
        ])
        logging.error(error_message)
        return False
    return True


def force_start_with_zero(path_mono_align_lab):
    """
    最初の音素(pau)の開始時刻を0にする。
    LABの元のiniの、左ブランクとか先行発声が動かされてると0ではなくなってしまうため。
    """
    mono_align_label = up.label.load(path_mono_align_lab)
    if mono_align_label[0].start != 0:
        warning_message = \
            'DB同梱のラベルの最初の音素開始時刻が0ではありません。0に修正して処理を続行します。({})'.format(
                basename(path_mono_align_lab))
        logging.warning(warning_message)
        mono_align_label[0].start = 0
        mono_align_label.write(path_mono_align_lab)


def calc_median_mean_pstdev(mono_align_lab_files: List[str],
                            mono_score_lab_files: List[str],
                            vowels=VOWELS
                            ) -> Tuple[int, int, int]:
    """
    ラベルと楽譜の母音のdurationの差の、統計値を求める。
    median: 中央値
    mean  : 平均値
    sigma : 標準偏差
    """
    # 全ラベルファイルを読み取る
    mono_align_label_objects = [up.label.load(path) for path in mono_align_lab_files]
    mono_score_label_objects = [up.label.load(path) for path in mono_score_lab_files]
    # Labelのリストを展開してPhonemeのリストにする
    mono_align_phonemes = list(chain.from_iterable(mono_align_label_objects))
    mono_score_phonemes = list(chain.from_iterable(mono_score_label_objects))
    # 母音以外を削除し、直後が休符なものも削除
    mono_align_phonemes = [
        phoneme for i, phoneme in enumerate(mono_align_phonemes[:-1])
        if (phoneme.symbol in vowels) and mono_align_phonemes[i + 1] not in ['cl', 'pau']
    ]
    mono_score_phonemes = [
        phoneme for i, phoneme in enumerate(mono_score_phonemes[:-1])
        if (phoneme.symbol in vowels) and mono_score_phonemes[i + 1] not in ['cl', 'pau']
    ]
    # durationの差の一覧
    duration_differences = [
        ph_align.duration - ph_score.duration
        for ph_align, ph_score in zip(mono_align_phonemes, mono_score_phonemes)
    ]
    # 中央値
    return (int(statistics.median(duration_differences)),
            int(statistics.mean(duration_differences)),
            int(statistics.pstdev(duration_differences)))


def offet_is_ok(path_mono_align_lab,
                path_mono_score_lab,
                mean_100ns: Union[int, float],
                stdev_100ns: Union[int, float],
                mode: str
                ) -> bool:
    """
    最初の音素の長さを比較して、閾値以上ずれていたらエラーを返す。
    threshold_ms の目安: 300ms-600ms (5sigma-10sigma)
    """
    k = {'strict': 5, 'medium': 6, 'lenient': 7}.get(mode, 6)
    # 単位換算して100nsにする
    upper_threshold = mean_100ns + k * stdev_100ns
    lower_threshold = mean_100ns - k * stdev_100ns
    # labファイルを読み込む
    mono_align_label = up.label.load(path_mono_align_lab)
    mono_score_label = up.label.load(path_mono_score_lab)
    # 設定した閾値以上差があるか調べる
    duration_difference = mono_align_label[0].duration - mono_score_label[0].duration
    if not lower_threshold < duration_difference < upper_threshold:
        warning_message = \
            'DB同梱のラベルの前奏が楽譜より {} ミリ秒以上早いか、{} ミリ秒以上長いです。({} ms) ({})'.format(
                round(lower_threshold / 10000),
                round(upper_threshold / 10000),
                round(duration_difference / 10000),
                basename(path_mono_align_lab)
            )
        logging.warning(warning_message)
        return False
    # 問題なければTrueを返す
    return True


def vowel_durations_are_ok(path_mono_align_lab,
                           path_mono_score_lab,
                           mean_100ns: Union[int, float],
                           stdev_100ns: Union[int, float],
                           mode: str,
                           vowels=VOWELS) -> bool:
    """
    母音の長さを比較して、楽譜中で歌詞ずれが起きていないかチェックする。
    閾値以上ずれていたら警告する。
    MIDIを自動生成するようなときに音素誤認識して、
    誤ったMIDIができてずれてることがあるのでその対策。

    threshold_ms の目安:  250 (5sigma-6sigma)
    - 優しめ: 6sigma
    - ふつう: 5sigma
    - 厳しめ: 4sigma
    """
    k = {'strict': 4, 'medium': 5, 'lenient': 6}.get(mode, 6)
    # 単位換算して100nsにする
    upper_threshold = mean_100ns + k * stdev_100ns
    lower_threshold = mean_100ns - k * stdev_100ns
    # labファイルを読み込む
    mono_align_label = up.label.load(path_mono_align_lab)
    mono_score_label = up.label.load(path_mono_score_lab)
    ok_flag = True
    # 休符を比較
    for i, (phoneme_align, phoneme_score) in enumerate(zip(mono_align_label[:-1], mono_score_label[:-1])):
        duration_difference = phoneme_align.duration - phoneme_score.duration
        if mono_align_label[i + 1].symbol in ['cl', 'pau']:
            continue
        if phoneme_align.symbol in vowels and not lower_threshold < duration_difference < upper_threshold:
            warning_message = '\n'.join([
                'DB同梱のラベルが楽譜から生成したラベルの母音より {} ミリ秒以上短いか、{} ミリ秒以上長いです。平均値 ± {}σ の範囲外です。({} ms) ({})'.format(
                    round(lower_threshold / 10000),
                    round(upper_threshold / 10000),
                    k,
                    round(duration_difference / 10000),
                    basename(path_mono_align_lab)),
                f'  直前の音素: {mono_align_label[i-1].symbol}',
                f'  DB同梱のラベル  : {phoneme_align}\t({phoneme_align.duration / 10000} ms)\t{path_mono_align_lab}',
                f'  楽譜からのラベル: {phoneme_score}\t({phoneme_score.duration / 10000} ms)\t{path_mono_score_lab}',
                f'  直後の音素: {mono_align_label[i+1].symbol}'
            ])
            logging.warning(warning_message)
            ok_flag = False
    return ok_flag


def main(path_config_yaml):
    """
    全体の処理をやる。
    """
    with open(path_config_yaml, 'r') as fy:
        config = yaml.load(fy, Loader=yaml.FullLoader)
    out_dir = config['out_dir']
    mono_align_files = natsorted(glob(f'{out_dir}/mono_align_round/*.lab'))
    mono_score_files = natsorted(glob(f'{out_dir}/mono_score_round/*.lab'))
    duration_check_mode = config['stage0']['vowel_duration_check']

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

    # 母音のdurationの統計値を取得
    print('Calculating median, mean and stdev of duration difference')
    _, mean_100ns, stdev_100ns = calc_median_mean_pstdev(
        mono_align_files, mono_score_files)

    # 前奏の長さを点検
    print('Checking first pau duration')
    for path_mono_align, path_mono_score in zip(tqdm(mono_align_files), mono_score_files):
        if not offet_is_ok(path_mono_align, path_mono_score,
                           mean_100ns, stdev_100ns, mode=duration_check_mode):
            invalid_basenames.append(basename(path_mono_align))
    if len(invalid_basenames) > 0:
        raise Exception('DBから生成したラベルと楽譜から生成したラベルに不整合があります。'
                        'ログファイルを参照して修正して下さい。')

    # 音素長をチェックする。
    print('Comparing mono-align-LAB durations and mono-score-LAB durations')
    for path_mono_align, path_mono_score in zip(tqdm(mono_align_files), mono_score_files):
        vowel_durations_are_ok(path_mono_align, path_mono_score,
                               mean_100ns, stdev_100ns, mode=duration_check_mode)


if __name__ == '__main__':
    main(argv[1].strip('"'))
