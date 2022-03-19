#!/usr/bin/env python3
# Copyright (c) 2022 oatsu
"""
timelagラベルとdurationラベルを合わせてtimingラベルにする。
"""
import numpy as np
import utaupy
from nnmnkwii.io import hts
from nnsvs.gen import postprocess_duration

TIMING_ARRAY_DTYPE = np.float32


def get_timelag_array(path_full_timelag):
    """timelagのフルラベルを読み取る。

    ノートの先頭の音素の値だけを取得して、行列にして返す。
    """
    # full_timelag を読んだあと必要な部分だけ抜き出す
    song = utaupy.hts.load(path_full_timelag).song
    timelag_array = np.array(
        [[note.start] for note in song.all_notes],
        dtype=TIMING_ARRAY_DTYPE
    )
    return timelag_array


def get_duration_array(path_full_duration):
    """
    durationのフルラベルを読み取って、行列にして返す。
    """
    duration_labels = hts.load(path_full_duration).round_()
    # そのままだと100ns単位なので5ms単位に直す。
    duration_array = np.array(
        [[round(t_start / 50000)] for t_start in duration_labels.start_times],
        dtype=TIMING_ARRAY_DTYPE
    )
    return duration_array


def generate_timing_label(path_score, path_timelag, path_duration, path_timing):
    """nnsvs.synthesis.postprocess_duration を使ってtimelagとdurationをがっちゃんこする。
    ファイル指定で入出力する。
    """
    # full_score を読む
    score_label = hts.load(path_score).round_()

    # full_timelag を読んだあと必要な部分だけ抜き出す
    timelag = get_timelag_array(path_timelag)
    # full_duration を読んだあと必要な部分だけ抜き出す
    duration = get_duration_array(path_duration)

    # よくわかってないけど何かいい感じにくっつけてくれる
    # Normalize phoneme durations
    duration_modified_labels = postprocess_duration(
        score_label, duration, timelag)
    # ファイル出力する
    with open(path_timing, 'w', encoding='utf-8') as f:
        f.write(str(duration_modified_labels))
