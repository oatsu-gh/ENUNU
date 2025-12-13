#!/usr/bin/env python3
# Copyright (c) 2022 oatsu
"""
ENUNUで外部ツールを呼び出すときに必要な関数とか
"""

import subprocess
from os import getcwd
from os.path import abspath, dirname, exists, isfile, splitext
from sys import executable
from typing import Union

import utaupy


def merge_mono_time_change_to_full(path_mono_lab, path_full_lab):
    """モノラベルの時刻でフルラベルの時刻を上書きする。

    外部ソフトではフルラベルを加工せずに
    モノラベルだけ加工する場合が多いだろうから。
    """
    # モノラベルを読み取る
    mono_label = utaupy.label.load(path_mono_lab)
    # フルラベルを読み取る
    full_label = utaupy.label.load(path_full_lab)
    # 時刻を上書きする
    for ph_mono, ph_full in zip(mono_label, full_label):
        ph_full.start = ph_mono.start
        ph_full.end = ph_mono.end
    # フルラベルを上書き保存する
    full_label.write(path_full_lab)


def merge_full_time_change_to_mono(path_full_lab, path_mono_lab):
    """フルラベルの時刻でモノラベルの時刻を上書きする。
    """
    # 順番入れ替えただけ
    # pylint: disable=arguments-out-of-order
    merge_mono_time_change_to_full(path_full_lab, path_mono_lab)


def merge_mono_contexts_change_to_full(path_mono_lab, path_full_lab):
    """モノラベルの音素記号でフルラベルの音素記号を上書きする。
    フルラベル読み取りと保存の処理が遅いから出来たらやりたくない。
    """
    # モノラベルを読み取る
    mono_label = utaupy.label.load(path_mono_lab)
    # フルラベルを読み取る
    full_label = utaupy.hts.load(path_full_lab)
    # 音素を上書きする
    for ph_mono, ph_full in zip(mono_label, full_label):
        ph_full.phoneme.identity = ph_mono.symbol
    # フルラベルを上書き保存する
    full_label.write(path_full_lab)


def merge_full_contexts_change_to_mono(path_full_lab, path_mono_lab):
    """フルラベルの音素記号でモノラベルの音素記号を上書きする。
    こっちもフルラベル読み取りと保存の処理が遅いから出来たらやりたくない。
    """
    # モノラベルを読み取る
    mono_label = utaupy.label.load(path_mono_lab)
    # フルラベルを読み取る
    full_label = utaupy.hts.load(path_full_lab)
    # 音素を上書きする
    for ph_mono, ph_full in zip(mono_label, full_label):
        ph_mono.symbol = ph_full.phoneme.identity
    # フルラベルを上書き保存する
    mono_label.write(path_full_lab)


def str_has_been_changed(s_old: str, s_new: str):
    """モノラベルやフルラベルが変更されているか調べる。
    """
    return s_old.strip() != s_new.strip()


def parse_extension_path(path) -> Union[str, None]:
    """拡張機能のパス中のエイリアスを置換する。

    Following aliases are available
      - '%e' (the directory enunu.py exists in)
      - '%v' (the directory voicebank and enuconfig.yaml exists in)
      - '%u' (the directory utau.exe exists in)
    """
    if path is None:
        return None
    # 各種パスを取得
    voice_dir = getcwd()
    enunu_dir = dirname(dirname(__file__))
    utau_dir = utaupy.utau.utau_root()
    # 置換
    path = path.replace(r'%e', enunu_dir)
    path = path.replace(r'%v', voice_dir)
    path = path.replace(r'%u', utau_dir)
    return path


def run_extension(path=None, **kwargs):
    """
    USTやラベルを加工する外部ソフトを呼び出す。
    """
    # path = path.strip('"')
    if path is None:
        return None
    # パスに含まれるエイリアスを展開
    path = parse_extension_path(path)
    if not exists(path):
        raise ValueError(f'指定されたファイルが見つかりません。({path})')
    if not isfile(path):
        raise ValueError(f'指定されたパスはファイルではありません。({path})')

    # 拡張機能を呼び出すときのコマンド
    args = [path]
    # 辞書をコマンド用のリストに追加する。値がNoneだったら無視する。
    # kwargs = {'mono_score': path_mono_score, 'full_score': path_full_score}
    # ↓
    # --mono_score basename(path_mono_score) --full_score basename(path_full_score)
    for key, value in kwargs.items():
        if value is None:
            continue
        args.append(f'--{key}')
        args.append(value)

    # 拡張機能がPythonスクリプトな場合に、
    # ENUNU同梱のインタープリタで実行するようにコマンドを変更する。
    if splitext(path.strip('"'))[1] == '.py':
        args.insert(0, abspath(executable))

    # 拡張機能を呼び出す。
    subprocess.run(args, cwd=dirname(path.strip('\'"')), check=True)
