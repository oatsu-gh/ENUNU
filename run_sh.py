#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
"""
run.sh を python で置換する。
設計の綺麗さよりも完コピを優先する。
"""
import os
import shutil

import yaml
from nnsvs.bin import prepare_features
import preprocess_data


def main(config_path='config.yaml',
         start_stage: int = 0,
         stop_stage: int = 0):
    """
    実行するステージを判断して、
    configファイルを読み取って、
    全体の処理を実行する。
    """
    config = yaml.safe_load('config.yaml')

    spk = config['spk']
    tag = config['tag']
    out_dir = config['out_dir']

    train_set = 'train_no_dev'
    dev_set = 'dev'
    eval_set = 'eval'
    datasets = [train_set, dev_set]
    testsets = [dev_set, eval_set]

    dump_dir = 'dump'

    dump_org_dir = os.path.join(dump_dir, spk, 'org')
    dump_norm_dir = os.path.join(dump_dir, spk, 'norm')

    """
    もとの run.sh では
    . $NNSVS_ROOT/utils/parse_options.sh || exit 1;
    ってコマンドがこの位置にあったけど役割が分からない。
    """

    if (tag is None) or (tag == ''):
        exp_name = spk
    else:
        exp_name = f'{spk}_{tag}'
    exp_dir = os.path.join('exp', exp_name)

    # ---------------------------------------------
    # STAGE 0
    # ---------------------------------------------
    if start_stage <= 0 <= stop_stage:
        print('#########################################')
        print('#                                       #')
        print('#  stage 0: Data preparation            #')
        print('#                                       #')
        print('#########################################')
        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)
        if os.path.exists('preprocess.data.log'):
            os.remove('preprocess.data.log')
        preprocess_data(config_path)

    # ---------------------------------------------
    # STAGE 1
    # ---------------------------------------------
    if start_stage <= 1 <= stop_stage:
        print('#########################################')
        print('#                                       #')
        print('#  stage 1: Feature generation          #')
        print('#                                       #')
        print('#########################################')
        if os.path.exists(dump_dir):
            shutil.rmtree(dump_dir)
        feature_generation_sh(config)


def feature_generation_sh(config) -> None:
    """
    nnsvs/egs/_commmon/spsvs/feature_genaration.sh を置換する。
    """
    config_dir = os.path.join('conf', 'prepare_features')
    # FIXME: ここちゃんとconfigファイルのある場所を選択できるようにする。
    if os.path.exists(config_dir):
        prepare_features.entry()
    else:
        prepare_features.entry()
