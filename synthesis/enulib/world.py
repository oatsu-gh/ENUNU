#!/usr/bin/env python3
# Copyright (c) 2022 oatsu
"""
acousticのファイルをWAVファイルにするまでの処理を行う。
"""
import hydra
import numpy as np
import pysptk
import pyworld
from enulib.common import set_checkpoint, set_normalization_stat
from hydra.utils import to_absolute_path
from nnmnkwii.io import hts
from nnmnkwii.postfilters import merlin_post_filter
from nnsvs.dsp import bandpass_filter
from nnsvs.gen import (
    gen_spsvs_static_features,
    gen_world_params
)
from nnsvs.logger import getLogger
from nnsvs.multistream import get_static_stream_sizes
from nnsvs.pitch import lowpass_filter
from nnsvs.postfilters import variance_scaling
from omegaconf import DictConfig, OmegaConf
from scipy.io import wavfile
import torch

logger = None


def estimate_bit_depth(wav: np.ndarray) -> str:
    """
    wavformのビット深度を判定する。
    16bitか32bit
    16bitの最大値: 32767
    32bitの最大値: 2147483647
    """
    # 音量の最大値を取得
    max_gain = np.nanmax(np.abs(wav))
    # 学習データのビット深度を推定(8388608=2^24)
    if max_gain > 8388608:
        return 'int32'
    if max_gain > 8:
        return 'int16'
    return 'float'


def generate_wav_file(config: DictConfig, wav, out_wav_path):
    """
    ビット深度を指定してファイル出力(32bit float)
    """
    # 出力された音量をもとに、学習に使ったビット深度を推定
    training_data_bit_depth = estimate_bit_depth(wav)
    # print(training_data_bit_depth)

    # 16bitで学習したモデルの時
    if training_data_bit_depth == 'int16':
        wav = wav / 32767
    # 32bitで学習したモデルの時
    elif training_data_bit_depth == 'int32':
        wav = wav / 2147483647
    elif training_data_bit_depth == 'float':
        pass
    # なぜか16bitでも32bitでもないとき
    else:
        raise ValueError('WAVのbit深度がよくわかりませんでした。')

    # 音量ノーマライズする場合
    if config.gain_normalize:
        wav = wav / np.max(np.abs(wav))

    # ファイル出力
    wav = wav.astype(np.float32)
    wavfile.write(out_wav_path, rate=config.sample_rate, data=wav)


# def acoustic2wav(config: DictConfig, path_timing, path_acoustic, path_wav):
#     """
#     Acousticの行列のCSVを読んで、WAVファイルとして出力する。
#     """
#     # loggerの設定
#     global logger  # pylint: disable=global-statement
#     logger = getLogger(config.verbose)
#     logger.info(OmegaConf.to_yaml(config))

#     # load labels and question
#     duration_modified_labels = hts.load(path_timing).round_()

#     # CUDAが使えるかどうか
#     # device = 'cuda' if torch.cuda.is_available() else 'cpu'

#     # 各種設定を読み込む
#     typ = 'acoustic'
#     model_config = OmegaConf.load(to_absolute_path(config[typ].model_yaml))

#     # hedファイルを読み取る。
#     question_path = to_absolute_path(config.question_path)
#     # hts2wav.pyだとこう↓-----------------
#     # これだと各モデルに別個のhedを適用できる。
#     # if config[typ].question_path is None:
#     #     config[typ].question_path = config.question_path
#     # --------------------------------------

#     # hedファイルを辞書として読み取る。
#     binary_dict, numeric_dict = hts.load_question_set(
#         question_path, append_hat_for_LL=False
#     )

#     # pitch indices in the input features
#     pitch_idx = len(binary_dict) + 1
#     # pitch_indices = np.arange(len(binary_dict), len(binary_dict)+3)

#     # pylint: disable=no-member
#     # Acousticの数値を読み取る
#     acoustic_features = np.loadtxt(
#         path_acoustic, delimiter=',', dtype=np.float64
#     )

#     # 設定の一部を取り出す

#     generated_waveform = gen_waveform(
#         duration_modified_labels,
#         acoustic_features,
#         binary_dict,
#         numeric_dict,
#         model_config.stream_sizes,
#         model_config.has_dynamic_features,
#         subphone_features=config.acoustic.subphone_features,
#         log_f0_conditioning=config.log_f0_conditioning,
#         pitch_idx=pitch_idx,
#         num_windows=model_config.num_windows,
#         post_filter=config.acoustic.post_filter,
#         sample_rate=config.sample_rate,
#         frame_period=config.frame_period,
#         relative_f0=config.acoustic.relative_f0
#     )

#     # 音量を調整して 32bit float でファイル出力
#     generate_wav_file(config, generated_waveform, path_wav)


def acoustic2world(config: DictConfig, path_timing, path_acoustic,
                   path_f0, path_spcetrogram, path_aperiodicity,
                   trajectory_smoothing=True,
                   trajectory_smoothing_cutoff=50,
                   vibrato_scale=1.0,
                   vuv_threshold=0.1):
    """
    Acousticの行列のCSVを読んで、WAVファイルとして出力する。
    """
    # loggerの設定
    global logger  # pylint: disable=global-statement
    logger = getLogger(config.verbose)
    logger.info(OmegaConf.to_yaml(config))

    # load labels and question
    duration_modified_labels = hts.load(path_timing).round_()

    # CUDAが使えるかどうか
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # 各種設定を読み込む
    acoustic_model_config = OmegaConf.load(to_absolute_path(config["acoustic"].model_yaml))

    # hedファイルを読み取る。
    question_path = to_absolute_path(config.question_path)
    # hts2wav.pyだとこう↓-----------------
    # これだと各モデルに別個のhedを適用できる。
    # if config[typ].question_path is None:
    #     config[typ].question_path = config.question_path
    # --------------------------------------

    # hedファイルを辞書として読み取る。
    binary_dict, numeric_dict = hts.load_question_set(
        question_path, append_hat_for_LL=False
    )

    # pitch indices in the input features
    pitch_idx = len(binary_dict) + 1
    # pitch_indices = np.arange(len(binary_dict), len(binary_dict)+3)

    # pylint: disable=no-member
    # Acousticの数値を読み取る
    acoustic_features = np.loadtxt(
        path_acoustic, delimiter=',', dtype=np.float64
    )

    # postfilter setting
    try:
        # substitute of maybe_set_checkpoints_(config)
        set_checkpoint(config, "postfilter")
        # substitute of maybe_set_normalization_stats_(config)
        set_normalization_stat(config, "postfilter")
    except:
        logger.info(f"There is no post_filter_type setting so merlin is used.")
        
    try:
        post_filter_type = config.acoustic.post_filter_type
    except: 
        logger.info(f"There is no post_filter_type setting so merlin is used.")
        post_filter_type = "merlin"

    if post_filter_type not in ["merlin", "nnsvs", "gv", "none"]:
        logger.info(f"Unknown post-filter type: {post_filter_type} so merlin is used.")
        post_filter_type = "merlin"
        
    if config.acoustic.post_filter is not None:
        logger.info("post_filter is deprecated. Use post_filter_type instead.")
    
    try:
        postfilter_out_scaler = joblib.load(config["postfilter"].out_scaler_path)
        # Apply GV post-filtering
        if post_filter_type in ["nnsvs", "gv"]:
            logger.info("Apply GV post-filtering")        
            static_stream_sizes = get_static_stream_sizes(
                acoustic_model_config.stream_sizes,
                acoustic_model_config.has_dynamic_features,
                acoustic_model_config.num_windows,
            )
            mgc_end_dim = static_stream_sizes[0]
            acoustic_features[:, :mgc_end_dim] = variance_scaling(
                postfilter_out_scaler.var_.reshape(-1)[:mgc_end_dim],
                acoustic_features[:, :mgc_end_dim],
                offset=2,
            )
            # bap
            bap_start_dim = sum(static_stream_sizes[:3])
            bap_end_dim = sum(static_stream_sizes[:4])
            acoustic_features[:, bap_start_dim:bap_end_dim] = variance_scaling(
                postfilter_out_scaler.var_.reshape(-1)[bap_start_dim:bap_end_dim],
                acoustic_features[:, bap_start_dim:bap_end_dim],
                offset=0,
            )

            # Learned post-filter using nnsvs
            if post_filter_type == "nnsvs":
                postfilter_model_config = OmegaConf.load(to_absolute_path(config["postfilter"].model_yaml))
                postfilter_model = hydra.utils.instantiate(postfilter_model_config.netG).to(device)

                logger.info("Apply mgc_postfilter")        
                in_feats = (
                    torch.from_numpy(acoustic_features).float().unsqueeze(0)                
                )
                in_feats = postfilter_out_scaler.transform(in_feats).float().to(device)
                out_feats = postfilter_model.inference(in_feats, [in_feats.shape[1]])
                acoustic_features = (
                    postfilter_out_scaler.inverse_transform(out_feats.cpu())
                    .squeeze(0)
                    .numpy()
                )
    except Exception as e:
        logger.info(e)
        logger.info("Unable to use NNSVS/GV postfilter")

    # Generate static features from acoustic features
    mgc, lf0, vuv, bap = gen_spsvs_static_features(
        duration_modified_labels,
        acoustic_features,
        binary_dict,
        numeric_dict,
        acoustic_model_config.stream_sizes,
        acoustic_model_config.has_dynamic_features,
        config.acoustic.subphone_features,
        pitch_idx,
        acoustic_model_config.num_windows,
        config.frame_period,
        config.acoustic.relative_f0,
        vibrato_scale,
        vuv_threshold
    )

    # NOTE: spectral enhancement based on the Merlin's post-filter implementation
    if post_filter_type == "merlin":
        alpha = pysptk.util.mcepalpha(config.sample_rate)
        mgc = merlin_post_filter(mgc, alpha)
    
        # Remove high-frequency components of mgc/bap
        # NOTE: It seems to be effective to suppress artifacts of GAN-based post-filtering

    if trajectory_smoothing:
        modfs = int(1 / 0.005)
        for d in range(mgc.shape[1]):
            mgc[:, d] = lowpass_filter(
                mgc[:, d], modfs, cutoff=trajectory_smoothing_cutoff
            )
        for d in range(bap.shape[1]):
            bap[:, d] = lowpass_filter(
                bap[:, d], modfs, cutoff=trajectory_smoothing_cutoff
            )

    # Generate WORLD parameters
    f0, spectrogram, aperiodicity = gen_world_params(
        mgc, lf0, vuv, bap, config.sample_rate, vuv_threshold=vuv_threshold
    )
            
    # csvファイルとしてf0の行列を出力
    for path, array in (
        (path_f0, f0),
        (path_spcetrogram, spectrogram),
        (path_aperiodicity, aperiodicity)
    ):
        np.savetxt(
            path,
            array,
            fmt='%.16f',
            delimiter=','
        )


def world2wav(config: DictConfig, path_f0, path_spectrogram, path_aperiodicity, path_wav):
    """WORLD用のパラメータからWAVファイルを生成する。"""
    f0 = np.loadtxt(
        path_f0, delimiter=',', dtype=np.float64
    )
    spectrogram = np.loadtxt(
        path_spectrogram, delimiter=',', dtype=np.float64
    )
    aperiodicity = np.loadtxt(
        path_aperiodicity, delimiter=',', dtype=np.float64
    )
    wav = pyworld.synthesize(
        f0, spectrogram, aperiodicity, config.sample_rate, config.frame_period
    )

    wav = bandpass_filter(wav, config.sample_rate)
    
    # 音量を調整して 32bit float でファイル出力
    generate_wav_file(config, wav, path_wav)
