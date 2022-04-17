#!/usr/bin/env python3
# Copyright (c) 2022 oatsu
# ---------------------------------------------------------------------------------
#
# MIT License
#
# Copyright (c) 2020 Ryuichi Yamamoto
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the 'Software'), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# ---------------------------------------------------------------------------------

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

from enulib.common import (ndarray_as_labels, set_checkpoint,
                           set_normalization_stat)

logger = None


def score2duration(config: DictConfig, score_path, duration_path):
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
    labels = hts.load(score_path).round_()
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
    binary_dict, continuous_dict = \
        hts.load_question_set(question_path, append_hat_for_LL=False)
    # pitch indices in the input features
    # pitch_idx = len(binary_dict) + 1
    pitch_indices = np.arange(len(binary_dict), len(binary_dict)+3)

    # f0の設定を読み取る。
    log_f0_conditioning = config.log_f0_conditioning

    # durationモデルを適用
    duration = predict_duration(
        device,
        labels,
        model,
        model_config,
        in_scaler,
        out_scaler,
        binary_dict,
        continuous_dict,
        pitch_indices,
        log_f0_conditioning,
        force_clip_input_features=False
    )
    # -----------------------------------------------------
    # ここまで nnsvs.bin.synthesis.synthesis() の内容 -----
    # -----------------------------------------------------

    # durationはtimelagと違って、
    # 100nsではなくサンプル数(5msごとに1サンプル)なので、
    # フォーマットを統一するために100ns表記に変換する。
    # NOTE: 5msじゃない学習をするようになったら直さないといけない。
    duration_100ns = duration[0] * 50000
    # フルラベルとして出力する
    duration_labels = ndarray_as_labels(duration_100ns, labels)
    with open(duration_path, 'w', encoding='utf-8') as f:
        f.write(str(duration_labels))
