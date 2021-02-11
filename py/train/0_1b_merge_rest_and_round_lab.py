#!/usr/bin/env python3
# Copyright (c) 2020 oatsu
"""
フルラベル中の休符を結合する。
いったんSongオブジェクトを経由するので、
utaupyの仕様に沿ったフルラベルになってしまうことに注意。

"""
from glob import glob
from os import makedirs
from os.path import basename
from sys import argv
from copy import copy

import utaupy as up
from utaupy.hts import Song
from utaupy.label import Label
import yaml
from tqdm import tqdm


def merge_rest_full(song:Song) -> Song:
    """
    フルラベル用

    Songオブジェクト内で休符 (sil, pau) が連続するときに結合する。
    転調したり拍子やテンポが変わっていない場合のみ結合する。

    [sil][m][a][pau][sil][pau][k][a] -> [pau][m][a][pau][k][a] にする
    """
    new_song = Song()

    # silだったら困るのでpauにする。
    first_note = song[0]
    if first_note.phonemes[0].identity == 'sil':
        first_note.phonemes[0].identity = 'pau'
    new_song.append(first_note)
    print(len(song), end=' ')

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
    print(len(song))

    return new_song


def merge_rests_mono(label: Label):
    """
    モノラベルの休符を結合する。
    休符はすべてpauにする。
    """
    # 休符を全部pauにする
    for phoneme in label:
        if phoneme.symbol == 'sil':
            phoneme.symbol = 'pau'

    new_label = Label()
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
    print(len(label))

    return new_label

def remove_breath_full(song: Song):
    """
    ブレス記号を削除して、前の音素(母音)を伸ばす。
    ノート内音素数とかが変わるので、時刻やノート内位置を再構築する必要がある。

    ブレス記号がある場合、
    音符が「あ」「か」「(ブレス記号)」のとき
    音節は [[a]] [[k a br]] となり、
    ノートは [[[a]]] [[[k a br]]] となっている。

    これを [[[a]]] [[[k a]]] とする。

    変更が起きたかどうかをboolで返す。
    """
    new_song_data = []
    # ループが深いので、楽譜中にブレスがあるときだけ処理を実行
    if 'br' in (ph.identity for ph in song.all_phonemes):
        # print('\nbrを除去します。')
        for note in song.all_notes :
            # ノート内の最後にbrがあるときは時間を調製してからbrを除去
            if note.phonemes[-1].identity == 'br':
                new_note = copy(note)
                new_note[-1][-2].end = copy(new_note[-1][-1].end)
                del new_note[-1][-1]
            # brが含まれないとき
            else:
                new_note = note
            # brを除去したSong用のリストにノートを追加
            new_song_data.append(new_note)
        # 音節内音素位置やノート内音節数が変わるので再補完
        song.data = new_song_data
        song.autofill()


def remove_breath_mono(label: Label):
    """
    ブレス記号を削除して、前の音素(母音)を伸ばす。
    """
    new_data = [label[0]]
    # 楽譜中にブレスがあるときだけ処理を実行する。
    if 'br' in (ph.symbol for ph in label):
        for i, phoneme in enumerate(label[1:], 1):
            if phoneme.symbol == 'br':
                label[i-1].end = phoneme.end
            else:
                new_data.append(phoneme)
        label.data = new_data



def round_full(song: Song, unit: int = 50000):
    """
    フルラベル用のSongオブジェクトの発声時刻を丸める。
    unit: 丸める基準
    """
    for phoneme in song.all_phonemes:
        phoneme.start = round(int(phoneme.start) / unit) * unit
        phoneme.end = round(int(phoneme.end) / unit) * unit


def round_mono(label: Label, unit: int = 50000):
    """
    モノラベル用のLabelオブジェクトの発声時刻を丸める。
    unit: 丸める基準
    """
    for phoneme in label:
        phoneme.start = round(int(phoneme.start) / unit) * unit
        phoneme.end = round(int(phoneme.end) / unit) * unit


def main(path_config_yaml):
    """
    musicxmlから生成されたラベルと、DBに同梱されていたラベルの、休符をすべて結合する。
    ついでにround版も作る。
    """
    with open(path_config_yaml, 'r') as fy:
        config = yaml.load(fy, Loader=yaml.FullLoader)
    out_dir = config['out_dir']

    # 処理後のラベルファイル出力用のフォルダを作る
    makedirs(f'{out_dir}/sinsy_full_round', exist_ok=True)
    makedirs(f'{out_dir}/sinsy_mono_round', exist_ok=True)
    makedirs(f'{out_dir}/mono_label_round', exist_ok=True)

    # Sinsyで出力したフルラベルを処理する。このときモノラベルのround版も生成する。
    lab_files = glob(f'{out_dir}/sinsy_full/*.lab')
    print('Merge rests and Round labels from Sinsy')
    for path_sinsy_full_in in tqdm(lab_files):
        path_sinsy_full_out = f'{out_dir}/sinsy_full_round/{basename(path_sinsy_full_in)}'
        path_sinsy_mono_out = f'{out_dir}/sinsy_mono_round/{basename(path_sinsy_full_in)}'
        song = up.hts.load(path_sinsy_full_in).song
        # 休符を結合してもとのフルラベルを上書き
        song = merge_rest_full(song)
        # ブレスを除去
        # remove_breath_full(song)
        # Sinsyの時間計算が気に入らないので、時間を計算しなおす
        # 楽譜と合わない発声時刻を知らない楽譜と合わない発声時刻が気に入らないよ
        song.reset_time()
        song.write(path_sinsy_full_in, strict_sinsy_style=False, label_type='full')
        # 丸める
        round_full(song)
        # 丸めたフルラベルを出力
        song.write(path_sinsy_full_out, strict_sinsy_style=False, label_type='full')
        # 丸めたモノラベルを出力
        song.write(path_sinsy_mono_out, strict_sinsy_style=False, label_type='mono')

    # Sinsyで出力したモノラベルを処理する。
    # NOTE: フルラベルのときに同時に処理するので不要

    # DBに同梱されていたモノラベルを処理する。
    print('Merge rests and Round labels from DB')
    lab_files = glob(f'{out_dir}/mono_label/*.lab')
    for path_mono_in in tqdm(lab_files):
        path_mono_out = f'{out_dir}/mono_label_round/{basename(path_mono_in)}'
        label = up.label.load(path_mono_in)
        # 休符を結合
        label = merge_rests_mono(label)
        # ブレスを削除して直前の音素を延長
        # remove_breath_mono(label)
        # ファイル出力
        label.write(path_mono_in)
        # 丸める
        round_mono(label)
        # 丸めたモノラベルを出力
        label.check_invalid_time()
        label.write(path_mono_out)


if __name__ == '__main__':
    print('------------------------------------------------------------------------------')
    print('[ Stage 0 ] [ Step 1b ] Merge rests and round times in label files.')
    print('------------------------------------------------------------------------------')
    main(argv[1])
