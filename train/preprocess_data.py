#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
"""
ステージ0 の data_prep.sh をPythonでやる。
"""
import logging
from sys import argv

from stage0 import (assert_wav_is_longer_than_lab, check_lab,
                    check_lab_after_segmentation, check_wav,
                    compare_mono_align_and_mono_score, copy_files,
                    copy_mono_time_to_full, finalize_lab,
                    force_ust_end_with_rest, full2mono, generate_train_list,
                    merge_rest_full_score, merge_rest_mono_align, round_lab,
                    segment_lab, ust2lab)


def main(path_config_yaml):
    """
    ステージ0の各ステップを順に実行する。
    """
    # ログ出力設定
    stream_handler = logging.StreamHandler()
    file_handler = logging.FileHandler(f'{__file__}.log', mode='w',)
    logging.basicConfig(level=logging.INFO, handlers=[stream_handler, file_handler])

    # singing_databaseフォルダ の中にあるファイルを dataフォルダにコピーする。
    copy_files.main(path_config_yaml)
    # mono_align (labフォルダのファイル) の中の音素の発生時刻が負でないか点検する。
    check_lab.main(path_config_yaml)
    # wavファイルのフォーマットが適切か点検する。
    check_wav.main(path_config_yaml)
    # ustファイルの最後が休符じゃないときに警告する。
    force_ust_end_with_rest.main(path_config_yaml)
    # ustファイル を labファイル に変換して、full_score として保存する。
    ust2lab.main(path_config_yaml)

    # mono_align (labフォルダのファイル) の連続する休符を結合する。
    merge_rest_mono_align.main(path_config_yaml)
    # full_score の連続する休符を結合する。
    merge_rest_full_score.main(path_config_yaml)

    # mono_align (labフォルダのファイル) を丸めて mono_align_round に保存する。
    # full_score を丸めて full_score_round に保存する。
    round_lab.main(path_config_yaml)

    # roundとか済ませた full_score をモノラベルにして mono_score として保存する。
    full2mono.main(path_config_yaml)

    # mono_align と mono_score の音素記号が一致しているか検査する。
    compare_mono_align_and_mono_score.main(path_config_yaml)

    # mono_align の時刻を full_score にコピーして full_align として保存する。
    # この時、最後の休符終了時刻だけは mono_align ではなく full_score の値を取得する。
    copy_mono_time_to_full.main(path_config_yaml)

    # wavファイルがfull_alignより長いことを確認する。
    assert_wav_is_longer_than_lab.main(path_config_yaml)

    # labファイルを分割する。
    # - mode='long' : pau-pau または pau-sil の並びの境界で切断する。
    # - mode='short' : pauの開始位置で切断する。
    segment_lab.main(path_config_yaml)

    # 分割後のラベルの発声時間が負になっていないか再度点検する。
    check_lab_after_segmentation.main(path_config_yaml)

    # いろいろする
    # - 学習用ファイルを各フォルダに配置する。
    # - wavファイルを分割してascoustic用のフォルダに置く。
    # - acoustic用のラベルの開始時刻を0にする。
    finalize_lab.main(path_config_yaml)

    # listを作成する
    generate_train_list.main(path_config_yaml)


if __name__ == '__main__':
    if len(argv) == 1:
        main('config.yaml')
    else:
        main(argv[1].strip('"'))
