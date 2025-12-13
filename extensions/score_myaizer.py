#!/usr/bin/env python3
# Copyright (c) 2024 oatsu
"""
LAB (score) の全部の歌詞を my a にする。
"""

from argparse import ArgumentParser

import utaupy


def main():
    """全体の処理をする
    """
    parser = ArgumentParser()
    parser.add_argument('--full_score', help='USTから生成したLABファイルのパス')
    # 使わない引数は無視して、必要な情報だけ取り出す。
    args, _ = parser.parse_known_args()
    path_full_score = args.full_score
    # ustファイルを読み取る
    full_score = utaupy.hts.load(path_full_score)

    # 表情音源のプレフィックス・サフィックスをvoicecolorの文字列として抽出する
    print('[pau] と [N] はそのままにします。母音は [a] にします。それ以外は [my] にします。')
    song = full_score.song
    phonemes = song.all_phonemes
    for phoneme in phonemes:
        if phoneme.is_rest():
            continue
        if phoneme.identity == 'N':
            continue
        if phoneme.is_vowel():
            phoneme.identity = 'a'
            continue
        phoneme.identity = 'my'
    # LABファイルを上書き
    song.write(path_full_score)
    print('[pau] と [N] はそのままにしました。母音は [a] にしました。それ以外は [my] にしました。')


if __name__ == '__main__':
    print('score_myaizer.py (2024-07-07) -------------------------')
    main()
    print('-------------------------------------------------------')
