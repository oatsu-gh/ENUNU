#! /usr/bin/env python3
# coding: utf-8
# Copyright (c) 2020 oatsu
"""
学習用のフルコンテキストラベルをENUNU向けに最適化する。
NNSVS用のレシピのステージ0とステージ1の間に割り込んで実行する想定。
→【変更】lab作成直後に実行する。切断後だと休符の情報が失われる。

1. フォルダを指定
2. フォルダ内の .lab 拡張子のファイルを再帰的に取得
3. utaupy.hts.HTSFullLabel として読み取る
4. 適当に書き換えて上書き保存
"""
from hts2json import hts2json
from utaupy import hts


def edit_e2e3(full_label: hts.HTSFullLabel):
    """
    e2(相対音高)を編集する。
    e3(キー)は適当にやる。とりあえずenuenuに合わせて120にしておく。
    """
    for note in full_label.song:
        try:
            note.contexts[1] = (int(note.contexts[1]) + int(note.contexts[2])) % 12
            note.contexts[2] = 120
        except ValueError as e:
            print(e)
    full_label.fill_contexts_from_songobj()


def modify_full_label_for_enuenu(path_lab_in, path_lab_out):
    """
    LABファイルを読み取ってutaupy.htsの仕様に沿って上書きする。
    モノラベルがヒットすると死ぬ。
    """
    hts2json(path_lab_in, path_lab_in.replace('.lab', '.json'))
    full_label = hts.load(path_lab_in)
    edit_e2e3(full_label)
    full_label.song.check()
    full_label.write(path_lab_out, strict_hts_style=False)
    hts2json(path_lab_out, path_lab_out.replace('.lab', '.json'))


def main():
    """
    直接実行された時の処理。
    ファイルを指定して変換する。
    """
    path_lab_in = input('path_lab_in: ').strip('"')
    path_lab_out = path_lab_in.replace('.lab', '_enuenu.lab')
    modify_full_label_for_enuenu(path_lab_in, path_lab_out)


if __name__ == '__main__':
    main()
