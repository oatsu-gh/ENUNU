#!/usr/bin/env python3
# Copyright (c) 2022 oatsu
"""
発声開始時刻が逆転してエラーになるのを修復する。
"""

from argparse import ArgumentParser

import utaupy
from tqdm import tqdm


def repair_label(path_label, time_unit=50000):
    """発声開始時刻が直前のノートの発声開始時刻より早くなっている音素を直す。"""
    label = utaupy.label.load(path_label)
    previous_start = label[0].start
    for phoneme in tqdm(label):
        current_start = phoneme.start
        phoneme.start = max(previous_start + time_unit, current_start)
        previous_start = current_start
    label.write(path_label)


if __name__ == '__main__':
    print('timing_repairer.py------------------------------------')
    parser = ArgumentParser()
    parser.add_argument(
        '--mono_timing', help='発声タイミングの情報を持ったHTSフルラベルファイルのパス'
    )
    # 使わない引数は無視
    args, _ = parser.parse_known_args()
    # 実行引数を渡して処理
    repair_label(path_label=args.mono_timing)
    print('-------------------------------------------------------')
