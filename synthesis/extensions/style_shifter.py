#!/usr/bin/env python3
# Copyright (c) 2022 oatsu
"""
USTの音高をずらして読み込んで、合成時にf0を本体の高さに戻すことで歌い癖をずらす。

1個のファイルでUST編集とf0編集ができるようにしたい。
UST読み込んで加工する際に、各ノートに独自エントリを書き込む。
USTにの [#SETTING] にすでに独自エントリがある場合はf0ファイルを編集する。
"""
import re
from argparse import ArgumentParser
from copy import copy
from math import log2
from pprint import pprint

import utaupy

STYLE_SHIFT_FLAG_PATTERN = re.compile(r'S(\d+|\+\d+|-\d+)')


def shift_ust_notes(ust) -> utaupy.ust.Ust:
    """フラグに基づいてUST内のノート番号をずらし、その分を独自エントリに追加する。
    """
    ust = copy(ust)
    key = '$EnunuStyleShift'
    ust.setting[key] = True
    for note in ust.notes:
        # フラグ内のスタイルシフトのパラメータを取得する
        style_shift = re.search(STYLE_SHIFT_FLAG_PATTERN, note.flags)
        # フラグにスタイルシフトのパラメータがあるとき
        if style_shift is not None:
            # フルラベルにするときの不具合の原因にならないように、フラグのスタイルシフト部分を削除する。
            note.flags = note.flags.replace(style_shift.group(), '')
            # 数値部分を取り出す
            style_shift_amount = int(style_shift.group(1))
            # スタイルシフト設定値の分だけノートの音高を下げる。
            note.notenum += int(style_shift_amount)
            # フラグのスタイルシフト値を独自エントリとしてノートに登録する。
            note[key] = '{:+}'.format(style_shift_amount)
        else:
            note[key] = 0

    return ust


def shift_f0(ust, full_timing, f0_list: list) -> list:
    """f0をいい感じに編集する
    """
    ust_notes = ust.notes
    hts_notes = full_timing.song.all_notes
    # ノート数が一致することを確認しておく
    if len(ust_notes) != len(hts_notes):
        raise ValueError(
            f'USTのノート数({len(ust_notes)}) と フルラベルのノート数({len(hts_notes)}) が一致していません。')

    # 各ノートのf0開始スライスと終了スライス
    f0_point_slices = [
        (round(note.start / 50000), round(note.end / 50000)) for note in hts_notes]

    # スタイルシフトの量をUSTのノートから取り出してリストにする
    style_shift_list = [
        int(note.get('$EnunuStyleShift', 0)) for note in ust_notes]

    # 計算しやすいように対数に変換
    log2_f0_list = [log2(hz) if hz > 0 else 0 for hz in f0_list]

    # f0のリストをノートごとに区切って2次元にする
    log2_f0_list_2d = [
        log2_f0_list[slice_start: slice_end] for (slice_start, slice_end) in f0_point_slices
    ]

    # ノート区切りごとにf0を調製して、新しいf0のリストを作る
    # このとき一番最初の開始時刻が0出ない時にf0点数が合わなくなるのを回避する。
    offset = round(hts_notes[0].start / 50000)
    new_log2_f0_list = log2_f0_list[0:offset]
    for f0_list_for_note, shift_amount in zip(log2_f0_list_2d, style_shift_list):
        delta_log2_f0 = shift_amount / (-12)
        new_log2_f0_list += [f0 + delta_log2_f0 if f0 >
                             0 else 0 for f0 in f0_list_for_note]
    # 書き換えたやつ対数から元に戻す
    new_f0_list = [
        (2 ** log2_f0 if log2_f0 > 0 else 0) for log2_f0 in new_log2_f0_list]
    return new_f0_list


def switch_mode(ust) -> str:
    """どのタイミングで起動されたかを、USTから調べて動作モードを切り替える。
    """
    if '$EnunuStyleShift' in ust.setting:
        return 'f0_editor'
    return 'ust_editor'


def main():
    parser = ArgumentParser()
    parser.add_argument('--ust', help='選択部分のノートのUSTファイルのパス')
    parser.add_argument('--f0', help='f0の情報を持ったCSVファイルのパス')
    parser.add_argument('--full_timing', help='タイミング推定済みのフルラベルファイルのパス')

    # 使わない引数は無視して、必要な情報だけ取り出す。
    args, _ = parser.parse_known_args()
    path_ust = args.ust

    ust = utaupy.ust.load(path_ust)

    # ust_editor として起動されたか、acoustic_editor として起動されたかを取得して動作切り替える
    mode = switch_mode(ust)

    # ust編集のステップで実行された場合、ustの音高操作などをする。
    if mode == 'ust_editor':
        print('USTの音高を加工します。/ Shifting notes in UST.')
        ust = shift_ust_notes(ust)
        ust.write(path_ust)
        print('USTの音高を加工しました。/ Shifted notes in UST.')

    # f0加工用に呼び出された場合、f0加工をする。
    elif mode == 'f0_editor':
        print('f0を加工します。/ Shifting f0.')
        # f0のファイルを読み取る
        path_f0 = args.f0
        with open(path_f0, 'r', encoding='utf-8') as f:
            f0_list = list(map(float, f.read().splitlines()))
        # フルラベルファイルを読み取る
        full_timing = utaupy.hts.load(args.full_timing)
        # f0を編集する
        new_f0_list = shift_f0(ust, full_timing, f0_list)
        new_f0_list = list(map(str, new_f0_list))
        s_f0 = '\n'.join(new_f0_list) + '\n'
        with open(path_f0, 'w', encoding='utf-8') as f:
            f.write(s_f0)
        print('f0を加工しました。/ Shifted f0.')

    # それ以外
    else:
        raise Exception('動作モードを判別できませんでした。')


if __name__ == "__main__":
    print('style_shifter.py (2022-09-24) -------------------------')
    main()
    print('-------------------------------------------------------')
