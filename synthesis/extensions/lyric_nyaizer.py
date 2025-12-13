#!/usr/bin/env python3
# Copyright (c) 2024 oatsu
"""
USTの全部の歌詞を ny a にする。
"""

from argparse import ArgumentParser

import utaupy


def main():
    """全体の処理をする
    """
    parser = ArgumentParser()
    parser.add_argument('--ust', help='選択部分のノートのUSTファイルのパス')
    # 使わない引数は無視して、必要な情報だけ取り出す。
    args, _ = parser.parse_known_args()
    path_ust = args.ust
    # ustファイルを読み取る
    ust = utaupy.ust.load(path_ust)

    # 表情音源のプレフィックス・サフィックスをvoicecolorの文字列として抽出する
    print('休符以外の歌詞をぜんぶ [ny a] にします。')
    notes = ust.notes
    for note in notes:
        if 'R' in note.lyric:
            note.lyric = 'R'
            print(' ', end='')
        else:
            note.lyric = 'ny a'
            print('nya', end='')
    print()
    # USTファイルを上書き
    ust.write(path_ust)
    print('休符以外の歌詞をぜんぶ [ny a] にしました。')


if __name__ == '__main__':
    print('lyric_nyaizer.py (2024-05-19) -------------------------')
    main()
    print('-------------------------------------------------------')
