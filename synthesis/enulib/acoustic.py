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
発声タイミングの情報を持ったフルラベルから、WORLD用の音響特長量を推定する。
"""
import hydra
import joblib
import numpy as np
import torch
from hydra.utils import to_absolute_path
from nnmnkwii.io import hts
from nnsvs.gen import predict_acoustic
from nnsvs.logger import getLogger
from omegaconf import DictConfig, OmegaConf

from enulib.common import set_checkpoint, set_normalization_stat

logger = None


def timing2acoustic(config: DictConfig, timing_path, acoustic_path):
    """
    フルラベルを読み取って、音響特長量のファイルを出力する。
    """
    # -----------------------------------------------------
    # ここから nnsvs.bin.synthesis.my_app() の内容 --------
    # -----------------------------------------------------
    # loggerの設定
    global logger  # pylint: disable=global-statement
    logger = getLogger(config.verbose)
    logger.info(OmegaConf.to_yaml(config))

    typ = 'acoustic'
    # CUDAが使えるかどうか
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # maybe_set_checkpoints_(config) のかわり
    set_checkpoint(config, typ)
    # maybe_set_normalization_stats_(config) のかわり
    set_normalization_stat(config, typ)

    # 各種設定を読み込む
    model_config = OmegaConf.load(to_absolute_path(config[typ].model_yaml))
    model = hydra.utils.instantiate(model_config.netG).to(device)
    checkpoint = torch.load(
        config[typ].checkpoint,
        map_location=lambda storage,
        loc: storage
    )

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
    duration_modified_labels = hts.load(timing_path).round_()

    # hedファイルを読み取る。
    question_path = to_absolute_path(config.question_path)
    # hts2wav.pyだとこう↓-----------------
    # これだと各モデルに別個のhedを適用できる。
    # if config[typ].question_path is None:
    #     config[typ].question_path = config.question_path
    # --------------------------------------
    # hedファイルを辞書として読み取る。
    binary_dict, continuous_dict = hts.load_question_set(
        question_path, append_hat_for_LL=False)
    # pitch indices in the input features
    # pitch_idx = len(binary_dict) + 1
    pitch_indices = np.arange(len(binary_dict), len(binary_dict)+3)

    # check force_clip_input_features (for backward compatibility)
    force_clip_input_features = True
    try:
        force_clip_input_features = config.acoustic.force_clip_input_features
    except:
        logger.info(f"force_clip_input_features of {typ} is not set so enabled as default")

    acoustic_features = predict_acoustic(
        device,
        duration_modified_labels,
        model,
        model_config,
        in_scaler,
        out_scaler,
        binary_dict,
        continuous_dict,
        config.acoustic.subphone_features,
        pitch_indices,
        config.log_f0_conditioning,
        force_clip_input_features
    )

    # csvファイルとしてAcousticの行列を出力
    np.savetxt(
        acoustic_path,
        acoustic_features,
        delimiter=','
    )
