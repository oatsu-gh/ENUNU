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
from glob import glob
from sys import argv

import yaml
from hts2json import hts2json
# from tqdm import tqdm
from utaupy import hts


def edit_e2e3(full_label: hts.HTSFullLabel):
    """
    e2(相対音高)を編集する。
    e3(キー)は適当にやる。とりあえずenuenuに合わせて120にしておく。
    """
    for note in full_label.song:
        if 'xx' not in (note.contexts[1], note.contexts[2]):
            note.contexts[1] = (int(note.contexts[1]) + int(note.contexts[2])) % 12
        note.contexts[2] = 120
    full_label.fill_contexts_from_songobj()


def modify_full_label_for_enuenu(path_lab_in, path_lab_out):
    """
    LABファイルを読み取ってutaupy.htsの仕様に沿って上書きする。
    モノラベルがヒットすると死ぬ。
    """
    full_label = hts.load(path_lab_in)
    edit_e2e3(full_label)
    full_label.song.check()
    full_label.write(path_lab_out, strict_sinsy_style=False)


def main_manual():
    """
    直接実行された時の処理。
    ファイルを指定して変換する。
    """
    path_lab_in = input('path_lab_in: ').strip('"')
    path_lab_out = path_lab_in.replace('.lab', '_enuenu.lab')
    hts2json(path_lab_in, path_lab_in.replace('.lab', '.json'))
    modify_full_label_for_enuenu(path_lab_in, path_lab_out)
    hts2json(path_lab_out, path_lab_out.replace('.lab', '.json'))



def main_auto(path_config_yaml: str):
    """
    NNSVSの学習時に呼び出されるのを想定。
    特定のフォルダ内にあるlabファイルをすべて処理する。
    """
    print('Modify label files for ENUENU.')
    # pathなどの設定があるファイルを読み取る
    with open(path_config_yaml, 'r') as f_yaml:
        config = yaml.load(f_yaml, Loader=yaml.FullLoader)
    out_dir = config['out_dir']
    # 処理すべきファイルを取得
    full_label_files = glob(f'{out_dir}/sinsy_full/*.lab')
    full_label_files += glob(f'{out_dir}/sinsy_full_round/*.lab')
    # ラベルを書き換えて上書き
    for path_full_label in full_label_files:
        print(f'  {path_full_label}')
        modify_full_label_for_enuenu(path_full_label, path_full_label)
        hts2json(path_full_label, path_full_label.replace('.lab', '.json'))


if __name__ == '__main__':
    from datetime import datetime
    print(datetime.now())
    if len(argv) == 1:
        main_manual()
    elif len(argv) == 2:
        main_auto(argv[1])
    else:
        raise TypeError(f'USAGE: {argv[0]} path_config_yaml')
    print(datetime.now())
