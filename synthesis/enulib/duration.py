#!/usr/bin/env python3
# Copyright (c) 2022 oatsu
"""
full_score ラベルと timelag データをもとに、NNSVSモデルを用いてdurationを計算する。
"""
import hydra
import joblib
import numpy as np
import torch
from hydra.utils import to_absolute_path
from nnmnkwii.io import hts
from nnsvs.gen import predict_duration
from nnsvs.logger import getLogger
from omegaconf import DictConfig, OmegaConf

from enulib.common import set_checkpoint, set_normalization_stat

logger = None


def timelag2duration(config: DictConfig, label_path, timelag_path, duration_path):
    """
    full_score と timelag ラベルから durationラベルを生成する。
    """
    # -----------------------------------------------------
    # ここから nnsvs.bin.synthesis.my_app() の内容 --------
    # -----------------------------------------------------
    # loggerの設定
    global logger
    logger = getLogger(config.verbose)
    logger.info(OmegaConf.to_yaml(config))

    typ = 'duration'
    # CUDAが使えるかどうか
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # maybe_set_checkpoints_(config) のかわり
    set_checkpoint(config, typ)
    # maybe_set_normalization_stats_(config) のかわり
    set_normalization_stat(config, typ)

    # 各種設定を読み込む
    model_config = OmegaConf.load(to_absolute_path(config[typ].model_yaml))
    model = hydra.utils.instantiate(model_config.netG).to(device)
    checkpoint = torch.load(config.timelag.checkpoint,
                            map_location=lambda storage,
                            loc: storage)
    model.load_state_dict(checkpoint['state_dict'])
    in_scaler = joblib.load(config[typ].in_scaler_path)
    out_scaler = joblib.load(config[typ].out_scaler_path)
    model.eval()
    # -----------------------------------------------------
    # ここまで nnsvs.bin.synthesis.my_app() の内容 --------
    # -----------------------------------------------------

    # -----------------------------------------------------
    # ここから nnsvs.bin.synthesis.synthesis() の内容 -----
    # -----------------------------------------------------
    # full_score_lab を読み取る。
    labels = hts.load(label_path).round_()
    timelag = hts.load(timelag_path).round_()

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
    # pitch_idx = len(binary_dict) + 1
    pitch_indices = np.arange(len(binary_dict), len(binary_dict)+3)

    # f0の設定を読み取る。
    log_f0_conditioning = config.log_f0_conditioning

    # timelagモデルを適用
    # Time-lag
    duration = predict_duration(
        device,
        labels,
        model,
        model_config,
        in_scaler,
        out_scaler,
        timelag,
        binary_dict,
        continuous_dict,
        pitch_indices,
        log_f0_conditioning
    )

    # TODO: ここの出力形式をモノラベルかフルラベルにする。
    with open(duration_path, 'w', encoding='utf-8') as f:
        f.write(str(duration))
    # -----------------------------------------------------
    # ここまで nnsvs.bin.synthesis.synthesis() の内容 -----
    # -----------------------------------------------------
    print(type(duration))
    print(duration)
