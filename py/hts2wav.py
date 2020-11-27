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

from os.path import basename, dirname, join, splitext
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
from omegaconf import DictConfig
from scipy.io import wavfile


def maybe_set_checkpoints_(config):
    """
    configファイルを参考に、使用するチェックポイントを設定する。
    """
    model_dir = to_absolute_path(config.model_dir)

    for typ in ("timelag", "duration", "acoustic"):
        # config of each model
        config[typ].model_yaml = join(model_dir, typ, "model.yaml")
        # checkpoint of each model
        config[typ].checkpoint = join(model_dir, typ, config[typ].checkpoint)


def maybe_set_normalization_stats_(config):
    """
    configファイルを参考に、使用する *_scaler.joblib ファイルを設定する。
    """
    stats_dir = to_absolute_path(config.stats_dir)

    for typ in ("timelag", "duration", "acoustic"):
        # I/O path of scalar file for each model
        config[typ].in_scaler_path = join(stats_dir, f"in_{typ}_scaler.joblib")
        config[typ].out_scaler_path = join(stats_dir, f"out_{typ}_scaler.joblib")


def probably_load_models_(config, device):
    """
    my_app 内にあった load() を繰り返す部分を関数として取り出した。
    """
    for typ in ("timelag", "duration", "acoustic"):
        model = hydra.utils.instantiate(config[typ].netG).to(device)
        checkpoint = torch.load(
            to_absolute_path(config[typ].checkpoint),
            map_location=lambda storage, loc: storage)
        model.load_state_dict(checkpoint["state_dict"])
        config[typ].in_scaler = joblib.load(to_absolute_path(config[typ].in_scaler_path))
        config[typ].out_scaler = joblib.load(to_absolute_path(config[typ].out_scaler_path))
        model.eval()


def probably_set_wav_data_(config, wav, logger):
    """
    ビット深度を指定
    """
    if str(config.bit_depth) in ('16', '16i', 'int16'):
        wav_data = wav.astype(np.int16)
    elif str(config.bit_depth) in ('24', '24i', 'int24'):
        wav_data = wav.astype(np.int24)
    elif str(config.bit_depth) in ('32f', 'float32'):
        wav_data = wav.astype(np.float32)
    else:
        logger.warn(
            'sample_rate can take "16", "14" or "32f".'
            ' This time render in 32bit float depth.')
        wav_data = wav.astype(np.float32)
    return wav_data


def synthesis(config, device, label_path, question_path):
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
            device, labels,
            config.timelag.model,
            config.timelag,
            config.timelag.in_scaler,
            config.timelag.out_scaler,
            binary_dict, continuous_dict, pitch_indices,
            log_f0_conditioning,
            config.timelag.allowed_range)

        # Timelag predictions
        durations = predict_duration(
            device, labels,
            config.duration.model,
            config.duration,
            config.duration.in_scaler,
            config.duration.out_scaler,
            lag, binary_dict, continuous_dict,
            pitch_indices, log_f0_conditioning)

        # Normalize phoneme durations
        duration_modified_labels = postprocess_duration(labels, durations, lag)

    # Predict acoustic features
    acoustic_features = predict_acoustic(
        device, duration_modified_labels,
        config.acoustic.model,
        config.acoustic,
        config.acoustic.in_scaler,
        config.acoustic.out_scaler,
        binary_dict, continuous_dict,
        config.acoustic.subphone_features,
        pitch_indices, log_f0_conditioning)

    # Waveform generation
    generated_waveform = gen_waveform(
        duration_modified_labels,
        acoustic_features,
        binary_dict, continuous_dict,
        config.acoustic.stream_sizes,
        config.acoustic.has_dynamic_features,
        config.acoustic.subphone_features,
        log_f0_conditioning,
        pitch_idx,
        config.acoustic.num_windows,
        config.acoustic.post_filter,
        config.sample_rate,
        config.frame_period,
        config.acoustic.relative_f0)

    return generated_waveform


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

    # hedファイルを全体で指定しているか、各モデルで設定しているかを判定する？
    if config.question_path is not None:
        config.timelag.question_path = config.question_path
        config.duration.question_path = config.question_path
        config.acoustic.question_path = config.question_path

    # GPUのCUDAが使えるかどうかを判定
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # 使用モデルの学習済みファイルのパスを設定する。
    maybe_set_checkpoints_(config)
    maybe_set_normalization_stats_(config)

    # モデルに関するファイルを読み取る。
    probably_load_models_(config, device)

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

    wav = synthesis(config, device, label_path, question_path)

    # 音量ノーマライズ
    if config.gain_normalize:
        wav = wav / np.max(np.abs(wav)) * (2**15 - 1)

    # サンプルレートとビット深度を指定してファイル出力
    wav_data = probably_set_wav_data_(config, wav, logger)
    wavfile.write(out_wav_path, rate=config.sample_rate, data=wav_data)


def hts2wav(config: DictConfig, label_path: str, out_wav_path: str):
    """
    パスを指定して音声合成を実施する。
    ENUNU用にパスを指定しやすいようにwrapした。
    """
    my_app(config, label_path=label_path, out_wav_path=out_wav_path)


def main():
    """
    手動起動したとき
    """
    # コマンドライン引数に必要な情報があるかチェック
    try:
        voicebank_config_path = argv[1].strip('"')
        label_path = argv[2].strip('"')
        out_wav_path = argv[3].strip('"')
    # コマンドライン引数が不足していれば標準入力で受ける
    except IndexError:
        print('Please input voicebank\'s config file path\n>>> ')
        voicebank_config_path = input().strip('"')
        print('Please input label file path\n>>> ')
        label_path = input().strip('"')
        out_wav_path = label_path.replace('.lab', '.wav')

    # configファイルのパスを分割する
    vb_config_dir = dirname(voicebank_config_path)
    vb_config_name, config_ext = splitext(basename(voicebank_config_path))
    if not config_ext in ('yml', 'yaml', 'YAML', 'YML'):
        raise ValueError('Selected config file is not YAML file.')
    # configファイルを読み取る
    config = hydra.main(config_path=vb_config_dir, config_name=vb_config_name)
    hts2wav(config, label_path, out_wav_path)


if __name__ == '__main__':
    main()  # pylint: disable=E1120
