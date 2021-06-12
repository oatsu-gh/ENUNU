#!/usr/bin/env python3
# Copyright (c) 2020 oatsu
"""
フルラベルを生成する。また、DB中のモノラベルを複製する。

- '{out_dir}/full_score' にフルラベルを生成する。
"""
from glob import glob
from os import makedirs
from os.path import basename, expanduser, splitext
from shutil import copy
from sys import argv

import pysinsy
import yaml
from nnmnkwii.io import hts
from tqdm import tqdm


def xml2full(path_xml_in, path_full_out, sinsy_dic_dir):
    """
    musicxmlファイルをフルラベルに変換する。
    """
    sinsy = pysinsy.sinsy.Sinsy()
    # かなローマ字変換用のファイルを読み取る
    assert sinsy.setLanguages('j', sinsy_dic_dir)
    # sinsyに楽譜を読ませて、読むのに失敗したらエラーになるようにする。
    assert sinsy.loadScoreFromMusicXML(path_xml_in)
    # フルラベルとしてSinsyからデータを受け取る
    labels = sinsy.createLabelData(False, 1, 1).getData()
    # フルラベルを入出力するためのオブジェクトを用意する。
    full_label = hts.HTSLabelFile()
    for label in labels:
        full_label.append(label.split(), strict=False)
    # ファイル出力する
    with open(path_full_out, 'w') as f:
        f.write(str(full_label))
    # Sinsyのメモリ解放
    sinsy.clearScore()


def main(path_config_yaml):
    """
    全体の処理をやる。
    """
    # 設定ファイルを読み取る
    with open(path_config_yaml, 'r') as fy:
        config = yaml.load(fy, Loader=yaml.FullLoader)
    db_root = expanduser(config['db_root']).strip('"')
    exclude_songs = config['exclude_songs']
    out_dir = config['out_dir'].strip('"')
    sinsy_dic_dir = config['sinsy_dic'].strip('"')

    # {out_dir}/.gitignoreファイルを作る。
    makedirs(f'{out_dir}', exist_ok=True)
    with open(f'{out_dir}/.gitignore', 'w') as f:
        f.write('*\n')

    # ラベルを出力するフォルダを用意
    makedirs(f'{out_dir}/sinsy_full', exist_ok=True)
    # 楽譜一覧を取得
    xml_files = sorted(glob(f'{out_dir}/xml/*.*xml') + glob(f'{out_dir}/musicxml/*.musicxml'))
    # LABファイル一覧を取得
    mono_labels = sorted(glob(f'{out_dir}/lab/*.lab', recursive=True))
    # 個数が合うか点検
    assert len(xml_files) == len(mono_labels), \
        f'MusicXMLファイル数({len(xml_files)})とLABファイル数({len(mono_labels)})が一致しません'

    # 楽譜をもとにフルラベルを生成
    print('Generating full label from musicxml -----')
    for path_xml in tqdm(xml_files):
        songname = splitext(basename(path_xml))[0]
        if songname in exclude_songs:
            continue
        path_full = (f'{out_dir}/sinsy_full/{songname}.lab')
        xml2full(path_xml, path_full, sinsy_dic_dir)


if __name__ == '__main__':
    print('----------------------------------------------------------------------')
    print('[ Stage 0 ] [ Step 1a ] Generate lab files from MusicXML files.')
    print('----------------------------------------------------------------------')
    main(argv[1])
