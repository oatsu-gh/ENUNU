#!/usr/bin/env python3
# Copyright (c) 2024 oatsu
"""
USTのサフィックスをVoiceColorとして検出し、
HTSフルラベルの特定のカラムに対応する文字列を登録するENUNU拡張機能。
ust_editor と lab_editor として呼び出す。
歌詞はひらがなとカタカナと休符だけ対応する。それ以外の歌詞はフラグを立てない。

辞書内の順序に依存するので、Python3.7以降でないと正常に動作しないことに注意。
"""

from copy import copy
from argparse import ArgumentParser
from tqdm import tqdm
from tqdm.contrib import tzip
import utaupy
from pprint import pprint

VOICECOLOR_DICT = {
    '通常': 'Normal',
    '強': 'Loud',
    '弱': 'Soft',
    '裏': 'Falsetto',
    '囁': 'Breathy',
    '甘': 'Sweet',
    '岩': 'Rock',
    '俺': 'Me',
    'Loud': 'Loud',
    'Soft': 'Soft',
    'Rock': 'Rock',
    'Pop': 'Pop'
}

def pop_voicecolors_in_ust(ust: utaupy.ust.Ust, voicecolor_dict: dict):
    """USTオブジェクト内の全ノートのサフィックスを取得しつつ、元のノートからは削除する。

    >>> d = {'強': 'Loud', '強裏':'LF', '裏':'Falsetto'}
    >>> ust = utaupy.ust.Ust()
    >>> ust.notes = [utaupy.ust.Ust() for i in range(4)]
    >>> ust.notes[0].lyric = 'あ強'
    >>> ust.notes[1].lyric = 'い裏'
    >>> ust.notes[2].lyric = 'う強裏'
    >>> ust.notes[3].lyric = 'R強'
    >>> ust, suffixes, voicecolors = pop_voicecolors_in_ust(ust, d)
    >>> suffixes, voicecolors
    (['強', '裏', '強裏', '強'], ['Loud', 'Falsetto', 'LF', 'Loud'])

    """
    key = '$EnunuSuffixVoiceColor'
    ust.setting[key] = True
    ust = copy(ust)

    # サフィックスの辞書を文字数順にソートする
    voicecolor_dict = dict(sorted(voicecolor_dict.items(), key=lambda x: len(x[0]), reverse=True))

    # TODO: ここ実装する
    if ust.previous_note is not None:
        pass
    # TODO: ここも実装する
    if ust.next_note is not None:
        pass

    # 取り出したsuffixのリスト
    l_suffixes = []
    l_voicecolors = []
    for note in tqdm(ust.notes):
        # 表情の文字列があったらリストに取り出して次のノートに移る
        for k, v in voicecolor_dict.items():
            if k in note.lyric:
                note.lyric = note.lyric.replace(k, '')
                l_suffixes.append(k)
                l_voicecolors.append(v)
                break
        # 表情の文字列がなかったら空白文字をリストに登録して次のノートに移る
        else:
            l_suffixes.append('')
            l_voicecolors.append('')
    assert len(l_suffixes) == len(l_voicecolors) == len(ust.notes)
    return ust, l_suffixes, l_voicecolors


def main(voicecolor_dict=VOICECOLOR_DICT):
    """全体の処理をする
    """
    parser = ArgumentParser()
    parser.add_argument('--ust', help='選択部分のノートのUSTファイルのパス')
    # 使わない引数は無視して、必要な情報だけ取り出す。
    args, _ = parser.parse_known_args()
    path_ust = args.ust
    # ustファイルを読み取る
    ust = utaupy.ust.load(path_ust)

    # 表情音源のプレフィックス・サフィックスをvoicecolorの文字列として抽出する
    print('USTの歌詞からVoiceColorを取得します。/ Checking VoiceColors in notes.')
    ust, _, l_voicecolors = pop_voicecolors_in_ust(ust, voicecolor_dict)

    # voicecolorの文字列をフラグに付加する
    print('VoiceColorを一時ファイルのフラグに転記します。/ Copying VoiceColors to flags.')
    for note, voicecolor in tzip(ust.notes, l_voicecolors):
        note.flags = note.flags + voicecolor

    # USTファイルを上書き
    ust.write(path_ust)
    print('VoiceColorの取得と転記を完了しました。/ Finished checking and copying VoiceColors.')



if __name__ == '__main__':
    print('voicecolor_applier.py (2024-04-28) -------------------------')
    pprint(VOICECOLOR_DICT)
    main(VOICECOLOR_DICT)
    print('-------------------------------------------------------')
