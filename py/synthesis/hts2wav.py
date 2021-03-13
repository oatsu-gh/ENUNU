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
NNSVSを利用して、ラベルから音声ファイルを生成する。
nnsvs-synthesis コマンドの源である nnsvs.bin.synthesis.py をENUNU用に改変した。
"""

from datetime import datetime
from os.path import join, relpath, split, splitext
from sys import argv

import hydra
import joblib
import numpy as np
import torch
from hydra.experimental import compose, initialize
from nnmnkwii.io import hts
from nnsvs.gen import (gen_waveform, postprocess_duration, predict_acoustic,
                       predict_duration, predict_timelag)
from nnsvs.logger import getLogger
from omegaconf import DictConfig, OmegaConf
from scipy.io import wavfile


def maybe_set_checkpoints_(config: DictConfig):
    """
    configファイルを参考に、使用するチェックポイントを設定する。
    """
    model_dir = config.model_dir
    for typ in ('timelag', 'duration', 'acoustic'):
        # checkpoint of each model
        if config[typ].checkpoint is None:
            config[typ].checkpoint = join(model_dir, typ, 'best_loss.pth')
        else:
            config[typ].checkpoint = join(model_dir, typ, config[typ].checkpoint)


def maybe_set_normalization_stats_(config: DictConfig):
    """
    configファイルを参考に、使用する *_scaler.joblib ファイルを設定する。
    """
    stats_dir = config.stats_dir
    for typ in ('timelag', 'duration', 'acoustic'):
        # I/O path of scalar file for each model
        config[typ].in_scaler_path = join(stats_dir, f'in_{typ}_scaler.joblib')
        config[typ].out_scaler_path = join(stats_dir, f'out_{typ}_scaler.joblib')


def generate_wav_file(config: DictConfig, wav, out_wav_path, logger):
    """
    ビット深度を指定してファイル出力
    """
    max_gain = np.max(np.abs(wav))

    # 学習データのビット震度を推定(8388608=2^24)
    if max_gain > 8388608:
        training_data_bit_depth = 32
    else:
        training_data_bit_depth = 16

    # 出力ファイルのビット震度を指定
    bit_depth = int(config.bit_depth)
    if bit_depth not in (16, 32):
        logger.warn("bit_depth can take '16' or '32'. This time render in 32bit int depth.")

    # 16bit出力のとき
    if bit_depth == 16:
        limit_gain = 32767
        # 16bitの音声を学習したと思われるときはそのまま出力
        # 32bitで学習して16bit出力しようとしている場合は16bit小さくする。
        if training_data_bit_depth == 32:
            wav = wav / 65536
        wav = wav.astype(np.int16)
    # 32bit出力のとき
    elif bit_depth == 32:
        limit_gain = 2147483647
        # 32bitの音声を学習したと思われるときはそのまま出力
        # 16bitで学習して32bit出力しようとしている場合は16bit大きくする。
        if training_data_bit_depth == 16:
            wav = wav * 65536
        wav = wav.astype(np.int32)
    # なぜか16bitでも32bitでもないとき
    else:
        raise ValueError('Unexpected Error')

    # 音量ノーマライズする場合
    if config.gain_normalize:
        wav = wav * limit_gain / max_gain
    # 音量ノーマライズしない場合、クリッピングしてたら警告
    else:
        if max_gain > limit_gain:
            logger.warn("Output WAV file seems clipped")

    # ファイル出力
    wavfile.write(out_wav_path, rate=config.sample_rate, data=wav)


def set_each_question_path(config: DictConfig):
    """
    qstを読み取るのめんどくさい
    """
    # hedファイルを全体で指定しているか、各モデルで設定しているかを判定する
    for typ in ('timelag', 'duration', 'acoustic'):
        if config[typ].question_path is None:
            config[typ].question_path = config.question_path
        else:
            config[typ].question_path = config[typ].question_path


def load_qst(question_path, append_hat_for_LL=False) -> tuple:
    """
    question.hed ファイルを読み取って、
    binary_dict, continuous_dict, pitch_idx, pitch_indices を返す。
    """
    binary_dict, continuous_dict = hts.load_question_set(
        question_path, append_hat_for_LL=append_hat_for_LL)
    pitch_indices = np.arange(len(binary_dict), len(binary_dict) + 3)
    pitch_idx = len(binary_dict) + 1
    return (binary_dict, continuous_dict, pitch_indices, pitch_idx)


def synthesis(config, device, label_path,
              timelag_model, timelag_config, timelag_in_scaler, timelag_out_scaler,
              duration_model, duration_config, duration_in_scaler, duration_out_scaler,
              acoustic_model, acoustic_config, acoustic_in_scaler, acoustic_out_scaler):
    """
    音声ファイルを合成する。
    """
    # load labels and question
    labels = hts.load(label_path).round_()
    # load questions
    set_each_question_path(config)
    log_f0_conditioning = config.log_f0_conditioning

    if config.ground_truth_duration:
        # Use provided alignment
        duration_modified_labels = labels
    else:
        # Time-lag predictions
        timelag_binary_dict, timelag_continuous_dict, timelag_pitch_indices, _ \
            = load_qst(config.timelag.question_path)
        lag = predict_timelag(
            device, labels,
            timelag_model,
            timelag_config,
            timelag_in_scaler,
            timelag_out_scaler,
            timelag_binary_dict,
            timelag_continuous_dict,
            timelag_pitch_indices,
            log_f0_conditioning,
            config.timelag.allowed_range)

        # Duration predictions
        duration_binary_dict, duration_continuous_dict, duration_pitch_indices, _ \
            = load_qst(config.timelag.question_path)
        durations = predict_duration(
            device, labels,
            duration_model,
            duration_config,
            duration_in_scaler,
            duration_out_scaler,
            lag,
            duration_binary_dict,
            duration_continuous_dict,
            duration_pitch_indices,
            log_f0_conditioning)
        # Normalize phoneme durations
        duration_modified_labels = postprocess_duration(labels, durations, lag)

    acoustic_binary_dict, acoustic_continuous_dict, acoustic_pitch_indices, acoustic_pitch_idx \
        = load_qst(config.timelag.question_path)
    # Predict acoustic features
    acoustic_features = predict_acoustic(
        device, duration_modified_labels,
        acoustic_model,
        acoustic_config,
        acoustic_in_scaler,
        acoustic_out_scaler,
        acoustic_binary_dict,
        acoustic_continuous_dict,
        config.acoustic.subphone_features,
        acoustic_pitch_indices,
        log_f0_conditioning)

    # Waveform generation
    generated_waveform = gen_waveform(
        duration_modified_labels,
        acoustic_features,
        acoustic_binary_dict,
        acoustic_continuous_dict,
        acoustic_config.stream_sizes,
        acoustic_config.has_dynamic_features,
        config.acoustic.subphone_features,
        log_f0_conditioning,
        acoustic_pitch_idx,
        acoustic_config.num_windows,
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
    logger.info(OmegaConf.to_yaml(config))

    # GPUのCUDAが使えるかどうかを判定
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # 使用モデルの学習済みファイルのパスを設定する。
    maybe_set_checkpoints_(config)
    maybe_set_normalization_stats_(config)

    # モデルに関するファイルを読み取る。
    model_root = config.model_dir
    # timelag
    timelag_config = OmegaConf.load(join(model_root, "timelag", "model.yaml"))
    timelag_model = hydra.utils.instantiate(timelag_config.netG).to(device)
    checkpoint = torch.load(config.timelag.checkpoint,
                            map_location=lambda storage,
                            loc: storage)
    timelag_model.load_state_dict(checkpoint['state_dict'])
    timelag_in_scaler = joblib.load(config.timelag.in_scaler_path)
    timelag_out_scaler = joblib.load(config.timelag.out_scaler_path)
    timelag_model.eval()

    # duration
    duration_config = OmegaConf.load(join(model_root, "duration", "model.yaml"))
    duration_model = hydra.utils.instantiate(duration_config.netG).to(device)
    checkpoint = torch.load(config.duration.checkpoint,
                            map_location=lambda storage,
                            loc: storage)
    duration_model.load_state_dict(checkpoint['state_dict'])
    duration_in_scaler = joblib.load(config.duration.in_scaler_path)
    duration_out_scaler = joblib.load(config.duration.out_scaler_path)
    duration_model.eval()

    # acoustic model
    acoustic_config = OmegaConf.load(join(model_root, "acoustic", "model.yaml"))
    acoustic_model = hydra.utils.instantiate(acoustic_config.netG).to(device)
    checkpoint = torch.load(config.acoustic.checkpoint,
                            map_location=lambda storage,
                            loc: storage)
    acoustic_model.load_state_dict(checkpoint['state_dict'])
    acoustic_in_scaler = joblib.load(config.acoustic.in_scaler_path)
    acoustic_out_scaler = joblib.load(config.acoustic.out_scaler_path)
    acoustic_model.eval()

    # 設定を表示
    # print(OmegaConf.to_yaml(config))
    # synthesize wav file from lab file.
    # 入力するラベルファイルを指定。
    if label_path is None:
        assert config.label_path is not None
        label_path = config.label_path
    else:
        pass
    logger.info('Process the label file: %s', label_path)

    # 出力するwavファイルの設定。
    if out_wav_path is None:
        out_wav_path = config.out_wav_path
    else:
        pass
    logger.info('Synthesize the wav file: %s', out_wav_path)
    wav = synthesis(
        config, device, label_path,
        timelag_model, timelag_config, timelag_in_scaler, timelag_out_scaler,
        duration_model, duration_config, duration_in_scaler, duration_out_scaler,
        acoustic_model, acoustic_config, acoustic_in_scaler, acoustic_out_scaler)
    logger.info('Synthesized the wav file: %s', out_wav_path)

    # サンプルレートとビット深度を指定してファイル出力
    generate_wav_file(config, wav, out_wav_path, logger)


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
    if len(argv) >= 4:
        voicebank_config_yaml_path = argv[1].strip('"')
        label_path = argv[2].strip('"')
        out_wav_path = argv[3].strip('"')
    # コマンドライン引数が不足していれば標準入力で受ける
    else:
        voicebank_config_yaml_path = \
            input("Please input voicebank's config file path\n>>> ").strip('"')
        label_path = \
            input('Please input label file path\n>>> ').strip('"')
        out_wav_path = f'{splitext(label_path)[0]}.wav'

    str_now = datetime.now().strftime('%Y%m%d%h%M%S')
    out_wav_path = out_wav_path.replace('.wav', f'__{str_now}.wav')
    # configファイルのパスを分割する
    config_path, config_name = split(voicebank_config_yaml_path)

    # configファイルを読み取る
    initialize(config_path=relpath(config_path))
    config = compose(config_name=config_name, overrides=[f'+config_path={config_path}'])
    hts2wav(config, label_path, out_wav_path)


if __name__ == '__main__':
    main()
