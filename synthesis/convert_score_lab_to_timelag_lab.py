#!/usr/bin/env python3
# Copyright (c) 2022 oatsu
"""
full_score ラベルをもとに、NNSVSモデルを用いてtimelagを計算する。
timelag.labとして結果を出力する。
"""
from os.path import join

import hydra
import joblib
import numpy as np
import torch
from hydra.utils import to_absolute_path
from nnmnkwii.io import hts
from nnsvs.gen import predict_timelag
from nnsvs.logger import getLogger
from omegaconf import DictConfig, OmegaConf

logger = None


def set_checkpoint(config: DictConfig, typ: str):
    """
    使うモデルを指定する。
    """
    if config.model_dir is None:
        raise ValueError('"model_dir" config is required')
    typ = 'timelag'
    model_dir = to_absolute_path(config.model_dir)
    # config.timelagに項目を追加
    config[typ].model_yaml = \
        join(model_dir, typ, 'model.yaml')
    config[typ].checkpoint = \
        join(model_dir, typ, config.model_checkpoint)
    # hts2wav.pyだとこうしてた↓
    # config[typ].checkpoint = join(model_dir, typ, config[typ].checkpoint)


def set_normalization_stat(config: DictConfig, typ: str):
    """
    何してるのかわからないけどconfigを上書きする。
    """
    if config.stats_dir is None:
        raise ValueError('"stats_dir" config is required')
    stats_dir = to_absolute_path(config.stats_dir)
    # config.timelagに項目を追加
    config[typ].in_scaler_path = \
        join(stats_dir, f'in_{typ}_scaler.joblib')
    config[typ].out_scaler_path = \
        join(stats_dir, f'out_{typ}_scaler.joblib')


def load_qustion(question_path, append_hat_for_LL=False) -> tuple:
    """
    question.hed ファイルを読み取って、
    binary_dict, continuous_dict, pitch_idx, pitch_indices を返す。
    """
    binary_dict, continuous_dict = hts.load_question_set(
        question_path, append_hat_for_LL=append_hat_for_LL)
    pitch_indices = np.arange(len(binary_dict), len(binary_dict) + 3)
    pitch_idx = len(binary_dict) + 1
    return (binary_dict, continuous_dict, pitch_indices, pitch_idx)


def score2timelag(config: DictConfig, label_path) -> None:
    """
    全体の処理を実行する。
    """
    # -----------------------------------------------------
    # ここから nnsvs.bin.synthesis.my_app() の内容 --------
    # -----------------------------------------------------
    # loggerの設定
    global logger
    logger = getLogger(config.verbose)
    logger.info(OmegaConf.to_yaml(config))

    typ = 'timelag'
    # CUDAが使えるかどうか
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # maybe_set_checkpoints_(config) のかわり
    set_checkpoint(config, typ)
    # maybe_set_normalization_stats_(config) のかわり
    set_normalization_stat(config, typ)

    # 各種設定を読み込む
    timelag_config = \
        OmegaConf.load(to_absolute_path(config.timelag.model_yaml))
    timelag_model = \
        hydra.utils.instantiate(timelag_config.netG).to(device)
    checkpoint = \
        torch.load(config.timelag.checkpoint,
                   map_location=lambda storage,
                   loc: storage)
    timelag_model.load_state_dict(checkpoint['state_dict'])
    timelag_in_scaler = joblib.load(config[typ].in_scaler_path)
    timelag_out_scaler = joblib.load(config[typ].out_scaler_path)
    timelag_model.eval()
    # -----------------------------------------------------
    # ここまで nnsvs.bin.synthesis.my_app() の内容 --------
    # -----------------------------------------------------

    # -----------------------------------------------------
    # ここから nnsvs.bin.synthesis.synthesis() の内容 -----
    # -----------------------------------------------------
    # full_score_lab を読み取る。
    labels = hts.load(label_path).round_()

    # hedファイルを読み取る。
    question_path = to_absolute_path(config.question_path)
    # hts2wav.pyだとこう↓-----------------
    # これだと各モデルに別個のhedを適用できる。
    # if config[typ].question_path is None:
    #     config[typ].question_path = config.question_path
    # --------------------------------------
    # hedファイルを辞書として読み取る。
    binary_dict, continuous_dict = \
        hts.load_question_set(question_path, append_hat_for_LL=False)
    # pitch indices in the input features
    pitch_idx = len(binary_dict) + 1
    pitch_indices = np.arange(len(binary_dict), len(binary_dict)+3)

    # f0の設定を読み取る。
    log_f0_conditioning = config.log_f0_conditioning

    # timelagモデルを適用
    # Time-lag
    lag = predict_timelag(
        device,
        labels,
        timelag_model,
        timelag_config,
        timelag_in_scaler,
        timelag_out_scaler,
        binary_dict,
        continuous_dict,
        pitch_indices,
        log_f0_conditioning,
        config.timelag.allowed_range
    )
    # -----------------------------------------------------
    # ここまで nnsvs.bin.synthesis.synthesis() の内容 -----
    # -----------------------------------------------------
    print(type(lag))
    print(lag)
