#! /usr/bin/env python3
# coding: utf-8
# Copyright (c) 2020 oatsu
"""
1. UTAUプラグインのテキストファイルを読み取る。
  - 音源のフォルダを特定する。
  - プロジェクトもしくはUSTファイルのパスを特定する。
2. LABファイルを(一時的に)生成する
  - キャッシュフォルダでいいと思う。
3. LABファイル→WAVファイル
"""
import warnings
from datetime import datetime
from os import chdir, makedirs, startfile
from os.path import abspath, basename, dirname, exists, join, splitext
from shutil import copy
from sys import argv
from tempfile import mkdtemp
from typing import Iterable, List, Union

import colored_traceback.always  # pylint: disable=unused-import
import utaupy
from omegaconf import DictConfig, OmegaConf

from enulib.acoustic import timing2acoustic
from enulib.common import full2mono
from enulib.duration import score2duration
from enulib.extensions import (merge_full_contexts_change_to_mono,
                               merge_full_time_change_to_mono,
                               merge_mono_contexts_change_to_full,
                               merge_mono_time_change_to_full, run_extension,
                               str_has_been_changed)
from enulib.timelag import score2timelag
from enulib.timing import generate_timing_label
from enulib.utauplugin2score import utauplugin2score
from enulib.world import acoustic2wav

warnings.simplefilter('ignore')

# try:
#     from hts2wav import hts2wav
# except ModuleNotFoundError:
#     print('----------------------------------------------------------')
#     print('初回起動ですね。')
#     print('PC環境に合わせてPyTorchを自動インストールします。')
#     print('インストール完了までしばらくお待ちください。')
#     print('----------------------------------------------------------')
#     from install_torch import pip_install_torch
#     pip_install_torch(join('.', 'python-3.8.10-embed-amd64', 'python.exe'))
#     print('----------------------------------------------------------')
#     print('インストール成功しました。歌声合成を始めます。')
#     print('----------------------------------------------------------\n')
#     from hts2wav import hts2wav  # pylint: disable=ungrouped-imports


def get_standard_function_config(config, key) -> Union[None, str]:
    if 'extensions' not in config:
        return 'built-in'
    else:
        return config.extensions.get(key)


def get_extension_path_list(config, key) -> Union[None, List[str]]:
    """拡張機能のパスのリストを取得する。
    パスが複数指定されていてもひとつしか指定されていなくてもループできるようにする。
    """
    # 拡張機能の項目がなければNoneを返す。
    if 'extensions' not in config:
        return None
    # 目的の拡張機能のパスがあれば取得する。
    config_extensions_something = config.extensions.get(key)
    if config_extensions_something is None:
        return None
    if config_extensions_something == "":
        return None
    if isinstance(config_extensions_something, str):
        return [config_extensions_something]
    if isinstance(config_extensions_something, Iterable):
        return list(config_extensions_something)
    # 空文字列でもNULLでもリストでも文字列でもない場合
    raise TypeError(
        f'Extension path must be null or strings or list, not {type(config_extensions_something)} for {config_extensions_something}'
    )


def get_project_path(path_utauplugin):
    """
    キャッシュパスとプロジェクトパスを取得する。
    """
    plugin = utaupy.utauplugin.load(path_utauplugin)
    setting = plugin.setting
    # ustのパス
    path_ust = setting.get('Project')
    # 音源フォルダ
    voice_dir = setting['VoiceDir']
    # 音声キャッシュのフォルダ(LABとJSONを設置する)
    cache_dir = setting['CacheDir']

    return path_ust, voice_dir, cache_dir


def main_as_plugin(path_plugin: str) -> str:
    """
    UtauPluginオブジェクトから音声ファイルを作る
    """
    # UTAUの一時ファイルに書いてある設定を読み取る
    print(f'{datetime.now()} : reading settings in TMP')
    path_ust, voice_dir, _ = get_project_path(path_plugin)
    path_enuconfig = join(voice_dir, 'enuconfig.yaml')

    # configファイルがあるか調べて、なければ例外処理
    if not exists(path_enuconfig):
        raise Exception(
            '音源フォルダに enuconfig.yaml が見つかりません。'
            'UTAU音源選択でENUNU用モデルを指定してください。'
        )
    # カレントディレクトリを音源フォルダに変更する
    chdir(voice_dir)

    # configファイルを読み取る
    print(f'{datetime.now()} : reading enuconfig')
    config = DictConfig(OmegaConf.load(path_enuconfig))

    # 日付時刻を取得
    str_now = datetime.now().strftime('%Y%m%d_%H%M%S')
    # 入出力パスを設定する
    if path_ust is not None:
        songname = splitext(basename(path_ust))[0]
        out_dir = dirname(path_ust)
        temp_dir = join(out_dir, f'{songname}_enutemp')
    # USTが未保存の場合
    else:
        print('USTが保存されていないので一時フォルダにWAV出力します。')
        songname = f'temp__{str_now}'
        temp_dir = mkdtemp(prefix='enunu-')
        out_dir = temp_dir

    # 一時出力フォルダがなければつくる
    makedirs(temp_dir, exist_ok=True)
    # 各種出力ファイルのパスを設定
    path_temp_ust = abspath(join(temp_dir, 'temp.ust'))
    path_full_score = abspath(join(temp_dir, 'score.full'))
    path_mono_score = abspath(join(temp_dir, 'score.lab'))
    path_full_timelag = abspath(join(temp_dir, 'timelag.full'))
    path_mono_timelag = abspath(join(temp_dir, 'timelag.lab'))
    path_full_duration = abspath(join(temp_dir, 'duration.full'))
    path_mono_duration = abspath(join(temp_dir, 'duration.lab'))
    path_full_timing = abspath(join(temp_dir, 'timing.full'))
    path_mono_timing = abspath(join(temp_dir, 'timing.lab'))
    path_acoustic = abspath(join(temp_dir, 'acoustic.csv'))
    # path_f0 = abspath(join(temp_dir, 'world.f0'))
    # path_bap = abspath(join(temp_dir, 'world.bap'))
    # path_mgc = abspath(join(temp_dir, 'world.mgc'))
    path_wav = abspath(join(out_dir, f'{songname}__{str_now}.wav'))

    # USTを一時フォルダに複製
    print(f'{datetime.now()} : copying UST')
    copy(path_plugin, path_temp_ust)

    # USTを事前加工------------------------------------------------------------------
    extension_list = get_extension_path_list(config, 'ust_editor')
    if extension_list is not None:
        for path_extension in extension_list:
            print(f'{datetime.now()} : editing UST with {path_extension}')
            run_extension(
                path_extension,
                ust=path_temp_ust
            )

    # フルラベル(score)生成----------------------------------------------------------
    converter = get_standard_function_config(config, 'ust_converter')
    # フルラベル生成をしない場合
    if converter is None:
        pass
    # ENUNUの組み込み機能でUST→LAB変換をする場合
    elif converter == 'built-in':
        print(f'{datetime.now()} : converting UST to score with built-in function')
        utauplugin2score(
            path_temp_ust,
            config.table_path,
            path_full_score,
            path_mono_out=None,
            strict_sinsy_style=(not config.trained_for_enunu)
        )
        # full_score から mono_score を生成
        full2mono(path_full_score, path_mono_score)
    # 外部ソフトでUST→LAB変換をする場合
    else:
        print(
            f'{datetime.now()} : converting UST to score with built-in function{converter}')
        run_extension(
            converter,
            ust=path_temp_ust,
            table=config.table_path,
            full_score=path_full_score,
            mono_score=path_mono_score
        )

    # フルラベル(score)を加工-------------------------------------------------------
    extension_list = get_extension_path_list(config, 'score_editor')
    if extension_list is not None:
        for path_extension in extension_list:
            print(f'{datetime.now()} : editing score with {path_extension}')
            # 変更前のモノラベルを読んでおく
            with open(path_mono_timelag, encoding='utf-8') as f:
                str_mono_old = f.read()
            # 外部ソフトを実行
            run_extension(
                path_extension,
                ust=path_temp_ust,
                full_score=path_full_score,
                mono_score=path_mono_score
            )
            # 変更後のモノラベルを読む
            with open(path_mono_timelag, encoding='utf-8') as f:
                str_mono_new = f.read()
        # モノラベルの時刻が変わっていたらフルラベルに転写して、
            # そうでなければフルラベルの時刻をモノラベルに転写する。
            # NOTE: 歌詞が変更されていると思って処理する。
            if str_has_been_changed(str_mono_old, str_mono_new):
                merge_mono_time_change_to_full(
                    path_mono_score, path_full_score)
                merge_mono_contexts_change_to_full(
                    path_mono_score, path_full_score)
            else:
                merge_full_time_change_to_mono(
                    path_full_score, path_mono_score)
                merge_full_contexts_change_to_mono(
                    path_full_timelag, path_mono_timelag)

    # フルラベル(timelag)を生成: score.full -> timelag.full-----------------------
    calculator = get_standard_function_config(config, 'timelag_calculator')
    # timelag計算をしない場合
    if calculator is None:
        print(f'{datetime.now()} : skipped timelag calculation')
    # ENUNUの組み込み機能でtimelag計算をする場合
    elif calculator == 'built-in':
        print(f'{datetime.now()} : calculating timelag with built-in function')
        score2timelag(
            config,
            path_full_score,
            path_full_timelag
        )
        # full_timelag から mono_timelag を生成
        full2mono(path_full_timelag, path_mono_timelag)
    # 外部ソフトでtimelag計算をする場合
    else:
        print(f'{datetime.now()} : calculating timelag with {calculator}')
        run_extension(
            calculator,
            ust=path_temp_ust,
            table=config.table_path,
            full_score=path_full_score,
            mono_score=path_mono_score,
            full_timelag=path_full_timelag,
            mono_timelag=path_mono_timelag
        )

    # フルラベル(timelag)を加工: timelag.full -> timelag.full---------------------
    extension_list = get_extension_path_list(config, 'timelag_editor')
    if extension_list is not None:
        for path_extension in extension_list:
            print(f'{datetime.now()} : editing timelag with {path_extension}')
            # 変更前のモノラベルを読んでおく
            with open(path_mono_timelag, encoding='utf-8') as f:
                str_mono_old = f.read()
            # 外部ソフトを起動
            run_extension(
                path_extension,
                ust=path_temp_ust,
                full_score=path_full_score,
                mono_score=path_mono_score,
                full_timelag=path_full_timelag,
                mono_timelag=path_mono_timelag
            )
            # 変更後のモノラベルを読む
            with open(path_mono_timelag, encoding='utf-8') as f:
                str_mono_new = f.read()
            # モノラベルの時刻が変わっていたらフルラベルに転写して、
            # そうでなければフルラベルの時刻をモノラベルに転写する。
            # NOTE: 歌詞は編集していないと信じて処理する。
            if str_has_been_changed(str_mono_old, str_mono_new):
                merge_mono_time_change_to_full(
                    path_mono_timelag, path_full_timelag)
            else:
                merge_full_time_change_to_mono(
                    path_full_timelag, path_mono_timelag)

    # フルラベル(duration) を生成 score.full & timelag.full -> duration.full-----
    calculator = get_standard_function_config(config, 'duration_calculator')
    # duration計算をしない場合
    if calculator is None:
        print(f'{datetime.now()} : skipped duration calculation')
    # ENUNUの組み込み機能でduration計算をする場合
    elif calculator == 'built-in':
        print(f'{datetime.now()} : calculating duration with built-in function')
        score2duration(
            config,
            path_full_score,
            path_full_timelag,
            path_full_duration
        )
        # full_duration から mono_duration を生成
        full2mono(path_full_duration, path_mono_duration)
    # 外部ソフトで duration 計算をする場合
    else:
        print(f'{datetime.now()} : calculating duration with {calculator}')
        run_extension(
            calculator,
            ust=path_temp_ust,
            full_score=path_full_score,
            mono_score=path_mono_score,
            full_timelag=path_full_timelag,
            mono_timelag=path_mono_timelag,
            full_duration=path_full_duration,
            mono_duration=path_mono_duration
        )

    # フルラベル(duration)を加工: duration.full -> duration.full-----------------
    extension_list = get_extension_path_list(config, 'duration_editor')
    if extension_list is not None:
        for path_extension in extension_list:
            print(f'{datetime.now()} : editing duration with {path_extension}')
            # 変更前のモノラベルを読んでおく
            with open(path_mono_duration, encoding='utf-8') as f:
                str_mono_old = f.read()
            # 外部ソフトでdurationを編集する
            run_extension(
                path_extension,
                ust=path_temp_ust,
                full_score=path_full_score,
                mono_score=path_mono_score,
                full_timelag=path_full_timelag,
                mono_timelag=path_mono_timelag,
                full_duration=path_full_duration,
                mono_duration=path_mono_duration
            )
            # 変更後のモノラベルを読む
            with open(path_mono_duration, encoding='utf-8') as f:
                str_mono_new = f.read()
            # モノラベルの時刻が変わっていたらフルラベルに転写して、
            # そうでなければフルラベルの時刻をモノラベルに転写する。
            # NOTE: 歌詞は編集していないという前提で処理する。
            if str_has_been_changed(str_mono_old, str_mono_new):
                merge_mono_time_change_to_full(
                    path_mono_duration, path_full_duration)
            else:
                merge_full_time_change_to_mono(
                    path_full_duration, path_mono_duration)

    # フルラベル(timing) を生成 timelag.full & duration.full -> timing.full------
    calculator = get_standard_function_config(config, 'timing_calculator')
    # duration計算をしない場合
    if calculator is None:
        print(f'{datetime.now()} : skipped timing calculation')
    # ENUNUの組み込み機能で計算する場合
    elif calculator == 'built-in':
        print(f'{datetime.now()} : calculating timing with built-in function')
        generate_timing_label(
            path_full_score,
            path_full_timelag,
            path_full_duration,
            path_full_timing
        )
        # フルラベルからモノラベルを生成
        full2mono(path_full_timing, path_mono_timing)
    # 外部ソフトで計算する場合
    else:
        print(f'{datetime.now()} : calculating timing with {calculator}')
        run_extension(
            calculator,
            ust=path_temp_ust,
            full_score=path_full_score,
            mono_score=path_mono_score,
            full_timelag=path_full_timelag,
            mono_timelag=path_mono_timelag,
            full_duration=path_full_duration,
            mono_duration=path_mono_duration,
            full_timing=path_full_timing,
            mono_timing=path_mono_timing
        )

    # フルラベル(timing) を加工: timing.full -> timing.full----------------------
    extension_list = get_extension_path_list(config, 'timing_editor')
    if extension_list is not None:
        # 複数ツールのすべてについて処理実施する
        for path_extension in extension_list:
            print(f'{datetime.now()} : editing timing with {path_extension}')
            # 変更前のモノラベルを読んでおく
            with open(path_mono_duration, encoding='utf-8') as f:
                str_mono_old = f.read()
            run_extension(
                path_extension,
                ust=path_temp_ust,
                full_score=path_full_score,
                mono_score=path_mono_score,
                full_timelag=path_full_timelag,
                mono_timelag=path_mono_timelag,
                full_duration=path_full_duration,
                mono_duration=path_mono_duration,
                full_timing=path_full_timing,
                mono_timing=path_mono_timing
            )
            # 変更後のモノラベルを読む
            with open(path_mono_duration, encoding='utf-8') as f:
                str_mono_new = f.read()
            # モノラベルの時刻が変わっていたらフルラベルに転写して、
            # そうでなければフルラベルの時刻をモノラベルに転写する。
            # NOTE: 歌詞は編集していないという前提で処理する。
            if str_has_been_changed(str_mono_old, str_mono_new):
                merge_mono_time_change_to_full(
                    path_mono_timing, path_full_timing)
            else:
                merge_full_time_change_to_mono(
                    path_full_timing, path_mono_timing)

    # 音響パラメータを推定 timing.full -> acoustic---------------------------
    calculator = get_standard_function_config(config, 'timing_calculator')
    # 計算をしない場合
    if calculator is None:
        print(f'{datetime.now()} : skipped timing calculation')
    elif calculator == 'built-in':
        print(
            f'{datetime.now()} : calculating timing with built-in function')
        timing2acoustic(config, path_full_timing, path_acoustic)
    else:
        print(
            f'{datetime.now()} : calculating timing with {calculator}')
        run_extension(
            calculator,
            ust=path_temp_ust,
            full_score=path_full_score,
            mono_score=path_mono_score,
            full_timelag=path_full_timelag,
            mono_timelag=path_mono_timelag,
            full_duration=path_full_duration,
            mono_duration=path_mono_duration,
            full_timing=path_full_timing,
            mono_timing=path_mono_timing,
            acoustic=path_acoustic
        )

    # 音響パラメータを加工: acoustic.csv -> acoustic.csv-------------------------
    extension_list = get_extension_path_list(config, 'acoustic_editor')
    if extension_list is not None:
        for path_extension in extension_list:
            print(f'{datetime.now()} : editing acoustic with {path_extension}')
            run_extension(
                path_extension,
                ust=path_temp_ust,
                full_score=path_full_score,
                mono_score=path_mono_score,
                full_timelag=path_full_timelag,
                mono_timelag=path_mono_timelag,
                full_duration=path_full_duration,
                mono_duration=path_mono_duration,
                full_timing=path_full_timing,
                mono_timing=path_mono_timing,
                acoustic=path_acoustic
            )

    # WORLDを使って音声ファイルを生成: acoustic.csv -> <songname>.wav--------------
    synthesizer = get_standard_function_config(config, 'wav_synthesizer')
    # 計算をしない場合
    if synthesizer is None:
        print(f'{datetime.now()} : skipped synthesizing WAV')
    elif synthesizer == 'built-in':
        print(f'{datetime.now()} : synthesizing WAV with built-in function')
        acoustic2wav(
            config,
            path_full_timing,
            path_acoustic,
            path_wav
        )
    else:
        print(f'{datetime.now()} : synthesizing WAV with {synthesizer}')
        run_extension(
            synthesizer,
            ust=path_temp_ust,
            full_score=path_full_score,
            mono_score=path_mono_score,
            full_timelag=path_full_timelag,
            mono_timelag=path_mono_timelag,
            full_duration=path_full_duration,
            mono_duration=path_mono_duration,
            full_timing=path_full_timing,
            mono_timing=path_mono_timing,
            acoustic=path_acoustic
        )

    # 音声ファイルを加工: <songname>.wav -> <songname>.wav
    extension_list = get_extension_path_list(config, 'wav_editor')
    if extension_list is not None:
        for path_extension in extension_list:
            print(f'{datetime.now()} : editing WAV with {path_extension}')
            run_extension(
                path_extension,
                ust=path_temp_ust,
                full_score=path_full_score,
                mono_score=path_mono_score,
                full_timelag=path_full_timelag,
                mono_timelag=path_mono_timelag,
                full_duration=path_full_duration,
                mono_duration=path_mono_duration,
                full_timing=path_full_timing,
                mono_timing=path_mono_timing,
                wav=path_wav
            )

    # print(f'{datetime.now()} : converting LAB to JSON')
    # hts2json(path_full_score, path_json)

    # Windowsの時は音声を再生する。
    startfile(path_wav)

    return path_wav


def main(path: str):
    """
    入力ファイルによって処理を分岐する。
    """
    # logging.basicConfig(level=logging.INFO)
    if path.endswith('.tmp'):
        main_as_plugin(path)
    else:
        raise ValueError('Input file must be TMP(plugin).')


if __name__ == '__main__':
    print('_____ξ ・ヮ・)ξ < ENUNU v0.3.0 ________')
    print(f'argv: {argv}')
    if len(argv) == 3 or len(argv) == 2:
        main(argv[1])
    elif len(argv) == 1:
        main(input('Input file path of TMP(plugin)\n>>> ').strip('"'))
    else:
        raise Exception('引数が多すぎます。')
