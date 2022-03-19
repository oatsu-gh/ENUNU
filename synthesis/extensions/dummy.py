#!/usr/bin/env python3
# Copyright (c) 2022 oatsu
"""
ENUNUの拡張機能のダミースクリプト
"""
from os import getcwd
from pprint import pprint
from sys import argv


def main():
    print("dummy.py--------------------")
    pprint(argv)
    pprint(getcwd())
    print("----------------------------")


if __name__ == '__main__':
    main()
