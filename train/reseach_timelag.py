#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
"""
label_phone_align と label_phone_score から統計値を計算する。
timelag と duration をざっくり計算する。
全部、母音、子音、休符 くらいのざっくり加減で。
"""
from glob import glob
from itertools import chain
from os.path import basename

import utaupy
from tqdm import tqdm

# VOWELS = ('a', 'i', 'u', 'e', 'o', 'A', 'I', 'U', 'E', 'O', 'N')


def load_labels(label_dir) -> utaupy.label.Label:
    """
    フォルダを指定してラベルオブジェクトを一気に取得する。
    """
    lab_files = sorted(glob(f'{label_dir}/*.lab'))
    label_objects = [utaupy.hts.load(path).as_mono() for path in tqdm(lab_files)]
    new_label = utaupy.label.Label()
    new_label.data = list(chain.from_iterable(label_objects))
    return new_label


def timelag_and_duration_difference(path_lab_align, path_lab_score):
    """
    時刻差分を計算して返す
    """
    lab_align = utaupy.hts.load(path_lab_align).as_mono()
    lab_score = utaupy.hts.load(path_lab_score).as_mono()

    lines = []
    songname = basename(path_lab_align)
    for ph_align, ph_score in zip(lab_align, lab_score):
        timelag_ms = (ph_align.start - ph_score.start) / 10000
        duration_difference_ms = (ph_align.duration - ph_score.duration) / 10000
        lines.append(f'{timelag_ms},{duration_difference_ms},{ph_align.symbol},{songname}')
    return lines


def main():
    """
    フォルダ指定とかする
    """
    timelag_dir = input('timelag_dir: ').strip('"')

    lab_align_files = sorted(glob(f'{timelag_dir}/label_phone_align/*.lab'))
    lab_score_files = sorted(glob(f'{timelag_dir}/label_phone_score/*.lab'))

    lines = ['timelag,duration_difference,phoneme,filename']
    for path_lab_align, path_lab_score in zip(tqdm(lab_align_files), lab_score_files):
        lines += timelag_and_duration_difference(path_lab_align, path_lab_score)

    with open('result.csv', 'w') as f:
        f.write('\n'.join(lines))

    # # 全音素
    # mono_score_phonemes = list(chain.from_iterable(mono_score_label_objects))
    # mono_align_phonemes = list(chain.from_iterable(mono_align_label_objects))
    #
    # timelag_data_ms = [
    #     (ph_score.start - ph_align.start) / 10000
    #     for (ph_align, ph_score) in tqdm(zip(mono_align_phonemes, mono_score_phonemes))
    #     if ph_score.symbol != 'pau'
    # ]
    # duration_difference_data_ms = [
    #     (ph_align.duration - ph_score.duration) / 10000
    #     for (ph_align, ph_score) in tqdm(zip(mono_align_phonemes, mono_score_phonemes))
    #     if ph_score.symbol != 'pau'
    # ]
    #
    # print('timelag (without pau)---------------------')
    # with open('all_timelag.csv', 'w') as f:
    #     f.write('\n'.join(map(str, timelag_data_ms)))
    # print('  中央値  [ms]:', round(statistics.median(timelag_data_ms)))
    # print('  平均値  [ms]:', round(statistics.mean(timelag_data_ms)))
    # print('  標準偏差[ms]:', round(statistics.pstdev(timelag_data_ms)))
    # print('timelag-----------------------------------')
    #
    # print('')
    # print('duration_difference (without pau)---------')
    # with open('all_duration_differences.csv', 'w') as f:
    #     f.write('\n'.join(map(str, duration_difference_data_ms)))
    # print('  中央値  [ms]:', round(statistics.median(duration_difference_data_ms)))
    # print('  平均値  [ms]:', round(statistics.mean(duration_difference_data_ms)))
    # print('  標準偏差[ms]:', round(statistics.pstdev(duration_difference_data_ms)))
    # print('duration_difference-----------------------')
    # print('')
    #
    # timelag_data_ms = [
    #     (ph_score.start - ph_align.start) / 10000
    #     for (ph_align, ph_score) in zip(mono_align_phonemes, mono_score_phonemes)
    #     if ph_score.symbol == 'pau'
    # ]
    # duration_difference_data_ms = [
    #     (ph_align.duration - ph_score.duration) / 10000
    #     for (ph_align, ph_score) in zip(mono_align_phonemes, mono_score_phonemes)
    #     if ph_score.symbol == 'pau'
    # ]
    # print('timelag(pau)------------------------------')
    # with open('pau_timelag.csv', 'w') as f:
    #     f.write('\n'.join(map(str, timelag_data_ms)))
    # print('  中央値  [ms]:', round(statistics.median(timelag_data_ms)))
    # print('  平均値  [ms]:', round(statistics.mean(timelag_data_ms)))
    # print('  標準偏差[ms]:', round(statistics.pstdev(timelag_data_ms)))
    # print('timelag----------------------------------')
    #
    # print('')
    # print('duration_difference(pau)-----------------')
    # with open('pau_duration_differences.csv', 'w') as f:
    #     f.write('\n'.join(map(str, duration_difference_data_ms)))
    # print('  中央値  [ms]:', round(statistics.median(duration_difference_data_ms)))
    # print('  平均値  [ms]:', round(statistics.mean(duration_difference_data_ms)))
    # print('  標準偏差[ms]:', round(statistics.pstdev(duration_difference_data_ms)))
    # print('duration_difference---------------------')

    input('おわり')


if __name__ == '__main__':
    main()
