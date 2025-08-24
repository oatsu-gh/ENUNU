#!/usr/bin/env python3
# Copyright (c) 2022 oatsu
"""
ENUNUで外部ツールを呼び出すときに必要な関数とか
"""

import logging
import subprocess
from contextlib import contextmanager
from os import getcwd
from os.path import abspath, basename, dirname, exists, isfile, splitext
from sys import executable
from typing import Union

import utaupy


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


def run_an_extension(path=None, **kwargs):
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


def merge_mono_changes_to_full(path_mono_lab, path_full_lab):
    """モノラベルの音素記号でフルラベルの音素記号を上書きする。
    フルラベル読み取りと保存の処理が遅いから出来たらやりたくない。
    """
    # モノラベルを読み取る
    mono_label = utaupy.label.load(path_mono_lab)
    # フルラベルを読み取る
    full_label = utaupy.hts.load(path_full_lab)
    # 音素を上書きする
    for ph_mono, ph_full in zip(mono_label, full_label):
        ph_full.start = ph_mono.start
        ph_full.end = ph_mono.end
        ph_full.phoneme.identity = ph_mono.symbol
    # フルラベルを上書き保存する
    full_label.write(path_full_lab)


def merge_full_changes_to_mono(path_full_lab, path_mono_lab):
    """フルラベルの音素記号でモノラベルの音素記号を上書きする。
    こっちもフルラベル読み取りと保存の処理が遅いから出来たらやりたくない。
    """
    # フルラベルを読み取る
    full_label = utaupy.hts.load(path_full_lab)
    # モノラベルを上書き保存する
    full_label.as_mono().write(path_full_lab)


@contextmanager
def merge_label_changes(path_full_label: str, path_mono_label: str) -> str:
    """
    モノラベルファイルとフルラベルファイルに変化があるかを監視し、
    変化があった場合は処理結果を適当にマージする
    """
    # 引数の順番を間違っていないかチェック
    if 'full' not in path_full_label:
        logging.warning(
            f'path_full_label assigned item ({path_full_label}) does not seem HTS Full Context Label file.')
    if 'mono' not in path_mono_label:
        logging.warning(
            f'path_full_label assigned item ({path_mono_label}) does not seem mono Label file.')

    full_label_was_changed = False
    mono_label_was_changed = False

    # 拡張機能実行前のラベルの内容を保持する
    try:
        with open(path_full_label, encoding='utf-8') as f:
            str_full_old = f.read().strip()
        with open(path_mono_label, encoding='utf-8') as f:
            str_mono_old = f.read().strip()
    # 拡張機能実行後のラベルの内容を確認して変更内容を転写する。
    finally:
        with open(path_full_label, encoding='utf-8') as f:
            str_full_new = f.read().strip()
        with open(path_mono_label, encoding='utf-8') as f:
            str_mono_new = f.read().strip()
        full_was_changed = str_full_new != str_full_old
        mono_was_changed = str_mono_new != str_mono_old

        # モノラベルとフルラベル両方が変わっている場合
        if (full_was_changed, mono_was_changed) == (True, True):
            logging.warning(
                'Both mono-label and full-label were updated. Cannot merge the updated.')
        # フルラベルだけが変わっている場合
        if (full_was_changed, mono_was_changed) == (True, False):
            merge_full_changes_to_mono(path_full_label, path_mono_label)
            logging.info(
                'Mono-label was updated. Apply the updates on full-label.')
        # モノラベルだけが変わっている場合
        if (full_was_changed, mono_was_changed) == (False, True):
            merge_mono_changes_to_full(path_mono_label, path_full_label)
            logging.info(
                'Full-label was updated. Apply the updates on mono-label.')
        # どちらも変わっていない場合
        if (full_was_changed, mono_was_changed) == (False, False):
            logging.warning(
                'Neither full-label nor mono-label were updated. Please check if the extention does work.')
