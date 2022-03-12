#!/usr/bin/env python3
# Copyright (c) 2022 oatsu
"""
ENUNUの拡張機能のダミースクリプト
"""
from os import getcwd
from sys import argv


def main():
    print(argv)
    print(getcwd())
    input('waiting')


if __name__ == '__main__':
    main()
