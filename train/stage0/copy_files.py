#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
"""
歌唱DBから必要そうなファイルを全てコピーする。
USTとMusicXMLとLABとWAVとINI
"""

import shutil
from glob import glob
from os import makedirs
from os.path import expanduser, join
from sys import argv

import yaml
from tqdm import tqdm


def copy_target_files(db_root, out_dir, ext):
    """
    拡張子を指定して、ファイルを複製する。
    """
    target_files = glob(f'{db_root}/**/*.{ext}', recursive=True)
    if len(target_files) != 0:
        makedirs(join(out_dir, ext), exist_ok=True)
        print(f'Copying {ext} files')
        for path in tqdm(target_files):
            shutil.copy2(path, join(out_dir, ext))


def make_gitignore(out_dir):
    """
    {out_dir}/.gitignoreファイルを作る。
    """
    makedirs(f'{out_dir}', exist_ok=True)
    with open(f'{out_dir}/.gitignore', 'w') as f:
        f.write('*\n')


def main(path_config_yaml):
    """
    設定ファイルを読み取って、使いそうなファイルを複製する。
    """
    # 設定ファイルを読み取る
    with open(path_config_yaml, 'r') as fy:
        config = yaml.load(fy, Loader=yaml.FullLoader)
    # 歌唱DBのパスを取得
    db_root = expanduser(config['stage0']['db_root']).strip('"')
    # ファイルのコピー先を取得
    out_dir = config['out_dir'].strip('"')

    make_gitignore(out_dir)
    # 移動元と移動先を標準出力
    print(f'Copy files from "{db_root}" to "{out_dir}"')
    # ファイルをコピー
    target_extensions = ('wav', 'xml', 'musicxml', 'ust', 'ini', 'lab')
    for ext in target_extensions:
        copy_target_files(db_root, out_dir, ext)


if __name__ == '__main__':
    main(argv[1].strip('"'))
