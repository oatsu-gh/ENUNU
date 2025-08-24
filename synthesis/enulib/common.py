#!/usr/bin/env python3
# Copyright (c) 2022 oatsu
"""
ENUNUで合成するときに timelag/duration/acoustic共通で使う関数とか。
"""

from copy import copy
import os
from os.path import join

import numpy as np
import utaupy
from hydra.utils import to_absolute_path
from nnmnkwii.io import hts
from omegaconf import DictConfig, OmegaConf
from nnsvs import util

try:
    from parallel_wavegan.utils import load_model

    _pwg_available = True
except ImportError:
    _pwg_available = False


def full2mono(path_full, path_mono):
    """
    フルラベルをモノラベルに変換して保存する。
    """
    full_label = utaupy.hts.load(path_full)
    mono_label = full_label.as_mono()
    mono_label.write(path_mono)


def ndarray_as_labels(array_2d: np.ndarray, labels: hts.HTSLabelFile) -> hts.HTSLabelFile:
    """
    timelag, duration, timing などの ndarray を nnmnkwii.io.hts.HTSLabelFile に変換する。
    """
    if array_2d.ndim != 2:
        raise ValueError('input ndarray must be 2-dimentional array')
    new_labels = copy(labels)
    # 1列目を展開して発声開始時刻のところに入れる
    new_labels.start_times = np.ravel(np.round(array_2d[:, 0]).astype(int))
    # 発声終了時刻の列がない場合(timelag, duration)は0を代わりに入れる。
    if array_2d.shape[1] == 1:
        new_labels.end_times = [0] * len(array_2d)
    # 発声終了時刻の列がある場合(timing)はそれをコピーする。
    elif array_2d.shape[1] == 2:
        new_labels.end_times = np.ravel(np.round(array_2d[:, 1]).astype(int))
    else:
        raise ValueError(
            f'new_labels.shape should be (2, 1) or (2, 2). (new_labels.shape = {new_labels.shape})'
        )
    return new_labels


def set_checkpoint(config: DictConfig, typ: str):
    """
    使うモデルを指定する。
    """
    if config.model_dir is None:
        raise ValueError('"model_dir" config is required')
    model_dir = to_absolute_path(config.model_dir)
    # config.timelagに項目を追加
    config[typ].model_yaml = join(model_dir, typ, 'model.yaml')
    config[typ].checkpoint = join(model_dir, typ, config[typ].checkpoint)


def set_normalization_stat(config: DictConfig, typ: str):
    """
    何してるのかわからないけどconfigを上書きする。
    """
    if config.stats_dir is None:
        raise ValueError('"stats_dir" config is required')
    stats_dir = to_absolute_path(config.stats_dir)
    # config.timelagに項目を追加
    config[typ].in_scaler_path = join(stats_dir, f'in_{typ}_scaler.joblib')
    config[typ].out_scaler_path = join(stats_dir, f'out_{typ}_scaler.joblib')


def load_qustion(question_path, append_hat_for_LL=False) -> tuple:
    """
    question.hed ファイルを読み取って、
    binary_dict, continuous_dict, pitch_idx, pitch_indices を返す。
    """
    binary_dict, continuous_dict = hts.load_question_set(
        question_path, append_hat_for_LL=append_hat_for_LL
    )
    pitch_indices = np.arange(len(binary_dict), len(binary_dict) + 3)
    pitch_idx = len(binary_dict) + 1
    return (binary_dict, continuous_dict, pitch_indices, pitch_idx)


def get_vocoder_model(config: DictConfig, device: str):
    if not _pwg_available:
        raise ValueError('Unable to load "parallel_wavegan" library')

    typ = 'vocoder'

    # setup vocoder model path
    if config.model_dir is None:
        raise ValueError('"model_dir" config is required')

    model_dir = to_absolute_path(config.model_dir)
    config[typ].model_yaml = os.path.join(model_dir, typ, 'config.yml')
    config[typ].checkpoint = os.path.join(model_dir, typ, config[typ].checkpoint)

    # setup vocoder scaler path
    if config.stats_dir is None:
        raise ValueError('"stats_dir" config is required')

    stats_dir = to_absolute_path(config.stats_dir)
    in_vocoder_scaler_mean = os.path.join(stats_dir, f'in_vocoder_scaler_mean.npy')
    in_vocoder_scaler_var = os.path.join(stats_dir, f'in_vocoder_scaler_var.npy')
    in_vocoder_scaler_scale = os.path.join(stats_dir, f'in_vocoder_scaler_scale.npy')

    vocoder_config = OmegaConf.load(to_absolute_path(config[typ].model_yaml))
    vocoder = load_model(config[typ].checkpoint, config=vocoder_config).to(device)
    vocoder.eval()
    vocoder.remove_weight_norm()
    vocoder_in_scaler = util.StandardScaler(
        np.load(in_vocoder_scaler_mean),
        np.load(in_vocoder_scaler_var),
        np.load(in_vocoder_scaler_scale),
    )

    return vocoder_config, vocoder, vocoder_in_scaler
