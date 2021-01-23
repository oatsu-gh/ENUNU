#! /bin/bash
# 休符以外の音素数や音素記号がSinsyとDBのラベルで完全一致する前提で処理する。

script_dir=$(cd $(dirname ${BASH_SOURCE:-$0}); pwd)

if [ $# -ne 1 ];then
    echo "USAGE: data_prep.sh config_path"
    exit 1
fi

config_path=$1

# Step 1a:
# フルラベルを生成する。モノラベルは作らない。
# sinsy_full, sinsy_mono, mono_label の3フォルダにファイルが保存される。
python $script_dir/0_1a_gen_lab.py $config_path

# Step 1b:
# utaupyを使ってフルラベルとモノラベルを読んで、
# Sinsyのフルラベルをutaupy仕様に調整する。
# オブジェクトの状態で休符を結合して、
# オブジェクトの状態で数値を丸めて、
# ファイルとして保存する。
# このとき、休符周辺のコンテキストがutaupyの仕様に調整される。
# また、フルラベルをもとにモノラベルも生成して保存する。(丸めたもののみ保存)
# sinsy_full_round, sinsy_mono_round, mono_label_round の3フォルダにファイルが保存される。
python $script_dir/0_1b_remove_br_and_round.py $config_path

# Step 2:
# Sinsyの出力するラベルファイル(sinsy_mono_round)と、
# DBに含まれるラベルファイル(mono_label_round)の整合性をチェックする。
# 問題なければmono_dtwのフォルダに保存する。(dtwはしていない)
# mono_dtw の1フォルダにファイルが保存される。
python $script_dir/0_2_align_lab.py $config_path

# NOTE: チェックするだけならmono_dtwのフォルダいらなくない？

# Step 3a:
# Perform segmentation.
# Sinsyのフルラベル(sinsy_full_round)に
# DBのモノラベル(mono_dtw)の時刻をコピーしし、
# フルラベルファイル(full_dtw)として保存する。
# full_dtw の1フォルダにファイルが保存される。
python $script_dir/0_3a_copy_mono_time_to_full.py $config_path

# Step 3b:
# ラベルファイルを休符開始位置で分割する。
# 分割対象ファイルは sinsy_full_round, full_dtw, sinsy_mono_round, mono_dtw
# 保存先のフォルダは sinsy_full_round_seg, full_dtw_seg, sinsy_mono_round_seg, mono_label_round_seg
# NOTE: mono_dtw の保存先が mono_label_round_seg なことに注意。
# sinsy_full_round_seg, full_dtw_seg,
# sinsy_mono_round_seg, mono_label_round_seg の4フォルダにファイルが保存される。
python $script_dir/0_3b_segment_lab.py $config_path

# Step 4:
# Make labels for training
# 1. time-lag model
# 2. duration model
# 3. acoustic model
# 各モデルの学習用に、ラベルファイルを複製する。
# acousticモデルに関しては音声ファイルも複製する。
python $script_dir/0_4_finalize_lab.py $config_path
