#!/usr/bin/env python3
# Copyright (c) 2022 oatsu
"""
ENUNUで合成したf0をUTAUのピッチ曲線としてフィードバックする。
"""

from math import log2

import numpy as np
import utaupy
from scipy.signal import argrelmax, argrelmin

FRAME_PERIOD = 5  # ms
F0_FLOOR = 32


def load_f0(path_f0, frame_period=FRAME_PERIOD):
    """f0のファイルを読み取って、周波数と時刻(ms)の一覧を返す。
    """
    with open(path_f0, 'r', encoding='utf-8') as f:
        freq_list = list(map(float, f.read().splitlines()))
    time_list = [i*frame_period for i in range(len(freq_list))]
    return freq_list, time_list


def distribute_f0(freq_list, time_list, ust):
    """周波数とその時刻の情報をノートごとに分割する。
    """
    # 要素数が一致していることを確認しておく。
    assert len(freq_list) == len(time_list)
    len_f0 = len(freq_list)

    # ループ時にノートの終了時刻を記憶するための変数
    t_note_end = 0
    # ループ時にf0のインデックスを記憶するための変数
    idx_f0 = 0
    # 各ノートごとに分割されたf0とその時刻を保持するためのリスト。
    f0_freq_for_each_note = []
    f0_time_for_each_note = []

    # ノートごとにループする。
    # 最後のf0点が使用されない可能性があることに注意。
    for note in ust.notes:
        t_note_end += note.length_ms
        temp_f0_freq = []
        temp_f0_time = []
        # f0の時刻を前から順番に調べて、ノート内だったら一時リストに追加
        while time_list[idx_f0] < t_note_end and idx_f0 < len_f0:
            temp_f0_freq.append(freq_list[idx_f0])
            temp_f0_time.append(time_list[idx_f0])
            idx_f0 += 1
            # 最後の点を処理したらループを抜ける
            if idx_f0 == len_f0:
                break
        # 最後の点を次のノートにも重複して追加するために、インデックスを一つ下げる
        idx_f0 -= 1
        # 現在のノートに対するf0とその時刻のリストを、全体のリストに追加
        f0_freq_for_each_note.append(temp_f0_freq)
        f0_time_for_each_note.append(temp_f0_time)

    return f0_freq_for_each_note, f0_time_for_each_note


def reduce_f0_points_for_a_note(f0_list, time_list):
    """ノート内のf0点を削減する。

    UTAUのGUI上に表示できるピッチ密度には限界があるため、
    各ノートの以下のピッチ点になるものだけ残す。
    - ノート内で最初の点
    - ノート内で最後の点
    - 極大値と極小値と変曲点
    """
    # 点数が一致することを確認しておく
    assert len(f0_list) == len(time_list)

    # 1階微分
    delta_f0_freq = [0]  # 最初の点は勾配を計算できないので0
    delta_f0_freq += [
        next_freq - prev_freq for next_freq, prev_freq
        in zip(f0_list[:-1], f0_list[1:])
    ]
    delta_f0_freq += [0]  # 最後の点も勾配を計算できないので0

    # 極値のindexを取り出す
    extremum_f0_indices = \
        list(argrelmax(np.array(f0_list))[0]) + \
        list(argrelmin(np.array(f0_list))[0])
    # 最初と最後と極値のindex (残すf0点のみ)
    reduced_f0_indices = [0] + extremum_f0_indices + [len(f0_list) - 1]

    # 変曲点を使う場合↓------------------------------------
    # # 変曲点のindexを取り出す
    # inflection_f0_indices = \
    #     list(argrelmax(np.array(delta_f0_freq))[0]) + \
    #     list(argrelmin(np.array(delta_f0_freq))[0])
    # 最初と最後と極値と変曲点のindex (残すf0点のみ)
    # reduced_f0_indices = [0] + extremum_f0_indices + \
    # inflection_f0_indices + [len(f0_list) - 1]
    # -------------------------------------------------------

    # 重複する要素を削除
    reduced_f0_indices = list(set(reduced_f0_indices))
    # 順番がめちゃくちゃなので並べなおす
    reduced_f0_indices.sort()

    # 残したいf0の周波数
    l_reduced_f0_freq = [f0_list[i] for i in reduced_f0_indices]
    # 残したいf0の時刻
    l_reduced_f0_time = [time_list[i] for i in reduced_f0_indices]

    return l_reduced_f0_freq, l_reduced_f0_time


def notenum2hz(notenum: int, concert_pitch=440) -> float:
    """UTAUの音階番号を周波数に変換する
    """
    return concert_pitch * (2 ** ((notenum - 69) / 12))


def hz2cent(freq: float, notenum: int):
    """f0の周波数をUST用のPBY用の数値に変換する
    """
    base_hz = notenum2hz(notenum)
    if freq == 0:
        cent = 0
    else:
        cent = 120.0 * (log2(freq) - log2(base_hz))
    return cent


def note_times_ms(ust):
    """ノートの開始時刻(ms)と終了時刻(ms)のリストを返す。
    [[start, end], ...]
    """
    t_start = 0  # ノート開始時刻
    t_end = 0   # ノート終了時刻
    l_start_end = []  # 開始時刻と終了時刻のリスト

    # 各ノートの長さから、開始時刻と終了時刻を計算する
    for note in ust.notes:
        t_end += note.length_ms
        l_start_end.append([t_start, t_end])

    # リストを返す
    return l_start_end


def test():
    """Test
    """
    # USTファイルを読み取る
    path_ust = input('USTファイルを指定してください: ').strip('"')
    ust = utaupy.ust.load(path_ust)

    # f0ファイルを読み取る
    path_f0 = input('f0ファイルを指定してください: ').strip('"')
    freq_list, time_list = load_f0(path_f0)

    # ノートごとになるようにf0を分割して2次元リストにする
    print('ピッチ点をノートごとに分割します。')
    freq_list_2d, time_list_2d = distribute_f0(freq_list, time_list, ust)

    # 削減後のリストとか
    reduced_freq_list_2d = []
    reduced_time_list_2d = []

    # 各ノートのf0点を削減する
    print('ピッチ点を削減します。')
    for freq_list_for_a_note, time_list_for_a_note in zip(freq_list_2d, time_list_2d):
        l_freq, l_time = reduce_f0_points_for_a_note(
            freq_list_for_a_note, time_list_for_a_note
        )
        reduced_freq_list_2d.append(l_freq)
        reduced_time_list_2d.append(l_time)

    # 各ノートのピッチ点を登録する
    assert len(ust.notes) == len(
        reduced_freq_list_2d) == len(reduced_time_list_2d)
    print('各ノートにPBYとPBWとPBMを登録します。')
    for note, l_freq, l_time in zip(ust.notes, reduced_freq_list_2d, reduced_time_list_2d):
        notenum = note.notenum
        # PBSを仮登録
        note.pbs = [0, 0]
        # 相対音高(cent)を計算してPBYを登録
        note.pby = [hz2cent(freq, notenum) for freq in l_freq] + [0]
        # 時刻を計算してPBWを登録
        note.pbw = [0] + [t_next - t_now for t_now, t_next
                          in zip(l_time[:-1], l_time[1:])] + [0]
        # 全てS字で登録
        note.pbm = [''] * (len(l_freq) + 1)

    # PBSを計算して適切に登録しなおす
    print('各ノートにPBYとPBWとPBMを登録します。')
    for note, note_prev in zip(ust.notes[1:], ust.notes[:-1]):
        # 直前のノートのピッチ点が終わる時刻と 直前のノートが終わる時刻の差が
        # 今のノートのPBS
        offset = (note_prev.pbs[0] + sum(note_prev.pbw)) - note_prev.length_ms
        note.pbs = [offset, 0]

    # ファイル出力
    print('完了しました。上書き保存します。')
    path_ust_out = path_ust.replace('.ust', '_out.ust')
    ust.setting['Mode2'] = True
    ust.write(path_ust_out)


if __name__ == "__main__":
    test()
