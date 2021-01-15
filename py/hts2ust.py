#!/usr/bin/env python3
# Copyright (c) 2020 oatsu
"""
HTSフルラベルをUSTファイルに変換する。
"""
import utaupy as up


def htsnote2ustnote(hts_note: up.hts.Note, d_table: dict) -> up.ust.Note:
    """
    utaupy.hts.Note を utaupy.ust.Note に変換する。
    """
    ust_note = up.ust.Note()
    ust_note.length = int(hts_note.length) * 20
    phonemes = [phoneme.identity for phoneme in hts_note.phonemes]
    ust_note.lyric = ''.join(phonemes)
    # 音高情報が無かったらC4にする。
    ust_note.notenum = str(hts_note.notenum).replace('xx', '60')
    ust_note.tempo = hts_note.tempo
    return ust_note


def songobj2ustobj(hts_song: up.hts.Song, d_table: dict) -> up.ust.Ust:
    """
    Song オブジェクトを Ust オブジェクトに変換する。
    """
    ust = up.ust.Ust()
    for hts_note in hts_song:
        ust_note = htsnote2ustnote(hts_note, d_table)
        ust.notes.append(ust_note)
    ust.reload_tempo()

    for note in ust.notes:
        if note.lyric == 'pau':
            note.lyric = 'R'
    return ust


def hts2ust(path_hts, path_ust, path_table):
    """
    HTSフルコンテキストラベルファイルをUSTファイルに変換する。
    """
    d_table = up.table.load(path_table)
    full_label = up.hts.load(path_hts)
    ust = songobj2ustobj(full_label.song, d_table)
    ust.write(path_ust)

def main():
    """
    ファイル変換をする。
    """
    path_hts = input('path_hts: ')
    path_ust = path_hts.replace('.lab', '_hts2ust.ust')
    path_table = input('path_table: ')
    hts2ust(path_hts, path_ust, path_table)

if __name__ == '__main__':
    main()
