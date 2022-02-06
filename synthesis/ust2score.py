#!/usr/bin/env python3
# Copyright (c) 2022 oatsu
"""
TMPファイル(UTAUプラグインに渡されるUST似のファイル) を
フルラベル(full_score)とモノラベル(mono_score)に変換する。
"""
import utaupy


def ust2score(path_plugin_in, path_table, path_full_out, path_mono_out=None,
              strict_sinsy_style=False):
    """
    USTじゃなくてUTAUプラグイン用に最適化する。
    ust2hts.py 中の ust2hts を改変して、
    [#PREV] と [#NEXT] に対応させている。
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

    # [#PREV] や [#NEXT] が含まれているか判定
    prev_exists = plugin.previous_note is not None
    next_exists = plugin.next_note is not None
    if prev_exists:
        plugin.notes.insert(0, plugin.previous_note)
    if next_exists:
        plugin.notes.append(plugin.next_note)

    # Ust → HTSFullLabel
    song = utaupy.ustobj2songobj(plugin, table)
    full_label = utaupy.hts.HTSFullLabel()
    full_label.song = song
    full_label.fill_contexts_from_songobj()

    # [#PREV] と [#NEXT] を消す前の状態での休符周辺のコンテキストを調整する
    if prev_exists or next_exists:
        full_label = utaupy.hts.adjust_pau_contexts(
            full_label, strict=strict_sinsy_style)
        full_label = utaupy.hts.adjust_break_contexts(full_label)

    # [#PREV] のノート(の情報がある行)を削る
    if prev_exists:
        target_note = full_label[0].note
        while full_label[0].note is target_note:
            del full_label[0]
        # PREVを消しても前のノート分ずれているので、最初の音素開始時刻が0になるようにする。
        # ずれを取得
        offset = full_label[0].start
        # 全音素の開始と終了時刻をずらす
        for oneline in full_label:
            oneline.start -= offset
            oneline.end -= offset
    # [#NEXT] のノート(の情報がある行)を削る
    if next_exists:
        target_note = full_label[-1].note
        while full_label[-1].note is target_note:
            del full_label[-1]

    # ファイル出力
    s = '\n'.join(list(map(str, full_label)))
    with open(path_full_out, mode='w', encoding='utf-8') as f:
        f.write(s)
    if path_mono_out is not None:
        full_label.as_mono().write(path_mono_out)
