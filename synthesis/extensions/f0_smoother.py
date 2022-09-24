#!/usr/bin/env python3
# Copyright (c) 2022 oatsu
"""
f0の極端に急峻な変化をなめらかにする拡張機能。
"""
from argparse import ArgumentParser
from copy import copy
from math import cos, log10, pi
from pprint import pprint

SMOOTHEN_WIDTH = 6  # 3から9くらいが良さそう。
DETECT_THRESHOLD = 0.6
IGNORE_THRESHOLD = 0.01


def repair_sudden_zero_f0(f0_list):
    """
    前後がどちらもf0=0ではないのに、急に出現したf0=0な点を修正する。
    >>> repair_sudden_zero_f0([1, 2, 3, 0, 5, 6])
    [1, 2, 3, 4, 5, 6]
    """
    newf0_list = copy(f0_list)
    for i, f0 in enumerate(f0_list[1:-2], 1):
        if all((f0 == 0, f0_list[i-1] != 0, f0_list[i+1] != 0)):
            newf0_list[i] = (f0_list[i-1] + f0_list[i+1]) / 2
    return newf0_list


def repair_jaggy_f0(f0_list, ignore_threshold):
    """明らかにギザギザしているf0を修復する。

    周囲の動きと明らかに逆の推移をしている区間を修復する。
    relative_f0 関連でノート境界で起こっている可能性がある。
    """
    newf0_list = copy(f0_list)
    indices = []

    # 不良検出
    for i, _ in enumerate(f0_list[2:-2], 2):
        # 計算する区間の両端のf0が無効なときはスキップ
        if any((f0_list[i-1] == 0, f0_list[i] == 0, f0_list[i+1] == 0, f0_list[i+2] == 0)):
            continue
        # 1区間の音程変化
        delta_1 = f0_list[i+1] - f0_list[i]
        # 3区間の音程変化
        delta_3 = f0_list[i+2] - f0_list[i-1]
        # ゼロ除算しそうなときはスキップ
        if delta_3 == 0:
            continue
        # f0変化が小さいときに誤判定しないようにスキップ
        if abs(delta_1) < ignore_threshold:
            continue
        # 2点間の変化が、その前後の点の変化と逆を向いている場合を検出する。
        if delta_1 * delta_3 < 0:
            indices.append(i)
    print("f0遷移方向が逆になっている区間: ", indices)

    # 修正すべき区間の周辺の点を直線を引いて(半ば強引に)修復
    for idx in indices:
        newf0_list[idx - 1] = \
            0.75 * newf0_list[idx - 2] + 0.25 * newf0_list[idx + 2]
        newf0_list[idx] = \
            0.5 * newf0_list[idx - 2] + 0.5 * newf0_list[idx + 2]
        newf0_list[idx + 1] = \
            0.25 * newf0_list[idx - 2] + 0.75 * f0_list[idx + 2]

    return newf0_list


def get_rapid_f0_change_indices(f0_list: list, detect_threshold: list, ignore_threshold):
    """急峻なf0変化を検出する。

    1区間での変化量が前後を含めた3区間の変化量の半分を上回る場合、急峻な変化とみなす。
    """
    indices = []
    # f0のリスト内ループ
    for i, _ in enumerate(f0_list[1:-2], 1):
        # 計算する区間の両端のf0が無効なときはスキップ
        if any((f0_list[i-1] == 0, f0_list[i] == 0, f0_list[i+1] == 0, f0_list[i+2] == 0)):
            continue
        # 1区間の音程変化
        delta_1 = f0_list[i+1] - f0_list[i]
        # 3区間の音程変化
        delta_3 = f0_list[i+2] - f0_list[i-1]
        # ゼロ除算しそうなときはスキップ
        if delta_3 == 0:
            continue
        # f0変化が小さいときに誤判定しないようにスキップ
        if abs(delta_1) < ignore_threshold:
            continue
        # 一定以上の急峻さで検出
        if delta_1 / delta_3 > detect_threshold:
            indices.append(i)
    return indices

    # def get_rapid_f0_change_indices(f0_list: list, detect_threshold: list, ignore_threshold, width=SMOOTHEN_WIDTH):
    #     """急峻なf0変化を検出する。

    #     1区間での変化量が前後を含めた3区間の変化量の半分を上回る場合、急峻な変化とみなす。
    #     3区間ではなく任意の区間で設定できるようにした。
    #     """
    #     indices = []
    #     # f0のリスト内ループ
    #     for i, _ in enumerate(f0_list[width:-(width+1)], width):
    #         # 計算する区間の中に休符があるときはスキップ
    #         if any((f0_list[i-1] == 0, f0_list[i] == 0, f0_list[i+width] == 0, f0_list[i+width] == 0)):
    #             continue
    #         # 1区間の音程変化
    #         delta_1 = f0_list[i+1] - f0_list[i]
    #         # 3区間の音程変化
    #         delta_wide = f0_list[i+width+1] - f0_list[i-width]
    #         # ゼロ除算しそうなときはスキップ
    #         if delta_wide == 0:
    #             continue
    #         # f0変化が小さいときに誤判定しないようにスキップ
    #         if abs(delta_1) < ignore_threshold:
    #             continue
    #         # 一定以上の急峻さで検出
    #         if delta_1 / delta_wide > detect_threshold:
    #             indices.append(i)
    #     return indices


def reduce_indices(indices):
    """時間的に近い2点で急速なf0変化が検出された場合、両方補正すると変になるので削減する。

    # 連続して検出された場合
    >>> reduce_indices([10, 11])
    [10]

    # 1つだけ間をあけて検出された場合
    >>> reduce_indices([10, 12])
    [11]
    >>> reduce_indices([10, 12, 16])
    [11, 16]

    >>> reduce_indices([10, 13])
    [11]

    # 2回連続で処理する場合(1)
    >>> reduce_indices([10, 11, 12])
    [11]
    >>> reduce_indices([10, 12, 14])
    [12]
    >>> reduce_indices([10, 13, 14])
    [12]
    >>> reduce_indices([10, 11, 13])
    [11]
    >>> reduce_indices([10, 12, 13])
    [12]

    """
    indices = copy(indices)

    for i, _ in enumerate(indices[:-1]):
        delta = indices[i+1] - indices[i]
        if delta == 1:
            indices[i] = None
            indices[i + 1] = indices[i + 1] - 1
        elif delta == 2:
            indices[i] = None
            indices[i + 1] = indices[i + 1] - 1
        elif delta == 3:
            indices[i] = None
            indices[i + 1] = indices[i + 1] - 2
        else:
            pass
    indices = [idx for idx in indices if idx is not None]

    return indices


def get_adjusted_widths(f0_list: list, rapid_f0_change_indices: list, default_width: int):
    """基準値を計算するための値に0が含まれてしまうときに幅を狭くして返す。

    返すリストは 0 以上の整数からなるリストで、
    0の時は補正を行わないことになるのでスキップしていいと思う。
    """
    # 万が一負の値が入ったていたら止める
    assert default_width >= 0

    # 結果を格納するリスト
    adjusted_widths = []
    len_f0_list = len(f0_list)

    # 指定されたf0の点の周辺を順に調べる
    for f0_idx in rapid_f0_change_indices:
        # 急峻な変化をする2点の前後を近い順に調査
        width = default_width
        # そもそも両端がIndexErrorになってしまうのを回避する必要がある。
        # f0の長さが足りない場合は補正幅を狭める。
        while (f0_idx - width) < 0 or (f0_idx + width + 1) > len_f0_list:
            width -= 1
        # 両端のf0が0な場合は、平滑化の幅を狭める。
        # ただし、wが負になって右側と左側のf0の位置が逆転する前にループを止める。
        # while width > 0 and (f0_list[f0_idx - width] == 0 or f0_list[f0_idx + width + 1] == 0):
        while width > 0 and (0 in f0_list[f0_idx - width: f0_idx + width + 2]):
            width -= 1
        # 調整後の値をリストに追加
        adjusted_widths.append(width)

    # 一応長さ確認
    assert len(adjusted_widths) == len(rapid_f0_change_indices)

    # 調整した幅の一覧をリストにして返す
    return adjusted_widths


def get_target_f0_list(f0_list: list, rapid_f0_change_indices: list, adjusted_widths: list):
    """補正に用いる基準値(平均値)を計算する。

    中心となる2点からwidth分だけ前後の両端の点の平均値を、補正に用いる値とする。
    その値をリストにして返す。
    """
    # 念のため
    assert len(rapid_f0_change_indices) == len(adjusted_widths)

    # 補正の基準にするf0の値
    target_f0_list = []

    # 急峻な変化がある場所について、前から順に平均値を計算していく。
    for f0_idx, width in zip(rapid_f0_change_indices, adjusted_widths):
        f0_left = f0_list[f0_idx - width]
        f0_right = f0_list[f0_idx + width + 1]
        target_f0 = (f0_left + f0_right) / 2
        target_f0_list.append(target_f0)

    # こんな感じのリストを返す → [(f0_idx, width), ...]
    return target_f0_list


def get_smoothened_f0_list(f0_list, width, detect_threshold, ignore_threshold):
    """修正すべき区間と、修正の基準として使う値を返す。
    [(idx, target_f0), ...]

    """
    # もとのf0を残すために複製して使う。
    f0_list = copy(f0_list)

    # 補正したほうがいい場所を検出する。
    rapid_f0_change_indices = get_rapid_f0_change_indices(
        f0_list,
        detect_threshold,
        ignore_threshold
    )
    # rapid_f0_change_indices = reduce_indices(rapid_f0_change_indices)

    # 不具合が起きないように補正幅を調整
    adjusted_widths = get_adjusted_widths(
        f0_list,
        rapid_f0_change_indices,
        width
    )
    assert len(rapid_f0_change_indices) == len(adjusted_widths)

    # 該当箇所の9区間の最初と最後の平均 (元の長さ: N-9, 追加後長さ: N-1)
    # ・-・-・-・-・=・-・-・-・-・
    target_f0_list = get_target_f0_list(
        f0_list,
        rapid_f0_change_indices,
        adjusted_widths
    )
    assert len(rapid_f0_change_indices) == len(target_f0_list)

    # 動作内容確認用に出力
    # pprint(list(zip(rapid_f0_change_indices, adjusted_widths, target_f0_list)))

    # 検出済みの場所と、その周辺に適用するターゲット値の組でループする
    for (f0_idx, width, target_f0) in zip(rapid_f0_change_indices, adjusted_widths, target_f0_list):
        # 調整不要(不可能)な場合はスキップ
        if width <= 0:
            continue
        # 修正必要なf0点の前後数点を、近くから順に補正する。
        for i in range(width):
            # 元の値をどのくらい使うか
            ratio_of_original_f0 = cos(
                pi * ((width - i) / (2 * width + 1)))
            # ターゲット値にどのくらい寄せるか
            ratio_of_target_f0 = 1 - ratio_of_original_f0
            # 過去側のf0の点を補正する
            f0_list[f0_idx - i] = (
                ratio_of_target_f0 * target_f0 +
                ratio_of_original_f0 * f0_list[f0_idx - i]
            )
            # 未来側のf0の点を補正する
            f0_list[f0_idx + i + 1] = (
                ratio_of_target_f0 * target_f0 +
                ratio_of_original_f0 * f0_list[f0_idx + i + 1]
            )

    print(f'Smoothed {len(rapid_f0_change_indices)} points')
    # [(idx, target_f0), ...] の形にして返す
    return f0_list


def main():
    """全体時の処理をやる
    """
    parser = ArgumentParser()
    parser.add_argument('--f0', help='f0の情報を持ったCSVファイルのパス')

    # 使わない引数は無視して、必要な情報だけ取り出す。
    args, _ = parser.parse_known_args()

    # f0ファイルの入出力パス
    # ENUNUからの呼び出しがうまくいっていないか、テスト実行の場合
    if args.f0 is None:
        path_in = input('path: ').strip('\'\"')
        path_out = path_in.replace('.csv', '_out.csv')
    # ENUNUから呼び出しているとき
    else:
        path_in = str(args.f0).strip('\'"')
        path_out = path_in

    # f0のファイルを読み取る
    with open(path_in, 'r', encoding='utf-8') as f:
        f0_list = list(map(float, f.read().splitlines()))

    # 底を10とした対数に変換する (長さ: N)
    # f0が負や0だと対数変換できないのを回避しつつ、log(f0)>0 となるようにする。
    log_f0_list = [log10(max(f0, 1)) for f0 in f0_list]

    # 突発的な0Hzを直す。
    print('Repairing unnaturally sudden 0Hz in f0')
    log_f0_list = repair_sudden_zero_f0(log_f0_list)

    # ギザギザしてるのを直す
    # log_f0_list = repair_jaggy_f0(
    #     log_f0_list, ignore_threshold=IGNORE_THRESHOLD)

    # なめらかにする
    print('Smoothening f0')
    new_log_f0_list = get_smoothened_f0_list(
        log_f0_list,
        width=SMOOTHEN_WIDTH,
        detect_threshold=DETECT_THRESHOLD,
        ignore_threshold=IGNORE_THRESHOLD
    )

    # log(f0) でエラーが出ないためにf0=1Hzにしてあるのを0Hzに戻す。
    new_f0_list = []
    for log_f0 in new_log_f0_list:
        # log10(f0)=0 のときに f0=1Hz ではなく 0Hz にする。
        if log_f0 == 0:
            f0 = 0
        else:
            f0 = 10 ** log_f0
        new_f0_list.append(f0)

    # 文字列にする
    s = '\n'.join(list(map(str, new_f0_list)))

    # 出力
    with open(path_out, 'w', encoding='utf-8') as f:
        f.write(s)


if __name__ == "__main__":
    print('f0_smoother.py (2022-04-24) ---------------------------')
    main()
    print('-------------------------------------------------------')
