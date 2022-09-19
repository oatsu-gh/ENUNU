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
import sys
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

# ENUNUのフォルダ直下にあるenulibフォルダをimportできるようにする
sys.path.append(dirname(__file__))
warnings.simplefilter('ignore')
try:
    import enulib
except ModuleNotFoundError:
    print('----------------------------------------------------------')
    print('初回起動ですね。')
    print('PC環境に合わせてPyTorchを自動インストールします。')
    print('インストール完了までしばらくお待ちください。')
    print('----------------------------------------------------------')
    from install_torch import pip_install_torch
    pip_install_torch(join('.', 'python-3.8.10-embed-amd64', 'python.exe'))
    print('----------------------------------------------------------')
    print('インストール成功しました。歌声合成を始めます。')
    print('----------------------------------------------------------\n')
    import enulib


def get_standard_function_config(config, key) -> Union[None, str]:
    if 'extensions' not in config:
        return 'built-in'
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


def main_as_plugin(path_plugin: str, path_wav: Union[str, None]) -> str:
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

    # wav出力パスが指定されていない(プラグインとして実行している)場合
    if path_wav is None:
        # 入出力パスを設定する
        if path_ust is not None:
            songname = splitext(basename(path_ust))[0]
            out_dir = dirname(path_ust)
            temp_dir = join(out_dir, f'{songname}_enutemp')
            path_wav = abspath(join(out_dir, f'{songname}__{str_now}.wav'))
        # WAV出力パス指定なしかつUST未保存の場合
        else:
            print('USTが保存されていないので一時フォルダにWAV出力します。')
            songname = f'temp__{str_now}'
            out_dir = mkdtemp(prefix='enunu-')
            temp_dir = join(out_dir, f'{songname}_enutemp')
            path_wav = abspath(join(out_dir, f'{songname}__{str_now}.wav'))
    # WAV出力パスが指定されている場合
    else:
        songname = splitext(basename(path_wav))[0]
        out_dir = dirname(path_wav)
        temp_dir = join(out_dir, f'{songname}_enutemp')
        path_wav = abspath(path_wav)

    # 一時出力フォルダがなければつくる
    makedirs(temp_dir, exist_ok=True)
    # 各種出力ファイルのパスを設定
    # path_plugin = path_plugin
    path_temp_ust = abspath(join(temp_dir, 'temp.ust'))
    path_temp_table = abspath(join(temp_dir, 'temp.table'))
    path_full_score = abspath(join(temp_dir, 'score.full'))
    path_mono_score = abspath(join(temp_dir, 'score.lab'))
    path_full_timing = abspath(join(temp_dir, 'timing.full'))
    path_mono_timing = abspath(join(temp_dir, 'timing.lab'))
    path_acoustic = abspath(join(temp_dir, 'acoustic.csv'))
    path_f0 = abspath(join(temp_dir, 'f0.csv'))
    path_spectrogram = abspath(join(temp_dir, 'spectrogram.csv'))
    path_aperiodicity = abspath(join(temp_dir, 'aperiodicity.csv'))

    # USTを一時フォルダに複製
    print(f'{datetime.now()} : copying UST')
    copy(path_plugin, path_temp_ust)
    print(f'{datetime.now()} : copying Table')
    copy(config.table_path, path_temp_table)

    # USTを事前加工------------------------------------------------------------------
    extension_list = get_extension_path_list(config, 'ust_editor')
    if extension_list is not None:
        for path_extension in extension_list:
            print(f'{datetime.now()} : editing UST with {path_extension}')
            enulib.extensions.run_extension(
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
        enulib.utauplugin2score.utauplugin2score(
            path_temp_ust,
            path_temp_table,
            path_full_score,
            strict_sinsy_style=False
        )
        # full_score から mono_score を生成
        enulib.common.full2mono(path_full_score, path_mono_score)
    # 外部ソフトでUST→LAB変換をする場合
    else:
        print(
            f'{datetime.now()} : converting UST to score with built-in function{converter}')
        enulib.extensions.run_extension(
            converter,
            ust=path_temp_ust,
            table=path_temp_table,
            full_score=path_full_score,
            mono_score=path_mono_score
        )

    # フルラベル(score)を加工-------------------------------------------------------
    extension_list = get_extension_path_list(config, 'score_editor')

    # フルラベル生成を行う場合
    if extension_list is not None:
        for path_extension in extension_list:
            print(f'{datetime.now()} : editing score with {path_extension}')
            # 変更前のモノラベルを読んでおく
            with open(path_mono_score, encoding='utf-8') as f:
                str_mono_old = f.read()
            # 外部ソフトを実行
            enulib.extensions.run_extension(
                path_extension,
                ust=path_temp_ust,
                table=path_temp_table,
                full_score=path_full_score,
                mono_score=path_mono_score
            )
            # 変更後のモノラベルを読む
            with open(path_mono_score, encoding='utf-8') as f:
                str_mono_new = f.read()

            # モノラベルの時刻が変わっていたらフルラベルに転写して、
            # そうでなければフルラベルの時刻をモノラベルに転写する。
            # NOTE: 歌詞が変更されていると思って処理する。
            # モノラベルが更新されている場合
            if enulib.extensions.str_has_been_changed(str_mono_old, str_mono_new):
                # モノラベルの時刻をフルラベルに転写する。
                enulib.extensions.merge_mono_time_change_to_full(
                    path_mono_score,
                    path_full_score
                )
                # モノラベルの音素記号をフルラベルに転写する。
                enulib.extensions.merge_mono_contexts_change_to_full(
                    path_mono_score,
                    path_full_score
                )
            # フルラベルに更新があった場合、フルラベルの時刻をモノラベルに転写する。
            else:
                enulib.extensions.merge_full_time_change_to_mono(
                    path_full_score,
                    path_mono_score
                )

    # フルラベル(timing) を生成 score.full -> timing.full-----------------
    calculator = get_standard_function_config(config, 'timing_calculator')
    # duration計算をしない場合
    if calculator is None:
        print(f'{datetime.now()} : skipped timing calculation')
    # ENUNUの組み込み機能で計算する場合
    elif calculator == 'built-in':
        print(f'{datetime.now()} : calculating timing with built-in function')
        enulib.timing.score2timing(
            config,
            path_full_score,
            path_full_timing
        )
        # フルラベルからモノラベルを生成
        enulib.common.full2mono(path_full_timing, path_mono_timing)
    # 外部ソフトで計算する場合
    else:
        print(f'{datetime.now()} : calculating timing with {calculator}')
        enulib.extensions.run_extension(
            calculator,
            ust=path_temp_ust,
            table=path_temp_table,
            full_score=path_full_score,
            mono_score=path_mono_score,
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
            with open(path_mono_timing, encoding='utf-8') as f:
                str_mono_old = f.read()
            enulib.extensions.run_extension(
                path_extension,
                ust=path_temp_ust,
                table=path_temp_table,
                full_score=path_full_score,
                mono_score=path_mono_score,
                full_timing=path_full_timing,
                mono_timing=path_mono_timing
            )
            # 変更後のモノラベルを読む
            with open(path_mono_timing, encoding='utf-8') as f:
                str_mono_new = f.read()
            # モノラベルの時刻が変わっていたらフルラベルに転写して、
            # そうでなければフルラベルの時刻をモノラベルに転写する。
            # NOTE: 歌詞は編集していないという前提で処理する。
            if enulib.extensions.str_has_been_changed(str_mono_old, str_mono_new):
                enulib.extensions.merge_mono_time_change_to_full(
                    path_mono_timing, path_full_timing)
            else:
                enulib.extensions.merge_full_time_change_to_mono(
                    path_full_timing, path_mono_timing)

    # 音響パラメータを推定 timing.full -> acoustic---------------------------
    calculator = get_standard_function_config(config, 'acoustic_calculator')
    # 計算をしない場合
    if calculator is None:
        print(f'{datetime.now()} : skipped acoustic calculation')
    elif calculator == 'built-in':
        print(
            f'{datetime.now()} : calculating acoustic with built-in function')
        # timing.full から acoustic.csv を作る。
        enulib.acoustic.timing2acoustic(
            config, path_full_timing, path_acoustic)
        # acoustic のファイルから f0, spectrogram, aperiodicity のファイルを出力
        enulib.world.acoustic2world(
            config,
            path_full_timing,
            path_acoustic,
            path_f0,
            path_spectrogram,
            path_aperiodicity
        )
    else:
        print(
            f'{datetime.now()} : calculating acoustic with {calculator}')
        enulib.extensions.run_extension(
            calculator,
            ust=path_temp_ust,
            table=path_temp_table,
            full_score=path_full_score,
            mono_score=path_mono_score,
            full_timing=path_full_timing,
            mono_timing=path_mono_timing,
            acoustic=path_acoustic,
            f0=path_f0,
            spectrogram=path_spectrogram,
            aperiodicity=path_aperiodicity
        )

    # 音響パラメータを加工: acoustic.csv -> acoustic.csv -------------------------
    extension_list = get_extension_path_list(config, 'acoustic_editor')
    if extension_list is not None:
        for path_extension in extension_list:
            print(f'{datetime.now()} : editing acoustic with {path_extension}')
            enulib.extensions.run_extension(
                path_extension,
                ust=path_temp_ust,
                table=path_temp_table,
                full_score=path_full_score,
                mono_score=path_mono_score,
                full_timing=path_full_timing,
                mono_timing=path_mono_timing,
                acoustic=path_acoustic,
                f0=path_f0,
                spectrogram=path_spectrogram,
                aperiodicity=path_aperiodicity
            )

    # WORLDを使って音声ファイルを生成: acoustic.csv -> <songname>.wav--------------
    synthesizer = get_standard_function_config(config, 'wav_synthesizer')

    # ここでは合成をしない場合
    if synthesizer is None:
        print(f'{datetime.now()} : skipped synthesizing WAV')

    # 組み込まれたWORLDで合成する場合
    elif synthesizer == 'built-in':
        print(f'{datetime.now()} : synthesizing WAV with built-in function')
        # WAVファイル出力
        enulib.world.world2wav(
            config,
            path_f0,
            path_spectrogram,
            path_aperiodicity,
            path_wav
        )

    # 別途指定するソフトで合成する場合
    else:
        print(f'{datetime.now()} : synthesizing WAV with {synthesizer}')
        enulib.extensions.run_extension(
            synthesizer,
            ust=path_temp_ust,
            table=path_temp_table,
            full_score=path_full_score,
            mono_score=path_mono_score,
            full_timing=path_full_timing,
            mono_timing=path_mono_timing,
            acoustic=path_acoustic,
            f0=path_f0,
            spectrogram=path_spectrogram,
            aperiodicity=path_aperiodicity
        )

    # 音声ファイルを加工: <songname>.wav -> <songname>.wav
    extension_list = get_extension_path_list(config, 'wav_editor')
    if extension_list is not None:
        for path_extension in extension_list:
            print(f'{datetime.now()} : editing WAV with {path_extension}')
            enulib.extensions.run_extension(
                path_extension,
                ust=path_temp_ust,
                table=path_temp_table,
                full_score=path_full_score,
                mono_score=path_mono_score,
                full_timing=path_full_timing,
                mono_timing=path_mono_timing,
                acoustic=path_acoustic,
                f0=path_f0,
                spectrogram=path_spectrogram,
                aperiodicity=path_aperiodicity
            )

    # print(f'{datetime.now()} : converting LAB to JSON')
    # hts2json(path_full_score, path_json)

    # 音声を再生する。
    if exists(path_wav):
        startfile(path_wav)

    return path_wav


def main(path_plugin: str, path_wav_out: Union[str, None]):
    """
    入力ファイルによって処理を分岐する。
    """
    # logging.basicConfig(level=logging.INFO)
    if path_plugin.endswith('.tmp'):
        main_as_plugin(path_plugin, path_wav_out)
    else:
        raise ValueError('Input file must be TMP(plugin).')


if __name__ == '__main__':
    print('_____ξ ・ヮ・)ξ < ENUNU v0.5.2 ________')
    print(f'argv: {argv}')
    if len(argv) == 3:
        main(argv[1], argv[2])
    elif len(argv) == 2:
        main(argv[1], None)
    elif len(argv) == 1:
        main(input('Input file path of TMP(plugin)\n>>> ').strip('"'), None)
    else:
        raise Exception('引数が多すぎます。/ Too many arguments.')
