#!/usr/bin/env python3
# Copyright (c) 2022 oatsu
"""
USTに記載されている子音速度を用いて、timingラベルの子音の長さを調節する。

本ツール作成時のutaupyのバージョンは 1.17.0
"""

from argparse import ArgumentParser

import colored_traceback.always  # pylint: disable=unused-import
import utaupy


def get_velocities(ust):
    """USTを読み取って子音速度のリストを返す。
    """
    return tuple(note.velocity for note in ust.notes)


def calculate_consonant_magnification(velocity):
    """子音速度を倍率に変換する。
    """
    return 2 ** ((100 - velocity) / 100)


def repair_label(path_label, time_unit=50000):
    """発声開始時刻が直前のノートの発声開始時刻より早くなっている音素を直す。
    """
    label = utaupy.label.load(path_label)
    previous_start = label[0].start
    for phoneme in label:
        current_start = phoneme.start
        phoneme.start = max(previous_start + time_unit, current_start)
        previous_start = current_start
    label.write(path_label)


def apply_velocities_to_timing_full_label(path_full_timing, path_ust):
    """フルラベルファイルにUSTファイルの子音速度を適用する。
    """
    ust = utaupy.ust.load(path_ust)
    song = utaupy.hts.load(path_full_timing).song
    # ノート数が一致しないと処理できないのでエラー
    if len(ust.notes) != len(song.all_notes):
        raise ValueError(
            f'USTのノート数 ({len(ust.notes)} notes) とtimingラベルのノート数 ({len(song.all_notes)}) が一致しません。/ Numbers of notes in UST ({len(ust.notes)}) and in Timing-label ({len(song.all_notes)} notes) do not match.'
        )
    # 子音速度を取得する
    velocities = get_velocities(ust)
    # 子音の長さを加工していく。
    for hts_note, velocity in zip(song.all_notes, velocities):
        phoneme = hts_note.phonemes[0]
        # 最初の音素が子音だった場合、子音速度に応じて長さを調節する。
        if phoneme.is_consonant():
            duration = phoneme.duration
            # print(
            #     f'Applying consonant velocity: {duration} -> ', end='')
            duration = round(
                duration * calculate_consonant_magnification(velocity))
            # print(duration)
            # 発声開始時刻を上書き
            phoneme.start = phoneme.end - duration
    # 発声終了時刻を再計算
    song.reload_time()
    # ファイル出力
    song.write(path_full_timing)
    # 時刻の逆転が起きている部分を直す。
    repair_label(path_full_timing)


if __name__ == "__main__":
    print('velocity_applier.py------------------------------------')
    print('子音速度をタイミングラベルに反映しました。/ Applying velocity to timing.')
    parser = ArgumentParser()
    parser.add_argument('--ust', help='USTファイルのパス')
    parser.add_argument('--full_timing', help='発声タイミングの情報を持ったHTSフルラベルファイルのパス')
    # 使わない引数は無視
    args, _ = parser.parse_known_args()
    # 実行引数を渡して処理
    apply_velocities_to_timing_full_label(
        path_full_timing=args.full_timing,
        path_ust=args.ust
    )
    print('子音速度をタイミングラベルに反映しました。/ Applied velocity to timing.')
    print('-------------------------------------------------------')
