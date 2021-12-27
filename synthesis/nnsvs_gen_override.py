#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
# Copyright (c) 2021 maka_makamo
# Copyright (c) 2020 Ryuichi Yamamoto
"""
nnsvs.gen_waveform で waveform のほかに
f0, sp, bap, generated_waveform を返すようにしたいので上書きする。
"""
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

import numpy as np
import pysptk
import pyworld
from nnmnkwii.frontend import merlin as fe
from nnmnkwii.postfilters import merlin_post_filter
from nnmnkwii.preprocessing.f0 import interp1d
from nnsvs.gen import _midi_to_hz, get_windows
from nnsvs.multistream import get_static_stream_sizes, split_streams


def gen_waveform(labels,
                 acoustic_features,
                 binary_dict,
                 continuous_dict, stream_sizes,
                 has_dynamic_features,
                 subphone_features="coarse_coding",
                 log_f0_conditioning=True,
                 pitch_idx=None,
                 num_windows=3,
                 post_filter=True,
                 sample_rate=48000,
                 frame_period=5,
                 relative_f0=True):
    # pylint: disable=no-member
    windows = get_windows(num_windows)
    # Apply MLPG if necessary
    if np.any(has_dynamic_features):
        static_stream_sizes = get_static_stream_sizes(
            stream_sizes, has_dynamic_features, len(windows))
    else:
        static_stream_sizes = stream_sizes

    # Split multi-stream features
    mgc, target_f0, vuv, bap = split_streams(acoustic_features, static_stream_sizes)

    # Gen waveform by the WORLD vocodoer
    fftlen = pyworld.get_cheaptrick_fft_size(sample_rate)
    alpha = pysptk.util.mcepalpha(sample_rate)

    if post_filter:
        mgc = merlin_post_filter(mgc, alpha)

    spectrogram = pysptk.mc2sp(mgc, fftlen=fftlen, alpha=alpha)
    aperiodicity = pyworld.decode_aperiodicity(bap.astype(np.float64), sample_rate, fftlen)

    # fill aperiodicity with ones for unvoiced regions
    aperiodicity[vuv.reshape(-1) < 0.5, :] = 1.0
    # WORLD fails catastrophically for out of range aperiodicity
    aperiodicity = np.clip(aperiodicity, 0.0, 1.0)

    # F0
    if relative_f0:
        diff_lf0 = target_f0
        # need to extract pitch sequence from the musical score
        linguistic_features = fe.linguistic_features(labels,
                                                     binary_dict, continuous_dict,
                                                     add_frame_features=True,
                                                     subphone_features=subphone_features)
        f0_score = _midi_to_hz(linguistic_features, pitch_idx, False)[:, None]
        lf0_score = f0_score.copy()
        nonzero_indices = np.nonzero(lf0_score)
        lf0_score[nonzero_indices] = np.log(f0_score[nonzero_indices])
        lf0_score = interp1d(lf0_score, kind="slinear")

        f0 = diff_lf0 + lf0_score
        f0[vuv < 0.5] = 0
        f0[np.nonzero(f0)] = np.exp(f0[np.nonzero(f0)])
    else:
        f0 = target_f0
        f0[vuv < 0.5] = 0
        f0[np.nonzero(f0)] = np.exp(f0[np.nonzero(f0)])

    generated_waveform = pyworld.synthesize(f0.flatten().astype(np.float64),
                                            spectrogram.astype(np.float64),
                                            aperiodicity.astype(np.float64),
                                            sample_rate, frame_period)

    # 音量を小さくする(音割れ防止)
    # TODO: ここのかける定数をいい感じにする
    spectrogram *= 0.000000001
    sp = pyworld.code_spectral_envelope(spectrogram, sample_rate, 60)

    return f0, sp, bap, generated_waveform
