#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
"""
ステージ0 の data_prep.sh をPythonでやる。
"""
import sys

import stage0


def main(path_config_yaml):
    """
    ステージ0の各ステップを順に実行する。
    """
    stage0.copy_files.main(path_config_yaml)
    stage0.check_lab.main(path_config_yaml)
    stage0.force_ust_end_with_rest.main(path_config_yaml)
    stage0.ust2lab.main(path_config_yaml)
    stage0.merge_rest_full_score.main(path_config_yaml)
    stage0.merge_rest_mono_align.main(path_config_yaml)
    stage0.round_lab.main(path_config_yaml)
    stage0.full2mono.main(path_config_yaml)
    stage0.compare_mono_align_and_mono_score.main(path_config_yaml)
    stage0.copy_mono_time_to_full.main(path_config_yaml)
    stage0.segment_lab.main(path_config_yaml)
    stage0.finalize_lab.main(path_config_yaml)
    stage0.generate_train_list.main(path_config_yaml)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        main('config.yaml')
    else:
        main(sys.argv[1].strip('"'))
