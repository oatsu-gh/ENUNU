#! /usr/bin/env python3
# coding: utf-8
# Copyright (c) 2020 oatsu
"""
UTAUがresamplerを呼ぶときのコマンドを全部記録する。
エンジン代わりに実行する。
"""

from sys import argv
from pprint import pprint


def main(path_out):
    pprint(argv)
    s = ' '.join(argv) + '\n'
    with open(path_out, 'a', encoding='utf-8') as f:
        f.write(s)


if __name__ == '__main__':
    main('dummy2_result.txt')
    input()
