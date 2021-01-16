#! /usr/bin/env python3
# coding: utf-8
# Copyright (c) 2020 oatsu
"""
UTAUがレンダリング時に出力するtemp.batを読み取ってUSTファイルを出力する。
utaupy.ust.Ust オブジェクトを返せると便利。
できるなら utaupy.utaupluign.UtauPlugin オブジェクトのほうがいい。
[#PREV], [#NEXT] を扱えるため。

temp.batのうち、まずはwavtool1に渡す情報をすべて取得する。
"""

from os.path import basename, splitext

import utaupy


def load_tempbat_setting(path_tempbat: str) -> utaupy.ust.Note:
    """
    temp.bat を読み取って、[#SETTING] の項を再構築する。
    temp.bat の13行目までを読み取って辞書を返す
    """
    # temp.batを読む
    with open(path_tempbat, 'r', encoding='shift-jis') as fb:
        lines = [line.strip('\r\n') for line in fb.readlines()]
    # いったん辞書をつくる
    d = {}
    for line in lines[1:13]:
        _, info = line.split(maxsplit=1)
        key, value = info.split('=', 1)
        d[key] = value
    # [#SETTING] なノートにする
    setting_note = utaupy.ust.Note(tag='[#SETTING]')
    setting_note['Tempo'] = d['tempo']
    setting_note['VoiceDir'] = d['oto']
    setting_note['Tool1'] = d['tool']
    setting_note['Tool2'] = d['resamp']
    setting_note['OutFile'] = d['output']
    setting_note['Chachedir'] = d['cachedir']
    setting_note['Flags'] = d['flag'].strip('"')

    # できたノートを返す
    return setting_note


def load_tempbat_notes(path_tempbat: str) -> list:
    """
    temp.bat を読み取って、通常のノートを再構築する。
    utaupy.ust.Note からなるリストを返す。

    temp.bat の18行目以降のうち、
    '@call %helper%' (音符の場合)
    または
    '@%tool%' (休符の場合)
    から始まる行を取得する。
    """
    # temp.batを読む
    with open(path_tempbat, 'r', encoding='shift-jis') as fb:
        lines = [line.strip('\r\n') for line in fb.readlines()]
    # 使わない行を消す
    # TODO: 子音速度を取得と適用できるようにする。
    lines = [
        line for line in lines[18:]
        if (line.startswith(r'@call %helper%') or line.startswith(r'@"%tool%"'))
    ]
    for line in lines:
        print(line)

    # 音階をNoteNumに変換する辞書
    # 休符は0で入力されるので困る。
    # 困るのでUTAUの休符挿入仕様に合わせてC4の'60'にする。
    d = {
        '0': '60',
        'C1': '24', 'Db1': '25', 'D1': '26', 'Eb1': '27', 'E1': '28', 'F1': '29',
        'Gb1': '30', 'G1': '31', 'Ab1': '32', 'A1': '33', 'Bb1': '34', 'B1': '35',
        'C2': '36', 'Db2': '37', 'D2': '38', 'Eb2': '39', 'E2': '40', 'F2': '41',
        'Gb2': '42', 'G2': '43', 'Ab2': '44', 'A2': '45', 'Bb2': '46', 'B2': '47',
        'C3': '48', 'Db3': '49', 'D3': '50', 'Eb3': '51', 'E3': '52', 'F3': '53',
        'Gb3': '54', 'G3': '55', 'Ab3': '56', 'A3': '57', 'Bb3': '58', 'B3': '59',
        'C4': '60', 'Db4': '61', 'D4': '62', 'Eb4': '63', 'E4': '64', 'F4': '65',
        'Gb4': '66', 'G4': '67', 'Ab4': '68', 'A4': '69', 'Bb4': '70', 'B4': '71',
        'C5': '72', 'Db5': '73', 'D5': '74', 'Eb5': '75', 'E5': '76', 'F5': '77',
        'Gb5': '78', 'G5': '79', 'Ab5': '80', 'A5': '81', 'Bb5': '82', 'B5': '83',
        'C6': '84', 'Db6': '85', 'D6': '86', 'Eb6': '87', 'E6': '88', 'F6': '89',
        'Gb6': '90', 'G6': '91', 'Ab6': '92', 'A6': '93', 'Bb6': '94', 'B6': '95',
        'C7': '96', 'Db7': '97', 'D7': '98', 'Eb7': '99', 'E7': '100', 'F7': '101',
        'Gb7': '102', 'G7': '103', 'Ab7': '104', 'A7': '105', 'Bb7': '106', 'B7': '107',
        'C8': '108', 'Db8': '109', 'D8': '110', 'Eb8': '111', 'E8': '112', 'F8': '113',
        'Gb8': '114', 'G8': '115', 'Ab8': '116', 'A8': '117', 'Bb8': '118', 'B8': '119'
    }
    # ノートのリストを作る
    notes = []
    for line in lines:
        note = utaupy.ust.Note()
        args = line.split()
        # 'otoinidir\か.wav' から 'か' を抽出する。
        note.lyric = splitext(basename(args[2].strip('"')))[0]
        # 音程を抽出する。
        note.notenum = d[args[3]]
        # ノートの長さとテンポ
        length_and_tempo = args[4].split('@', 1)
        note.length = int(length_and_tempo[0])
        # TODO: ここのreplaceしてる部分の値が何を意味するか調べる。
        note.tempo = float(length_and_tempo[1].replace('-', '+').split('+', 1)[0])
        notes.append(note)
        print(note)
    # ノートのリストを返す
    return notes


def load_tempbat_as_ustobj(path_tempbat: str) -> utaupy.ust.Ust:
    """
    temp.bat を読み取って、Ustオブジェクトを生成する。
    """
    ust = utaupy.ust.Ust()
    ust.version = '1.20'
    ust.setting = load_tempbat_setting(path_tempbat)
    ust.notes = load_tempbat_notes(path_tempbat)
    ust.reload_tempo()
    ust.reload_tag_number(start=0)
    return ust


def bat2ust(path_tempbat, path_ust_out):
    """
    temp.bat を読み取って、UTAUプラグイン用のtmpファイルを出力する。
    """
    ust = load_tempbat_as_ustobj(path_tempbat)
    ust.write(path_ust_out)


def main():
    """
    直接スクリプトが実行された時の処理
    """
    path_tempbat = input('path_tempbat: ').strip('"')
    path_ust_out = 'bat2ust_result.ust'
    bat2ust(path_tempbat, path_ust_out)


if __name__ == '__main__':
    main()
