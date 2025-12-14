#!/usr/bin/env python3
# Copyright (c) 2022-2023 oatsu
"""
TMPファイル(UTAUプラグインに渡されるUST似のファイル) を
フルラベル(full_score)とモノラベル(mono_score)に変換する。
"""
import utaupy


def utauplugin2score(path_plugin_in, path_table, path_full_out, strict_sinsy_style=False):
    """
    UTAUプラグイン用のファイルをフルラベルファイルに変換する。
    """
    # プラグイン用一時ファイルを読み取る
    plugin = utaupy.utauplugin.load(path_plugin_in)
    # 変換テーブルを読み取る
    table = utaupy.table.load(path_table, encoding='utf-8')

    # 2ノート以上選択されているかチェックする
    if len(plugin.notes) < 2:
        raise Exception(
            'ENUNU requires at least 2 notes. / ENUNUを使うときは2ノート以上選択してください。'
        )

    # 歌詞が無いか空白のノートを休符にする。
    for note in plugin.notes:
        if note.lyric.strip(' 　') == '':
            note.lyric = 'R'
        # フルラベルの区切り文字と干渉しないように符号を置換する
        if note.flags != '':
            note.flags = note.flags.replace('-', 'n')
            note.flags = note.flags.replace('+', 'p')
    # classを変更
    ust = plugin.as_ust()
    # フルラベル用のclassに変換
    song = utaupy.utils.ustobj2songobj(ust, table)
    # ファイル出力
    song.write(path_full_out, strict_sinsy_style)
