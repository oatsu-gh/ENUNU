#!/usr/bin/env python3
# Copyright (c) 2022 oatsu
"""
timelagとdurationをまとめて実行する。

MDN系のdurationが確率分布を持って生成されるため、フルラベルにしづらい。
そのため、timelagとdurationをファイル出力せずにtimingまで一気にやる。
"""
import hydra
import joblib
import numpy as np
import torch
from hydra.utils import to_absolute_path
from nnmnkwii.io import hts
from nnsvs.gen import postprocess_duration, predict_duration, predict_timelag
from nnsvs.logger import getLogger
from omegaconf import DictConfig, OmegaConf

from enulib.common import set_checkpoint, set_normalization_stat

logger = None


def _score2timelag(config: DictConfig, labels):
    """
    全体の処理を実行する。
    """
    # -----------------------------------------------------
    # ここから nnsvs.bin.synthesis.my_app() の内容 --------
    # -----------------------------------------------------
    # loggerの設定
    global logger  # pylint: disable=global-statement
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
    model_config = OmegaConf.load(to_absolute_path(config[typ].model_yaml))
    model = hydra.utils.instantiate(model_config.netG).to(device)
    checkpoint = torch.load(config[typ].checkpoint,
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
    # labels = hts.load(score_path).round_()

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

    # check force_clip_input_features (for backward compatibility)
    force_clip_input_features = True
    try:
        force_clip_input_features = config.timelag.force_clip_input_features
    except:
        logger.info(f"force_clip_input_features of {typ} is not set so enabled as default")
        
    # timelagモデルを適用
    # Time-lag
    lag = predict_timelag(
        device,
        labels,
        model,
        model_config,
        in_scaler,
        out_scaler,
        binary_dict,
        continuous_dict,
        pitch_indices,
        config.log_f0_conditioning,
        config.timelag.allowed_range,
        config.timelag.allowed_range_rest,
        force_clip_input_features
    )
    # -----------------------------------------------------
    # ここまで nnsvs.bin.synthesis.synthesis() の内容 -----
    # -----------------------------------------------------

    # フルラベルとして出力する
    # save_timelag_label_file(lag, score_path, timelag_path)
    return lag


def _score2duration(config: DictConfig, labels):
    """
    full_score と timelag ラベルから durationラベルを生成する。
    """
    # -----------------------------------------------------
    # ここから nnsvs.bin.synthesis.my_app() の内容 --------
    # -----------------------------------------------------
    # loggerの設定
    global logger  # pylint: disable=global-statement
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
    checkpoint = torch.load(config[typ].checkpoint,
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
    # labels = hts.load(score_path).round_()
    # いまのduraitonモデルだと使わない
    # timelag = hts.load(timelag_path).round_()

    # hedファイルを読み取る。
    question_path = to_absolute_path(config.question_path)
    # hts2wav.pyだとこう↓-----------------
    # これだと各モデルに別個のhedを適用できる。
    # if config[typ].question_path is None:
    #     config[typ].question_path = config.question_path
    # --------------------------------------
    # hedファイルを辞書として読み取る。
    binary_dict, numeric_dict = \
        hts.load_question_set(question_path, append_hat_for_LL=False)
    # pitch indices in the input features
    # pitch_idx = len(binary_dict) + 1
    pitch_indices = np.arange(len(binary_dict), len(binary_dict)+3)

    # check force_clip_input_features (for backward compatibility)
    force_clip_input_features = True
    try:
        force_clip_input_features = config.duration.force_clip_input_features
    except:
        logger.info(f"force_clip_input_features of {typ} is not set so enabled as default")

    # durationモデルを適用
    duration = predict_duration(
        device,
        labels,
        model,
        model_config,
        in_scaler,
        out_scaler,
        binary_dict,
        numeric_dict,
        pitch_indices,
        config.log_f0_conditioning,
        force_clip_input_features
    )
    # durationのタプルまたはndarrayを返す
    return duration


def score2timing(config: DictConfig, path_score, path_timing):
    """
    full_score から full_timing ラベルを生成する。
    """
    # full_score を読む
    score = hts.load(path_score).round_()
    # timelag
    timelag = _score2timelag(config, score)
    # duration
    duration = _score2duration(config, score)
    # timing
    timing = postprocess_duration(score, duration, timelag)

    # timingファイルを出力する
    with open(path_timing, 'w', encoding='utf-8') as f:
        f.write(str(timing))
