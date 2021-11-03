#!/bin/bash
# NOTE: the script is supposed to be used called from nnsvs recipes.
# Please don't try to run the shell script directry.

#------------------------------------------------------------------------------
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
#------------------------------------------------------------------------------

for s in ${datasets[@]};
do
    if [ -d conf/prepare_features ]; then
        ext="--config-dir conf/prepare_features.exe"
    else
        ext=""
    fi
    xrun $PYTHON_EXE -m nnsvs.bin.prepare_features $ext \
        utt_list=data/list/$s.list \
        out_dir=$dump_org_dir/$s/  \
        question_path=$question_path \
        timelag=$timelag_features \
        duration=$duration_features \
        acoustic=$acoustic_features
done

# Compute normalization stats for each input/output
mkdir -p $dump_norm_dir
for inout in "in" "out"; do
    if [ $inout = "in" ]; then
        scaler_class="sklearn.preprocessing.MinMaxScaler"
    else
        scaler_class="sklearn.preprocessing.StandardScaler"
    fi
    for typ in timelag duration acoustic;
    do
        find $dump_org_dir/$train_set/${inout}_${typ} -name "*feats.npy" > train_list.txt
        scaler_path=$dump_org_dir/${inout}_${typ}_scaler.joblib
        xrun $PYTHON_EXE -m nnsvs.bin.fit_scaler \
            list_path=train_list.txt \
            scaler.class=$scaler_class \
            out_path=$scaler_path
        rm -f train_list.txt
        cp -v $scaler_path $dump_norm_dir/${inout}_${typ}_scaler.joblib
    done
done

# apply normalization
for s in ${datasets[@]}; do
    for inout in "in" "out"; do
        for typ in timelag duration acoustic;
        do
            xrun $PYTHON_EXE -m nnsvs.bin.preprocess_normalize \
                in_dir=$dump_org_dir/$s/${inout}_${typ}/ \
                scaler_path=$dump_org_dir/${inout}_${typ}_scaler.joblib \
                out_dir=$dump_norm_dir/$s/${inout}_${typ}/
        done
    done
done
