#! /usr/bin/env python3
# coding: utf-8
# Copyright (c) 2020 oatsu
"""
nnsvsの学習時のログファイル train.log を読み取り、CSVに変換する。
グラフ生成はしたいがとりあえずExcelでつくる。
"""
from glob import glob
# from datetime import datetime
# from pprint import pprint
from os.path import basename, splitext

from tqdm import tqdm


def read_log(path_log):
    """
    ログファイルを読み取って、結果を抽出して返す。
    """
    # ファイル読み取り
    with open(path_log, 'r') as fl:
        lines = fl.readlines()
    # lossの値を格納するリスト
    loss_train_no_dev = []
    loss_dev = []
    # lossの値を取得してリストに追加
    for line in lines:
        if '[train_no_dev] [Epoch ' in line:
            loss_train_no_dev.append(line.split()[7])
        elif '[dev] [Epoch ' in line:
            loss_dev.append(line.split()[7])
    # 結果を返す
    return loss_train_no_dev, loss_dev


def generate_csv(loss_train_no_dev, loss_dev, path_csv_out):
    """
    loss_train_no_dev (list)
    loss_dev (list)
    """
    epoch_number_list = (str(i+1) for i in range(len(loss_train_no_dev)))
    l_data = list(zip(epoch_number_list, loss_train_no_dev, loss_dev))
    # 出力用の文字列にする
    s_csv = 'epoch, loss(train_no_dev), loss(dev)\n'
    s_csv += '\n'.join([','.join(v) for v in l_data])
    with open(path_csv_out, 'w') as fc:
        fc.write(s_csv)


def main():
    path_log_dir = input('path_log_dir: ').strip('"')
    list_path_log = glob(f'{path_log_dir}/**/*.log', recursive=True)
    for i, path_log in enumerate(tqdm(list_path_log)):
        loss_train_no_dev, loss_dev = read_log(path_log)
        # datetime_now = datetime.now().strftime("%Y%m%d_%H%M%S")
        path_csv_out = f'{splitext(basename(path_log))[0]}_{i}.csv'
        generate_csv(loss_train_no_dev, loss_dev, path_csv_out)


if __name__ == '__main__':
    main()
    input('おわり')
