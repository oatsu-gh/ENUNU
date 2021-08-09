#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
"""
ENUNUのリリース準備をする
"""

import shutil
import subprocess
from glob import glob
from os import makedirs
from os.path import basename, dirname, exists, isdir, join
from typing import List

DEVICES = ['cpu', 'cuda102', 'cuda111']
KEEP_LATEST_PACKAGES = ['pip', 'wheel', 'utaupy', 'nnmnkwii']
REMOVE_LIST = ['__pycache__', '.mypy']


def pip_install_upgrade(python_exe: str, packages: List[str]):
    """
    pythonのパッケージを更新する
    """
    args = [python_exe, '-m', 'pip', 'install', '--upgrade'] + packages
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
    s = f'{python_exe} enunu.py %*\n\nPAUSE\n'
    with open(path_out, 'w') as f:
        f.write(s)


def create_install_txt(path_out: str, version: str, device: str):
    """
    プラグインの各フォルダに install.txt を作成する。
    """
    s = '\n'.join(['type=editplugin',
                   f'folder=enunu-{version}-{device}',
                   f'contentsdir=enunu-{version}-{device}',
                   'description=NNSVSモデルに歌ってもらうUTAUプラグイン'])
    with open(path_out, 'w') as f:
        f.write(s)


def create_plugin_txt(path_out, version, device):
    """
    プラグインの各フォルダに plugin.txt を作成する。
    """
    s = '\n'.join([f'name=ENUNU v{version} ({device.uppee()}) (&9)',
                   r'execute=.\enunu.bat'])
    with open(path_out, 'w') as f:
        f.write(s)


def main():
    """
    全体的にいい感じにする
    """
    version = input('ENUNUのバージョンを入力してください。\n>>> ')
    assert '.' in version

    # 既存フォルダを削除する
    for device in ['cpu', 'cuda102', 'cuda111']:
        old_dir = join('_release', f'ENUNU-{version}-{device}')
        if exists(old_dir):
            shutil.rmtree(old_dir)

    for device in ['cpu', 'cuda102', 'cuda111']:
        print('\n----------------------------------------------')

        # 配布物を入れるフォルダを新規作成する
        enunu_release_dir = join(
            '_release', f'ENUNU-{version}-{device}', f'ENUNU-{version}-{device}'
        )
        print(f'Making directory: {enunu_release_dir}')
        makedirs(enunu_release_dir)

        # utaupyとかを更新する
        python_dir = f'python-3.8.9-embed-amd64-{device}'
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
        shutil.copy2('enunu.py', join(enunu_release_dir, 'enunu.py'))
        shutil.copy2('hts2wav.py', join(enunu_release_dir, python_dir, 'hts2wav.py'))
        shutil.copy2('nnsvs_gen_override.py', join(
            enunu_release_dir, python_dir, 'nnsvs_gen_override.py'))

        # enunu.bat をリリースフォルダに作成
        print('Creating enunu.bat')
        create_enunu_bat(join(enunu_release_dir, 'enunu.bat'),  python_exe)

        # plugin.txt をリリースフォルダに作成
        print('Creating plugin.txt')
        create_plugin_txt(join(enunu_release_dir, 'plugin.txt'), version, device)

        # install.txt を作る
        path_install_txt = join(dirname(enunu_release_dir), 'install.txt')
        create_install_txt(path_install_txt, version, device)
    print('\n----------------------------------------------')


if __name__ == '__main__':
    main()
    input('Press Enter to exit.')
