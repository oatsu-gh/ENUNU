#! /usr/bin/env python3
# coding: utf-8
# Copyright (c) 2020 oatsu
# Copyright (c) 2020 Ryuichi Yamamoto

# ---------------------------------------------------------------------------------
#
# This 'hts2wav.py' file is reedit of 'synthesis.py' from
# nnsvs/nnsvs/bin/synthesis.py, in NNSVS(https://github.com/r9y9/nnsvs).
#
# NNSVS is distributed under MIT License below.
#
# ---------------------------------------------------------------------------------
#
# MIT License
#
# Copyright (c) 2020 Ryuichi Yamamoto
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# ---------------------------------------------------------------------------------

"""
NNSVSを利用して、ラベルから音声ファイルを生成する。

nnsvs-synthesis コマンドの源である nnsvs.bin.synthesis.py をENUNU用に改変した。
"""

from os.path import join
from sys import argv

import hydra
import joblib
import numpy as np
import torch
from hydra.utils import to_absolute_path
from nnmnkwii.io import hts
from nnsvs.gen import (gen_waveform, postprocess_duration, predict_acoustic,
                       predict_duration, predict_timelag)
from nnsvs.logger import getLogger
from omegaconf import DictConfig, OmegaConf
from scipy.io import wavfile


def maybe_set_checkpoints_(config):
    """
    configファイルを参考に、使用するチェックポイントを設定する。
    """
    if config.model_dir is None:
        return
    model_dir = to_absolute_path(config.model_dir)

    for typ in ["timelag", "duration", "acoustic"]:
        model_config = join(model_dir, typ, "model.yaml")
        model_checkpoint = join(model_dir, typ, config.model_checkpoint)

        config[typ].model_yaml = model_config
        config[typ].checkpoint = model_checkpoint


def maybe_set_normalization_stats_(config):
    """
    configファイルを参考に、使用するチェックポイントを設定する。
    """
    if config.stats_dir is None:
        return
    stats_dir = to_absolute_path(config.stats_dir)

    for typ in ["timelag", "duration", "acoustic"]:
        in_scaler_path = join(stats_dir, f"in_{typ}_scaler.joblib")
        out_scaler_path = join(stats_dir, f"out_{typ}_scaler.joblib")

        config[typ].in_scaler_path = in_scaler_path
        config[typ].out_scaler_path = out_scaler_path


def synthesis(
        config, device, label_path, question_path,
        timelag_model, timelag_config, timelag_in_scaler, timelag_out_scaler,
        duration_model, duration_config, duration_in_scaler, duration_out_scaler,
        acoustic_model, acoustic_config, acoustic_in_scaler, acoustic_out_scaler):
    """
    音声ファイルを合成する。
    """
    # load labels and question
    labels = hts.load(label_path).round_()
    binary_dict, continuous_dict = hts.load_question_set(
        question_path, append_hat_for_LL=False)

    # pitch indices in the input features
    # TODO: configuarable
    pitch_idx = len(binary_dict) + 1
    pitch_indices = np.arange(len(binary_dict), len(binary_dict) + 3)

    log_f0_conditioning = config.log_f0_conditioning

    if config.ground_truth_duration:
        # Use provided alignment
        duration_modified_labels = labels
    else:
        # Time-lag
        lag = predict_timelag(
            device, labels, timelag_model, timelag_config, timelag_in_scaler,
            timelag_out_scaler, binary_dict, continuous_dict, pitch_indices,
            log_f0_conditioning, config.timelag.allowed_range)

        # Timelag predictions
        durations = predict_duration(
            device, labels, duration_model, duration_config,
            duration_in_scaler, duration_out_scaler, lag, binary_dict, continuous_dict,
            pitch_indices, log_f0_conditioning)

        # Normalize phoneme durations
        duration_modified_labels = postprocess_duration(labels, durations, lag)

    # Predict acoustic features
    acoustic_features = predict_acoustic(
        device, duration_modified_labels, acoustic_model, acoustic_config,
        acoustic_in_scaler, acoustic_out_scaler, binary_dict, continuous_dict,
        config.acoustic.subphone_features, pitch_indices, log_f0_conditioning)

    # Waveform generation
    generated_waveform = gen_waveform(
        duration_modified_labels, acoustic_features,
        binary_dict, continuous_dict, acoustic_config.stream_sizes,
        acoustic_config.has_dynamic_features,
        config.acoustic.subphone_features, log_f0_conditioning,
        pitch_idx, acoustic_config.num_windows,
        config.acoustic.post_filter, config.sample_rate, config.frame_period,
        config.acoustic.relative_f0)

    return generated_waveform


@hydra.main(config_path="conf/synthesis/config.yaml")
def my_app(config: DictConfig, label_path: str = None, out_wav_path: str = None) -> None:
    """
    configファイルから各種設定を取得し、labファイルをもとにWAVファイルを生成する。

    もとの my_app との相違点:
        - ビット深度指定をできるようにした。
        - utt_list を使わず単一ファイルのみにした。
        - 単一ファイルのときの音量ノーマライズを無効にした。
    """
    logger = getLogger(config.verbose)
    logger.info(config.pretty())

    # GPUのCUDAが使えるかどうかを判定
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    maybe_set_checkpoints_(config)
    maybe_set_normalization_stats_(config)

    # timelagモデルに関するファイルを読み取る。
    timelag_config = OmegaConf.load(
        to_absolute_path(config.timelag.model_yaml))
    timelag_model = hydra.utils.instantiate(timelag_config.netG).to(device)
    checkpoint = torch.load(
        to_absolute_path(config.timelag.checkpoint),
        map_location=lambda storage, loc: storage)
    timelag_model.load_state_dict(checkpoint["state_dict"])
    timelag_in_scaler = joblib.load(
        to_absolute_path(config.timelag.in_scaler_path))
    timelag_out_scaler = joblib.load(
        to_absolute_path(config.timelag.out_scaler_path))
    timelag_model.eval()

    # durationモデルに関するファイルを読み取る。
    duration_config = OmegaConf.load(to_absolute_path(config.duration.model_yaml))
    duration_model = hydra.utils.instantiate(duration_config.netG).to(device)
    checkpoint = torch.load(
        to_absolute_path(config.duration.checkpoint),
        map_location=lambda storage, loc: storage)
    duration_model.load_state_dict(checkpoint["state_dict"])
    duration_in_scaler = joblib.load(to_absolute_path(config.duration.in_scaler_path))
    duration_out_scaler = joblib.load(to_absolute_path(config.duration.out_scaler_path))
    duration_model.eval()

    # acousticモデルに関するファイルを読み取る。
    acoustic_config = OmegaConf.load(
        to_absolute_path(config.acoustic.model_yaml))
    acoustic_model = hydra.utils.instantiate(acoustic_config.netG).to(device)
    checkpoint = torch.load(
        to_absolute_path(config.acoustic.checkpoint),
        map_location=lambda storage, loc: storage)
    acoustic_model.load_state_dict(checkpoint["state_dict"])
    acoustic_in_scaler = joblib.load(to_absolute_path(config.acoustic.in_scaler_path))
    acoustic_out_scaler = joblib.load(to_absolute_path(config.acoustic.out_scaler_path))
    acoustic_model.eval()

    # Run synthesis for each utt.
    question_path = to_absolute_path(config.question_path)

    # synthesize wav file from lab file.
    # 入力するラベルファイルを指定。
    if label_path is None:
        assert config.label_path is not None
        label_path = to_absolute_path(config.label_path)
    else:
        label_path = to_absolute_path(label_path)
    logger.info("Process the label file: %s", label_path)

    # 出力するwavファイルの設定。
    if out_wav_path is None:
        out_wav_path = to_absolute_path(config.out_wav_path)
    else:
        out_wav_path = to_absolute_path(out_wav_path)
    logger.info("Synthesize the wav file: %s", out_wav_path)

    wav = synthesis(
        config, device, label_path, question_path,
        timelag_model, timelag_config, timelag_in_scaler, timelag_out_scaler,
        duration_model, duration_config, duration_in_scaler, duration_out_scaler,
        acoustic_model, acoustic_config, acoustic_in_scaler, acoustic_out_scaler)

    # 音量ノーマライズ
    if config.gain_normalize:
        wav = wav / np.max(np.abs(wav)) * (2**15 - 1)

    # サンプルレートとビット深度を指定してファイル出力
    if str(config.bit_depth) in ('16', '16i', 'int16'):
        wavfile.write(out_wav_path, rate=config.sample_rate, data=wav.astype(np.int16))
    if str(config.bit_depth) in ('24', '24i', 'int24'):
        wavfile.write(out_wav_path, rate=config.sample_rate, data=wav.astype(np.int16))
    elif str(config.bit_depth) in ('32f', 'float32'):
        wavfile.write(out_wav_path, rate=config.sample_rate, data=wav.astype(np.float32))
    else:
        logger.info('Sample_rate can take "16", "14" or "32f". This time render in 32f bit depth.')
        wavfile.write(out_wav_path, rate=config.sample_rate, data=wav.astype(np.float32))


def hts2wav(label_path: str, out_wav_path: str):
    """
    パスを指定して音声合成を実施する。
    ENUNU用にパスを指定しやすいようにwrapした。
    """
    my_app(label_path=label_path, out_wav_path=out_wav_path)  # pylint: disable=E1120


def main():
    """
    手動起動したとき
    """
    try:
        label_path = argv[1].strip('"')
        out_wav_path = argv[2].strip('"')
    except IndexError:
        print('Please input the file path')
        label_path = input('label_path  : ')
        out_wav_path = label_path.replace('.lab', '.wav')
    hts2wav(label_path, out_wav_path)


if __name__ == '__main__':
    main()
