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
full_score ラベルをもとに、NNSVSモデルを用いてtimelagを計算する。
timelag.labとして結果を出力する。
"""
import hydra
import joblib
import numpy as np
import torch
import utaupy
from hydra.utils import to_absolute_path
from nnmnkwii.io import hts
from nnsvs.gen import predict_timelag
from nnsvs.logger import getLogger
from omegaconf import DictConfig, OmegaConf

from enulib.common import (ndarray_as_labels, set_checkpoint,
                           set_normalization_stat)

logger = None


def score2timelag(config: DictConfig, score_path, timelag_path):
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
    labels = hts.load(score_path).round_()

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
        log_f0_conditioning,
        config.timelag.allowed_range,
        config.timelag.allowed_range_rest
    )
    # -----------------------------------------------------
    # ここまで nnsvs.bin.synthesis.synthesis() の内容 -----
    # -----------------------------------------------------

    # フルラベルとして出力する
    save_timelag_label_file(lag, score_path, timelag_path)


def save_timelag_label_file(array_2d: np.ndarray, path_full_score, path_full_timelag_out):
    """
    timelagの情報はノートごとなので、音素ごとに適切になるように出力する。
    """
    if array_2d.shape[1] != 1:
        raise ValueError(
            f'The shape of ndarray for timelag must be (any, 1), not {array_2d.shape}'
        )
    timelag_values = tuple(np.ravel(np.round(array_2d[:, 0]).astype(int)))
    song = utaupy.hts.load(path_full_score).song

    # timelagの値をフルラベルの時刻に入れる。
    for delta_t, note in zip(timelag_values, song.all_notes):
        for phoneme in note.phonemes:
            phoneme.start = delta_t
            phoneme.end = 0
    # フルラベルをモノラベルに変換する。
    song_as_mono_label = song.as_mono()
    # [#PREV] や [#NEXT] の値がフルラベルファイル入出力するときに
    # 各種値が自動再計算で消えるのを防ぐ目的で、
    # もとのfull_scoreのコンテキストをそのまま使用する。
    label_to_export_as_file = utaupy.label.load(path_full_score)
    label_to_export_as_file.start_times = song_as_mono_label.start_times
    label_to_export_as_file.end_times = song_as_mono_label.end_times
    # ファイル出力
    label_to_export_as_file.write(path_full_timelag_out)


def load_timelag_label_file(path_full_timelag) -> np.ndarray:
    """
    timelag情報を持ったフルラベルを読み取る。
    ノートごとの情報である前提なので、
    ノート内で複数の値を持っている場合は無効な値としてエラーにする。
    """
    # ラベルを読み取る
    song = utaupy.hts.load(path_full_timelag).song
    # timelag用のフルラベルファイルから、ノートごとのtimelag値を取得する。
    timelag_values = [[note.phonemes[0].start] for note in song.all_notes]
    # timelagを行列に変換する
    array_2d = np.array(timelag_values)
    return array_2d
