#! /usr/bin/env python3
# coding: utf-8
# Copyright (c) 2020 oatsu
"""
HTSフルコンテキストラベルをJSONと相互変換する。
"""

import re


def load(path: str, encoding='utf-8') -> dict:
    """
    HTSフルコンテキストラベル(Sinsy用)のファイルを読み取り、辞書にする。
    """
    # ファイルを読み取って行のリストにする
    try:
        with open(path, mode='r', encoding=encoding) as f:
            lines = [line.rstrip('\r\n') for line in f.readlines()]
    except UnicodeDecodeError:
        with open(path, mode='r', encoding='sjis') as f:
            lines = [line.rstrip('\r\n') for line in f.readlines()]
    return load_lines(lines)


def load_lines(lines: list) -> dict:
    """
    文字列のリスト(行のリスト)をもとに値を登録する。
    """
    # ラベル情報のリスト
    labels = []
    # HTSフルコンテキストラベルの各行を読み取っていく
    for line in lines:
        line_split = line.split(maxsplit=2)
        # 1行分の辞書
        d_line = {}
        # 時刻の情報 [発声開始時刻, 発声終了時刻]
        d_line['time'] = list(map(int, line_split[0:2]))
        # コンテキスト部分を取り出す
        str_contexts = line_split[2]
        # コンテキスト文字列を /A: などの文字列で区切って一次元リストにする
        l_contexts = re.split('/.:', str_contexts)
        # 特定の文字でさらに区切って二次元リストにする
        delimiters = re.escape('=+-~∼!@#$%^ˆ&;_|[]')
        l_contexts_2d = [re.split((f'[{delimiters}]'), s) for s in l_contexts]
        # 各種コンテキストを辞書に登録する
        d_line['p'] = l_contexts_2d[0]
        d_line['a'] = l_contexts_2d[1]
        d_line['b'] = l_contexts_2d[2]
        d_line['c'] = l_contexts_2d[3]
        d_line['d'] = l_contexts_2d[4]
        d_line['e'] = l_contexts_2d[5]
        d_line['f'] = l_contexts_2d[6]
        d_line['g'] = l_contexts_2d[7]
        d_line['h'] = l_contexts_2d[8]
        d_line['i'] = l_contexts_2d[9]
        d_line['j'] = l_contexts_2d[10]
        # ラベル情報のリストに追加
        labels.append(d_line)
    return {'labels': labels}


def export_flatjson(d: dict, path) -> str:
    """
    JSON文字列でファイル出力する。
    1音素1行
    """
    s = ',\n'.join([f'        {str(d_line)}' for d_line in d['labels']])
    s = s.replace('\'', '"').replace('{', '{ ').replace('}', ' }')
    s = '{\n    \"labels\": [\n' + s + '\n    ]\n}\n'
    with open(path, mode='w', encoding='utf-8', newline='\n') as f:
        f.write(s)
    return s


def hts2json(path_lab, path_json):
    """
    HTSフルコンテキストラベルファイル(.lab) を
    JSONファイル(.json) に変換する。
    """
    export_flatjson(load(path_lab), path_json)


if __name__ == '__main__':
    from sys import argv
    hts2json(argv[1], argv[2])
