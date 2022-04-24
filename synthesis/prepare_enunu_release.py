#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
"""
ENUNUのリリース準備をする
"""

import shutil
import subprocess
from glob import glob
from os import makedirs
from os.path import basename, dirname, exists, isdir, join, splitext
from typing import List

KEEP_LATEST_PACKAGES = ['pip', 'setuptools', 'wheel', 'utaupy']
REMOVE_LIST = ['__pycache__', '.mypy']
PYTHON_DIR = 'python-3.8.10-embed-amd64'


def pip_install_upgrade(python_exe: str, packages: List[str]):
    """
    pythonのパッケージを更新する
    """
    args = [python_exe, '-m', 'pip', 'install', '--upgrade',
            '--no-warn-script-location'] + packages
    subprocess.run(args, check=True)


def remove_cache_files(path_dir, remove_list):
    """
    キャッシュファイルを削除する。
    """
    # キャッシュフォルダを再帰的に検索
    dirs_to_remove = [
        path for path in glob(join(path_dir, '**', '*'), recursive=True)
        if (isdir(path) and basename(path) in remove_list)
    ]
    # キャッシュフォルダを削除
    for cache_dir in dirs_to_remove:
        shutil.rmtree(cache_dir)


def copy_python_dir(python_dir, enunu_release_dir):
    """
    配布のほうにPythonをコピーする
    """
    shutil.copytree(python_dir, join(enunu_release_dir, python_dir))


def create_enunu_bat(path_out: str, python_exe: str):
    """
    プラグインの各フォルダに enunu.bat を作成する。
    """
    s = f'@echo off\n\n{python_exe} enunu.py %*\n\nPAUSE\n'
    with open(path_out, 'w', encoding='cp932') as f:
        f.write(s)


def create_install_txt(path_out: str, version: str):
    """
    プラグインの各フォルダに install.txt を作成する。
    """
    s = '\n'.join(['type=editplugin',
                   f'folder=ENUNU-{version}',
                   f'contentsdir=ENUNU-{version}',
                   'description=NNSVSモデルに歌ってもらうUTAUプラグイン'])
    with open(path_out, 'w', encoding='cp932') as f:
        f.write(s)


def create_plugin_txt(path_out, version):
    """
    プラグインの各フォルダに plugin.txt を作成する。
    """
    s = '\n'.join([f'name=ENUNU v{version} (&9)',
                   r'execute=.\enunu.bat'])
    with open(path_out, 'w', encoding='cp932') as f:
        f.write(s)


def copy_documents(path_out):
    """
    markdownドキュメントをリリースフォルダにコピーして、
    txtファイルに変換する。
    """
    documents = {'./../LICENSE',
                 './../README.md',
                 './../README_English.md',
                 './../HISTORY.md'}

    for old_path in documents:
        new_path = join(path_out, f'{basename(splitext(old_path)[0])}.txt')
        with open(old_path, 'r', encoding='utf-8') as f:
            s = f.read()
        if old_path.endswith('.md'):
            s = s.replace('\\', '')
        # markdownからバックスラッシュを除く
        with open(new_path, 'w', encoding='utf-8') as f:
            f.write(s)


def main():
    """
    全体的にいい感じにする
    """
    version = input('ENUNUのバージョンを入力してください。\n>>> ').lstrip('v')
    assert '.' in version

    # 既存フォルダを削除する
    old_dir = join('_release', f'ENUNU-{version}')
    if exists(old_dir):
        shutil.rmtree(old_dir)

    print('\n----------------------------------------------')

    # 配布物を入れるフォルダを新規作成する
    enunu_release_dir = join(
        '_release', f'ENUNU-{version}', f'ENUNU-{version}')
    print(f'Making directory: {enunu_release_dir}')
    makedirs(enunu_release_dir)

    # README をリリースフォルダにコピーする
    print('Copying documents')
    copy_documents(enunu_release_dir)

    # utaupyとかを更新する
    python_dir = PYTHON_DIR
    python_exe = join(python_dir, 'python.exe')
    print(f'Upgrading packages of {python_dir} (this may take some minutes)')
    pip_install_upgrade(python_exe, KEEP_LATEST_PACKAGES)
    print()

    # Pythonの実行ファイルをコピーする
    print(f'Copying {python_dir} -> {join(enunu_release_dir, python_dir)}')
    shutil.copytree(python_dir, join(enunu_release_dir, python_dir))

    # キャッシュファイルを削除する
    print('Removing cache')
    remove_cache_files(enunu_release_dir, REMOVE_LIST)

    # enunu.py と hts2wav.py と nnsvs_gen_override.py をコピーする
    print('Copying python scripts')
    shutil.copy2('enunu.py', join(enunu_release_dir))
    shutil.copy2('install_torch.py', join(enunu_release_dir))
    shutil.copytree('enulib', join(enunu_release_dir, 'enulib'))
    shutil.copytree('extensions', join(enunu_release_dir, 'extensions'))

    # enunu.bat をリリースフォルダに作成
    print('Creating enunu.bat')
    create_enunu_bat(join(enunu_release_dir, 'enunu.bat'),  python_exe)

    # plugin.txt をリリースフォルダに作成
    print('Creating plugin.txt')
    create_plugin_txt(join(enunu_release_dir, 'plugin.txt'), version)

    # install.txt を作る
    path_install_txt = join(dirname(enunu_release_dir), 'install.txt')
    create_install_txt(path_install_txt, version)

    print('\n----------------------------------------------')


if __name__ == '__main__':
    main()
    input('Press Enter to exit.')
