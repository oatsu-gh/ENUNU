#!/usr/bin/env python
# Copyright (c) 2021 oatsu
"""
配布用フォルダを準備する
"""

from glob import glob
from os import makedirs
from os.path import basename, exists
from shutil import copy2, copytree
from sys import argv

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


def copy_model(singer, exp_name, release_dir):
    """
    exp_name: 試験のID
    """
    exp_name = singer + '_' + exp_name
    makedirs(f'{release_dir}/exp/{exp_name}/acoustic', exist_ok=True)
    makedirs(f'{release_dir}/exp/{exp_name}/duration', exist_ok=True)
    makedirs(f'{release_dir}/exp/{exp_name}/timelag', exist_ok=True)
    list_path_model = glob(f'exp/{exp_name}/*/*.pth')
    list_path_model += glob(f'exp/{exp_name}/*/model.yaml')

    print('copying model')
    for path_model in tqdm(list_path_model):
        copy2(path_model, f'{release_dir}/{path_model}')


def copy_general_config(path_config_yaml, release_dir):
    """
    singer: 歌唱者名
    """
    print(f'copying {basename(path_config_yaml)}')
    copy2(path_config_yaml, f'{release_dir}/{basename(path_config_yaml)}')


def copy_enuconfig(path_config_yaml, path_enuconfig_yaml, release_dir):
    """
    enuconfig の hed ファイル名を、学習に使ったものに合わせる。
    """
    # 学習フォルダにあるconfigとenuconfigを読み取る
    with open(path_enuconfig_yaml, 'r', encoding='utf-8') as f:
        enuconfig = yaml.safe_load(f)
    with open(path_config_yaml, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    with open(path_enuconfig_yaml, 'r', encoding='utf-8') as f:
        s = f.read()

    # hedファイルを指定する項目を上書きする
    old_qst_path = enuconfig['question_path'].strip('"\'')
    new_qst_path = config['question_path'].strip('"\'')
    print(old_qst_path, new_qst_path)
    s = s.replace(old_qst_path, new_qst_path)

    # 置換済みの文字列で書き換えたenuconfigをreleaseフォルダに保存
    print('copying enuconfig.yaml')
    with open(f'{release_dir}/enuconfig.yaml', 'w', encoding='utf-8') as f:
        s = f.write(s)


def main(path_config_yaml):
    """
    各種ファイルをコピーする
    """
    # load settings
    with open(path_config_yaml, 'r') as f_yaml:
        config = yaml.safe_load(f_yaml)
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
    copy_general_config(path_config_yaml, release_dir)
    copy_enuconfig(path_config_yaml, 'enuconfig.yaml', release_dir)
    copy_train_config(config_dir, release_dir)
    copy_dictionary(path_table, release_dir)
    copy_question(path_question, release_dir)
    copy_scaler(singer, release_dir)
    copy_model(singer, experiment_name, release_dir)


if __name__ == '__main__':
    if len(argv) == 1:
        main('config.yaml')
    else:
        main(argv[1].strip('"'))
