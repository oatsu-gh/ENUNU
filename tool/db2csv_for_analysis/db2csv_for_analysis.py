#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
"""
ENUNU用の歌唱データベースの音素データを、分析しやすい形式のCSVファイルにまとめる。
"""
from glob import glob
from os import makedirs
from os.path import basename, dirname, join, splitext
from shutil import copy2
from typing import List

import pandas
import utaupy
from tqdm import tqdm

DEFAULT_TABLE_PATH = 'kana2phonemes_003_oto2lab.table'


def compare_mono_and_full(path_mono, path_full) -> None:
    """
    モノラベルとフルラベルの音素が一致するか点検する。
    """
    mono = utaupy.label.load(path_mono)
    full = utaupy.hts.load(path_full)
    if len(mono) != len(full):
        raise ValueError(
            f'モノラベル({basename(path_mono)})とフルラベル({basename(path_full)})の音素数が一致しません。'
        )
    if not all(ph_mono.symbol == ph_full.symbol for ph_mono, ph_full in zip(mono, full)):
        raise ValueError(
            f'モノラベル({basename(path_mono)})とフルラベル({basename(path_full)})の音素記号が一致しません。'
        )


def merge_rests_mono(path_mono_lab_in, path_mono_lab_out):
    """
    モノラベルの休符を結合する。
    休符はすべてpauにする。
    """
    label = utaupy.label.load(path_mono_lab_in)
    # 休符を全部pauにする
    for phoneme in label:
        if phoneme.symbol == 'sil':
            phoneme.symbol = 'pau'

    new_label = utaupy.label.Label()
    prev_phoneme = label[0]
    new_label.append(prev_phoneme)
    for phoneme in label[1:]:
        if prev_phoneme.symbol == 'pau' and phoneme.symbol == 'pau':
            prev_phoneme.end += phoneme.end - phoneme.start
        else:
            new_label.append(phoneme)
            prev_phoneme = phoneme
    # 発声終了時刻を再計算(わずかにずれる可能性があるため)
    new_label.reload()
    # 上書き保存
    new_label.write(path_mono_lab_out)


def merge_rests_full(path_hts_in, path_hts_out):
    """
    フルラベル用

    Songオブジェクト内で休符 (sil, pau) が連続するときに結合する。
    転調したり拍子やテンポが変わっていない場合のみ結合する。

    [sil][m][a][pau][sil][pau][k][a] -> [pau][m][a][pau][k][a] にする
    """
    song = utaupy.hts.load(path_hts_in).song
    new_song = utaupy.hts.Song()

    for phoneme in song.all_phonemes:
        if phoneme.identity == 'sil':
            phoneme.identity = 'pau'
    first_note = song[0]
    new_song.append(first_note)

    prev_note = first_note
    for note in song[1:]:
        # 転調したり拍子やテンポが変わっていない場合のみ実行
        if all((note.is_rest(),
                prev_note.is_rest(),
                note.beat == prev_note.beat,
                note.tempo == prev_note.tempo,
                note.key == prev_note.key,
                note.length != 'xx',
                prev_note.length != 'xx')):
            # 直前のノート(休符)の長さを延長する
            prev_note.length = int(prev_note.length) + int(note.length)
        # 拍子が変わっていたり、音符だった場合は普通に追加
        else:
            new_song.append(note)
            prev_note = note
    # データを補完
    new_song.autofill()
    new_song.write(path_hts_out, strict_sinsy_style=False)


def mono2csv(path_mono_lab, path_csv):
    """
    モノラベルをcsvに変換して保存する。
    """
    with open(path_mono_lab, 'r', encoding='utf-8') as f:
        s = f.read()
    # 区切り文字をコンマにする
    s = s.replace(' ', ',')
    # カラム名の行を追加
    s = 'start(align), end(align), phoneme(align)\n' + s
    # 確実に改行で終わるようにする
    s = s.strip('\n') + '\n'
    # csvファイル出力
    with open(path_csv, 'w', encoding='utf-8') as f:
        f.write(s)


def unify_csv_files(mono_csv_files: List[str], full_csv_files: List[str], path_csv_out):
    """
    複数のCSVファイルを1ファイルに統合する。
    """
    mono_csv_files = sorted(mono_csv_files)
    full_csv_files = sorted(full_csv_files)
    lines_concat: List[str] = []

    header = 'songname'
    with open(mono_csv_files[0], 'r', encoding='utf-8') as f_mono:
        header += ',' + f_mono.read().splitlines()[0]
    with open(full_csv_files[0], 'r', encoding='utf-8') as f_full:
        header += ',' + f_full.read().splitlines()[0]
    lines_concat.append(header)

    for path_mono_csv, path_full_csv in zip(tqdm(mono_csv_files), full_csv_files):
        songname = splitext(basename(path_mono_csv))[0]
        # CSVを読み取る
        with open(path_mono_csv, 'r', encoding='utf-8') as f:
            lines_mono = f.read().splitlines()[1:]
        with open(path_full_csv, 'r', encoding='utf-8') as f:
            lines_full = f.read().splitlines()[1:]
        # 音素数が一致するかチェック
        if len(lines_mono) != len(lines_full):
            raise ValueError(
                f'モノラベルとフルラベルの音素数が一致しません。({songname})'
            )
        lines_concat += [
            f'{songname},{line_mono},{line_full}' for line_mono, line_full in zip(lines_mono, lines_full)
        ]

    s = '\n'.join(lines_concat).replace('xx', '')
    with open(path_csv_out, 'w', encoding='utf-8') as f:
        f.write(s)


def main():
    db_root = input('db_root: ').strip('"')
    ust_files = glob(join(db_root, '**', '*.ust'), recursive=True)
    lab_files = glob(join(db_root, '**', '*.lab'), recursive=True)
    path_table = DEFAULT_TABLE_PATH

    temp_dir = join(dirname(__file__), 'temp')
    path_result_csv = join(dirname(__file__), 'result.csv')

    makedirs(temp_dir, exist_ok=True)

    # LABファイルをCSVファイルにする
    mono_csv_files = []
    for path_lab in tqdm(lab_files):
        songname = splitext(basename(path_lab))[0]
        path_mono_lab = join(temp_dir, f'{songname}_mono_align.lab')
        path_mono_csv = join(temp_dir, f'{songname}_mono_align.csv')
        # 一時フォルダにLABファイルを複製
        copy2(path_lab, path_mono_lab)
        merge_rests_mono(path_mono_lab, path_mono_lab)
        # CSVファイルに変換
        mono2csv(path_mono_lab, path_mono_csv)
        # CSVファイル一覧に追加
        mono_csv_files.append(path_mono_csv)

    # USTファイルをCSVファイルにする
    full_csv_files = []
    for path_ust in tqdm(ust_files):
        songname = splitext(basename(path_ust))[0]
        path_full_lab = join(temp_dir, f'{songname}_full_score.lab')
        path_full_csv = join(temp_dir, f'{songname}_full_score.csv')
        utaupy.utils.ust2hts(path_ust, path_full_lab, path_table, strict_sinsy_style=False)
        merge_rests_full(path_full_lab, path_full_lab)
        utaupy.utils.hts2csv(path_full_lab, path_full_csv)
        # CSVファイル一覧に追加
        full_csv_files.append(path_full_csv)

    unify_csv_files(mono_csv_files, full_csv_files, path_result_csv)
    df = pandas.read_csv(path_result_csv)
    df = df.dropna(how='all', axis=1)
    print(df)
    df.to_csv(path_result_csv)


if __name__ == '__main__':
    main()
