#!/usr/bin/env python3
# Copyright (c) 2021 oatsu
"""
フルラベル中の休符を結合して上書きする。
いったんSongオブジェクトを経由するので、
utaupyの仕様に沿ったフルラベルになってしまうことに注意。
"""
from copy import copy
from glob import glob
from os.path import basename
from sys import argv

import utaupy as up
import yaml
from tqdm import tqdm
from utaupy.hts import Song
from utaupy.label import Label


def merge_rests_full(song: Song) -> Song:
    """
    フルラベル用

    Songオブジェクト内で休符 (sil, pau) が連続するときに結合する。
    転調したり拍子やテンポが変わっていない場合のみ結合する。

    [sil][m][a][pau][sil][pau][k][a] -> [pau][m][a][pau][k][a] にする
    """
    new_song = Song()

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
        for note in song.all_notes:
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
                label[i - 1].end = phoneme.end
            else:
                new_data.append(phoneme)
        label.data = new_data


def main(path_config_yaml):
    """
    musicxmlから生成されたラベルと、DBに同梱されていたラベルの、休符をすべて結合する。
    ついでにround版も作る。
    """
    with open(path_config_yaml, 'r') as fy:
        config = yaml.load(fy, Loader=yaml.FullLoader)
    out_dir = config['out_dir']

    # フルラベルを処理する。
    lab_files = glob(f'{out_dir}/full_score/*.lab')
    print('Merging rests of full-LAB files')
    for path_full in tqdm(lab_files):
        song = up.hts.load(path_full).song
        # 休符を結合してもとのフルラベルを上書き
        song = merge_rests_full(song)
        # ブレスを除去
        # remove_breath_full(song)
        # Sinsyの時間計算が気に入らないので、時間を計算しなおす
        # 楽譜と合わない発声時刻を知らない楽譜と合わない発声時刻が気に入らないよ
        song.reset_time()
        song.write(path_full, strict_sinsy_style=False, as_mono=False)


if __name__ == '__main__':
    if len(argv) == 1:
        main('config.yaml')
    else:
        main(argv[1].strip('"'))
