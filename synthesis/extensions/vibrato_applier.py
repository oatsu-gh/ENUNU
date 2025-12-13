#!/usr/bin/env python3
# Copyright (c) 2025 oatsu
"""
UST のビブラート情報を f0 値に反映する。
ENUNU / SimpleEnunu の拡張機能のうち acoustic_editor で使用することを想定。

## 方針
ノートごとに計算したいが、f0 は音声全体のものなのでフィードバックするf0も全体で扱うほうが楽。
ノートごとにmsで計算すると誤差が蓄積する可能性があるので、tick で計算したほうが良さそう？

## もとのビブラートの書式

### 例
VBR=65,180,35,20,20,0,0

### 詳細(8項目)
- 長さ[%]
- 周期[ms]
- 深さ[cent]
- 入(フェードイン)[%]
- 出(フェードアウト)[%]
- 位相[%]
- 高さ[%]
- 未使用[-]

## 位置計算に必要なもの
- ノート長 [ms]
- ビブラートの開始時刻[ms]
- ビブラートの終了時刻[ms]

## 形状計算に必要なもの
- ビブラートの深さ[cent]
- ビブラートの周期[ms]
- フェードイン[ms]
- フェードアウト[ms]

"""

import math
from argparse import ArgumentParser
from os.path import dirname, join

import utaupy  # utaupy>=1.21.0 is required
from utaupy.ust import Ust

MODE_SWITCH_KEY = '$EnunuVibratoApplier'


def get_vibrato_start_times(ust: Ust):
    """
    USTを読み取ってビブラートの開始時刻のリストを返す。
    """
    t_total_ms = 0  # [ms]
    l = []
    for note in ust.notes:
        note_length_ms = note.length_ms
        t_total_ms += note_length_ms
        # ビブラートが設定されていないノートはスキップ
        if note.vibrato is None:
            continue
        # ビブラートが設定されているノートの処理
        vibrato_duration_ms = note.vibrato[0] / 100 * note_length_ms
        # ビブラートの開始時刻を計算
        vibrato_start_time = round(t_total_ms - vibrato_duration_ms)
        # ビブラートの開始時刻をリストに追加
        l.append(vibrato_start_time)
    # ビブラートの開始時刻のリストを返す
    return l


def get_vibrato_shapes(ust: Ust):
    """
    USTを読み取ってビブラートの形状を計算する。
    """
    vibrato_shapes = []
    for note in ust.notes:
        if note.vibrato is None:
            continue
        # 長さ[ms]
        vibrato_duration = note.vibrato[0] / 100 * note.length_ms
        # 周期[ms]
        vibrato_period = note.vibrato[1]
        # 深さ[cent]
        vibrato_depth = note.vibrato[2]
        # 位相[ms]
        vibrato_phase = note.vibrato[5] / 100 * vibrato_period
        # フェードイン[ms]
        vibrato_fade_in = note.vibrato[3] / 100 * vibrato_duration
        # フェードアウト[ms]
        vibrato_fade_out = note.vibrato[4] / 100 * vibrato_duration

        # ビブラートの形状を計算
        shape = []
        # 1ms ごとに形状を計算する
        for t in range(int(vibrato_duration)):
            # 位相を考慮した正弦波の計算
            phase_adjusted_time = (t + vibrato_phase) % vibrato_period
            vibrato_value = vibrato_depth * \
                math.sin((2 * math.pi) * (phase_adjusted_time / vibrato_period))
            # フェードインの処理
            if t <= vibrato_fade_in:
                vibrato_value *= t / vibrato_fade_in
            # フェードアウトの処理
            elif t >= vibrato_duration - vibrato_fade_out:
                vibrato_value *= (vibrato_duration - t) / vibrato_fade_out
            # 登録
            shape.append(vibrato_value)
        # ビブラートの形状をリストに追加
        vibrato_shapes.append(shape)

    # ビブラートの形状のリストを返す[cent]
    return vibrato_shapes


def get_flat_baseline(ust: Ust):
    """
    USTを読み取って、ビブラートのないノートのベースラインを作成する。
    要素数 = UST全体の長さ[ms] になっている 0cent のリストを返す。
    """
    total_length_ms = math.ceil(sum(note.length_ms for note in ust.notes))
    return [0] * total_length_ms  # ベースラインは全て0centで初期化


def hz_to_cent(f0_list):
    """f0のリストを受け取り、centに変換する。
    f0が0の場合は1に置き換える。
    """
    return [math.log2(max(f0, 1)) * 1200 for f0 in f0_list]  # 1オクターブ = 1200cent


def cent_to_hz(cent_list):
    """centのリストを受け取り、f0に変換する。
    計算結果が1以下の場合は0に置き換える。
    """
    # POWER!!
    f0_list = [2 ** (cent / 1200) for cent in cent_list]
    # 1以下の値は0に置き換える
    f0_list = [x if x > 1 else 0 for x in f0_list]
    return f0_list


def load_f0_file(path_f0):
    """f0のファイルを読み取り、f0のリストを返す。
    ファイルは1行に1つのf0値が書かれていると仮定する。
    """
    with open(path_f0, 'r', encoding='utf-8') as f:
        f0_list = list(map(float, f.read().splitlines()))
    return f0_list


def switch_mode(ust) -> str:
    """どのタイミングで起動されたかを、USTから調べて動作モードを切り替える。
    """
    if MODE_SWITCH_KEY in ust.setting:
        return 'acoustic_editor'
    return 'ust_editor'


def calc_and_export_vibrato_shapes(path_ust: str, path_delta_f0_cent_out: str, f0_time_unit_ms: int = 5):
    """
    USTからビブラートの形状を計算し、Δf0[cent]のファイルに出力する。
    Δf0のファイルが出力済みであることを示すため、
    USTの[#SETTING]に $EnunuVibratoApplier を追加する。
    """
    # USTファイルを読み込む
    ust = utaupy.ust.load(path_ust)
    # ベースラインを取得
    vibrato_heights = get_flat_baseline(ust)
    # ビブラートの開始時刻を取得
    vibrato_start_times = get_vibrato_start_times(ust)
    # ビブラートの形状を取得
    vibrato_shapes = get_vibrato_shapes(ust)

    # ビブラートの個数が一致することを確認する
    print(f'ビブラート形状のリストの要素数: {len(vibrato_shapes)}')
    print(f'ビブラート開始時刻のリストの要素数: {len(vibrato_start_times)}')
    assert len(vibrato_start_times) == len(vibrato_shapes), \
        f'ビブラート開始時刻のリスト({len(vibrato_start_times)}) と ビブラート形状のリスト({len(vibrato_shapes)}) の要素数が一致しません。'

    # ベースラインにビブラートの形状を加算する
    for t, shape in zip(vibrato_start_times, vibrato_shapes):
        vibrato_heights[t:t + len(shape)] = shape
    # NNSVSのf0は5ms刻みなので5つごとに間引く。
    vibrato_heights = vibrato_heights[::f0_time_unit_ms]

    # ビブラート形状のピッチ線をファイル出力
    s = '\n'.join(list(map(str, vibrato_heights)))
    with open(path_delta_f0_cent_out, 'w', encoding='utf-8') as f:
        f.write(s)
    # USTの設定に $EnunuVibratoApplier を追加して上書き
    ust.setting[MODE_SWITCH_KEY] = True
    ust.write(path_ust)

    return vibrato_heights


def apply_vibrato_to_f0(path_f0_in: str, path_f0_out: str, path_delta_f0_cent: str):
    """
    Δf0[cent]のファイルを読み取り、f0 にビブラートを適用して出力する。
    f0_time_unit_ms は f0 の時間単位で、デフォルトは 5ms。
    """
    # f0のファイルを読み取る
    f0_list = load_f0_file(path_f0_in)
    len_f0_list = len(f0_list)
    # f0をcentに変換する
    f0_cent_list = hz_to_cent(f0_list)
    # Δf0[cent]のファイルを読み取る
    delta_f0_cent_list = load_f0_file(path_delta_f0_cent)

    # 要素数が概ね合っているかチェック
    print(f'f0の要素数               : {len_f0_list}')
    print(f'Δf0 (ビブラート) の要素数: {len(delta_f0_cent_list)}')

    # # ベースラインの要素数に対してf0の要素数が少ない場合は、f0の要素数に合わせてベースラインを切り詰める。
    # if len(f0_cent_list) < len(delta_f0_cent_list):
    #     delta_f0_cent_list = delta_f0_cent_list[:len(f0_cent_list)]

    # f0 にビブラートを加算する。ただし、f0 = 0Hz (f0_cent=0) の時は無声部分なのでビブラートを無視する。
    f0_cent_list = [
        f0_cent + delta if f0_cent > 0 else f0_cent
        for f0_cent, delta in zip(f0_cent_list, delta_f0_cent_list)
    ]

    # f0 を cent から Hz に戻す
    f0_list = cent_to_hz(f0_cent_list)

    # f0ファイルを上書き保存
    s = '\n'.join(list(map(str, f0_list)))
    with open(path_f0_out, 'w', encoding='utf-8') as f:
        f.write(s)

    # Δf0 のうち、使用済みの要素を削除して上書き保存する。
    delta_f0_cent_list = delta_f0_cent_list[len_f0_list:-1]
    s = '\n'.join(list(map(str, delta_f0_cent_list)))
    with open(path_delta_f0_cent, 'w', encoding='utf-8') as f:
        f.write(s)
    return f0_cent_list


def main(path_f0_in: str, path_f0_out: str, path_ust: str):
    """
    全体時の処理をやる
    """
    # 一時ファイルの置き場を指定
    path_delta_f0_cent = join(dirname(__file__), 'temp_delta_f0_cent.csv')
    # モード分岐する
    mode = switch_mode(utaupy.ust.load(path_ust))

    # 分岐処理する
    result = []
    if mode == 'ust_editor':
        # USTのビブラート形状を計算して出力する
        result = calc_and_export_vibrato_shapes(path_ust, path_delta_f0_cent)
    elif mode == 'acoustic_editor':
        # f0 と Δf0_cent を読み取ってf0ファイルを加工する
        result = apply_vibrato_to_f0(
            path_f0_in, path_f0_out, path_delta_f0_cent)
    return result


def test():
    """テスト用の関数。input関数でUSTファイルを指定して読み込み、ビブラートの形状を計算して表示する。
    """
    # f0のCSVファイルのパスを指定して読み込む
    f0_list = load_f0_file(input('f0のCSVファイルのパス: ').strip())
    print("ビブラートの形状を計算します。USTファイルを指定してください。")
    # USTファイルを読み込む
    ust = utaupy.ust.load(input('USTファイルのパス: ').strip())
    vibrato_start_times = get_vibrato_start_times(ust)
    vibrato_shapes = get_vibrato_shapes(ust)
    baseline = get_flat_baseline(ust)
    # baselineの要素数とf0の要素数を確認する
    print(f'length of f0_list: {len(f0_list)}')
    print(f'length of baseline: {len(baseline)}')

    assert len(vibrato_start_times) == len(vibrato_shapes), \
        f'ビブラート開始時刻のリスト({len(vibrato_start_times)}) と ビブラート形状のリスト({len(vibrato_shapes)}) の要素数が一致しません。'

    # ベースラインにビブラートの形状を加算する
    for t, shape in zip(vibrato_start_times, vibrato_shapes):
        baseline[t:t + len(shape)] = shape
    # f0 は 5ms 刻みなので5つごとに間引く。
    baseline = baseline[::5]
    # baselineを matplib でプロットする
    import matplotlib.pyplot as plt
    plt.plot(baseline)
    plt.title('Vibrato Shapes')
    plt.xlabel('Time [ms]')
    plt.ylabel('Pitch [cent]')
    plt.grid()
    plt.show()


if __name__ == '__main__':
    print('vibrato_applier.py-------------------------------------')

    parser = ArgumentParser()
    parser.add_argument('--f0', help='f0の情報を持ったCSVファイルのパス')
    parser.add_argument('--ust', help='USTファイルのパス')

    # 使わない引数は無視して、必要な情報だけ取り出す。
    args, _ = parser.parse_known_args()

    # ENUNUから呼び出しているとき
    if any([args.f0 is not None or args.ust]):
        main(args.f0, args.f0, args.ust)
    # ENUNUからの呼び出しがうまくいっていないか、テスト実行の場合
    else:
        test()

    print('-------------------------------------------------------')
