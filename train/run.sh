#!/bin/bash

##########
# customized for nnsvs on WSL(Ubuntu)
##########
# Set bash to 'debug' mode, it will exit on :
# -e 'error', -u 'undefined variable', -o ... 'error in pipeline', -x 'print commands',
set -e
set -u
set -o pipefail

function xrun () {
    set -x
    $@
    set +x
}

#change-----------------------------------------------------------
NNSVS_ROOT=../nnsvs
#change-----------------------------------------------------------
script_dir=$(cd $(dirname ${BASH_SOURCE:-$0}); pwd)
NNSVS_COMMON_ROOT=$NNSVS_ROOT/egs/_common/spsvs
NO2_ROOT=$NNSVS_ROOT/egs/_common/no2
. $NNSVS_ROOT/utils/yaml_parser.sh || exit 1;

eval $(parse_yaml "./config.yaml" "")

train_set="train_no_dev"
dev_set="dev"
eval_set="eval"
datasets=($train_set $dev_set $eval_set)
testsets=($dev_set $eval_set)

dumpdir=dump
dump_org_dir=$dumpdir/$spk/org
dump_norm_dir=$dumpdir/$spk/norm

stage=0
stop_stage=0

. $NNSVS_ROOT/utils/parse_options.sh || exit 1;

# exp name
if [ -z ${tag:=} ]; then
    expname=${spk}
else
    expname=${spk}_${tag}
fi
expdir=exp/$expname

if [ ${stage} -le -1 ] && [ ${stop_stage} -ge -1 ]; then
    if [ ! -e $db_root ]; then
	cat<<EOF
singing-database files were not found
EOF
    fi
fi

if [ ${stage} -le 0 ] && [ ${stop_stage} -ge 0 ]; then
    echo "stage 0: Data preparation"
    #change↓------------------------------------------------------
    rm -rf data dump
    bash data_prep.sh ./config.yaml
    #change↑------------------------------------------------------
fi

if [ ${stage} -le 1 ] && [ ${stop_stage} -ge 1 ]; then
    echo "stage 1: Feature generation"
    . $NNSVS_COMMON_ROOT/feature_generation.sh
fi

if [ ${stage} -le 2 ] && [ ${stop_stage} -ge 2 ]; then
    echo "stage 2: Training time-lag model"
    . $NNSVS_COMMON_ROOT/train_timelag.sh
fi

if [ ${stage} -le 3 ] && [ ${stop_stage} -ge 3 ]; then
    echo "stage 3: Training duration model"
    . $NNSVS_COMMON_ROOT/train_duration.sh
fi

if [ ${stage} -le 4 ] && [ ${stop_stage} -ge 4 ]; then
    echo "stage 4: Training acoustic model"
    . $NNSVS_COMMON_ROOT/train_acoustic.sh
fi

if [ ${stage} -le 5 ] && [ ${stop_stage} -ge 5 ]; then
    echo "stage 5: Generate features from timelag/duration/acoustic models"
    . $NNSVS_COMMON_ROOT/generate.sh
fi

if [ ${stage} -le 6 ] && [ ${stop_stage} -ge 6 ]; then
    echo "stage 6: Synthesis waveforms"
    . $NNSVS_COMMON_ROOT/synthesis.sh
fi
