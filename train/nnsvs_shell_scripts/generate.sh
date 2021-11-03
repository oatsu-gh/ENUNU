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


for s in ${testsets[@]}; do
    for typ in timelag duration acoustic; do
        if [ $typ = "timelag" ]; then
            eval_checkpoint=$timelag_eval_checkpoint
        elif [ $typ = "duration" ]; then
            eval_checkpoint=$duration_eval_checkpoint
        else
            eval_checkpoint=$acoustic_eval_checkpoint
        fi

        checkpoint=$expdir/$typ/${eval_checkpoint}
        name=$(basename $checkpoint)
        xrun $PYTHON_EXE -m nnsvs.bin.generate \
            model.checkpoint=$checkpoint \
            model.model_yaml=$expdir/$typ/model.yaml \
            out_scaler_path=$dump_norm_dir/out_${typ}_scaler.joblib \
            in_dir=$dump_norm_dir/$s/in_${typ}/ \
            out_dir=$expdir/$typ/predicted/$s/${name%.*}/
    done
done
