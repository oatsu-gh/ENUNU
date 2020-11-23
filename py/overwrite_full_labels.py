#! /usr/bin/env python3
# coding: utf-8
# Copyright (c) 2020 oatsu
"""
学習用のフルコンテキストラベルをENUNU向けに最適化する。
NNSVS用のレシピのステージ0とステージ1の間に割り込んで実行する想定。

1. フォルダを指定
2. フォルダ内の .lab 拡張子のファイルを再帰的に取得
3. utaupy.hts.HTSFullLabel として読み取る
4. 適当に書き換えて上書き保存
"""
from utaupy import hts


def edit_e2e3(full_label: hts.HTSFullLabel):
    """
    e2(相対音高)を編集する。
    e3(キー)は適当にやる。とりあえずenuenuに合わせて120にしておく。
    """
    for note in full_label.song:
        note.contexts[1] = (note.contexts[1] + note.contexts[2]) % 12
        note.contexts[2] = 120
    full_label.fill_contexts_from_songobj()


def main(path_lab):
    """
    LABファイルを読み取ってutaupy.htsの仕様に沿って上書きする。
    モノラベルがヒットすると死ぬ。
    """
    full_label = hts.load(path_lab)
    edit_e2e3(full_label)
    full_label.song.check()
    full_label.write(path_lab, strict_hts_style=False)


if __name__ == '__main__':
    from sys import argv
    main(argv[1])
