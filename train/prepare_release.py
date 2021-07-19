#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
"""
配布用フォルダを準備する
"""

from glob import glob
from os import makedirs
from os.path import exists
from shutil import copy2, copytree

import yaml
from send2trash import send2trash
from tqdm import tqdm


def copy_train_config(config_dir, release_dir):
    """
    acoustic_*.yaml, duration_*.yaml, timelag_*.yaml をコピー
    """
    print('copying config')
    copytree(config_dir, f'{release_dir}/{config_dir}')


def copy_dictionary(path_table, release_dir):
    """
    *.table, *.conf をコピー
    """
    print('copying dictionary')
    makedirs(f'{release_dir}/dic', exist_ok=True)
    copy2(path_table, f'{release_dir}/{path_table}')


def copy_question(path_question, release_dir):
    """
    hedファイル(question)をコピー
    """
    print('copying question')
    makedirs(f'{release_dir}/hed', exist_ok=True)
    copy2(path_question, f'{release_dir}/{path_question}')


def copy_scaler(singer, release_dir):
    """
    dumpフォルダにあるファイルをコピー
    """
    makedirs(f'{release_dir}/dump/{singer}/norm', exist_ok=True)
    list_path_scaler = glob(f'dump/{singer}/norm/*_scaler.joblib')

    print('copying scaler')
    for path_scaler in tqdm(list_path_scaler):
        copy2(path_scaler, f'{release_dir}/{path_scaler}')


def copy_model(singer, name_exp, release_dir):
    """
    name_exp: 試験のID
    """
    name_exp = singer + '_' + name_exp
    makedirs(f'{release_dir}/exp/{name_exp}/acoustic', exist_ok=True)
    makedirs(f'{release_dir}/exp/{name_exp}/duration', exist_ok=True)
    makedirs(f'{release_dir}/exp/{name_exp}/timelag', exist_ok=True)
    list_path_model = glob(f'exp/{name_exp}/*/*.pth')
    list_path_model += glob(f'exp/{name_exp}/*/model.yaml')

    print('copying model')
    for path_model in tqdm(list_path_model):
        copy2(path_model, f'{release_dir}/{path_model}')


def copy_general_config(release_dir):
    """
    singer: 歌唱者名
    """
    print('copying config.yaml')
    copy2('config.yaml', f'{release_dir}/config.yaml')


def copy_enuconfig(release_dir):
    """
    singer: 歌唱者名
    """
    print('copying enuconfig.yaml')
    copy2('enuconfig.yaml', f'{release_dir}/enuconfig.yaml')


def main():
    """
    各種ファイルをコピーする
    """
    # load settings
    with open('config.yaml', 'r') as f_yaml:
        config = yaml.load(f_yaml, Loader=yaml.FullLoader)
    singer = config['spk'].strip('"\'')
    config_dir = 'conf'
    release_dir = f'release/{singer}_---'
    path_table = config['table_path'].strip('"\'')
    path_question = config['question_path'].strip('"\'')
    experiment_name = config['tag'].strip('"\'')

    # copy models to the release directory
    if exists(release_dir):
        print('Sending existing directory to recycle bin')
        send2trash(release_dir)
    makedirs(release_dir, exist_ok=True)
    copy_general_config(release_dir)
    copy_enuconfig(release_dir)
    copy_train_config(config_dir, release_dir)
    copy_dictionary(path_table, release_dir)
    copy_question(path_question, release_dir)
    copy_scaler(singer, release_dir)
    copy_model(singer, experiment_name, release_dir)


if __name__ == '__main__':
    main()
