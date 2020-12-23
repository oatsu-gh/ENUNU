#! /usr/bin/env python3
# coding: utf-8
# Copyright (c) 2020 oatsu
"""
UTAU の Tool1 (wavtool) の代わりに使う。

## 処理内容
遺言状があるかどうか確認する

- 遺言状がない場合
  - temp.bat を読み取り、全体で何ノートを処理するか調べる。
  - 全体で何ノートあるか、新規の遺言状を作って**1行目**に記録する。このとき `open(path, 'w')` とすること。
- 必ず実施
  - 遺言状に自分が何人目のwavtoolか**2行目以降**に追記する。このとき `open(path, 'a')` とすること。
  - 自分が最後のwavtoolかどうか調べる。
    - この時点で遺言状の a==b になっていた場合は自分が最後。
    - 最後だった場合はwav生成を行う。
      - temp.bat の情報または temp$$$.ust を取得して、utaupy.ust.Ust オブジェクトを生成する。
      - utaupy.ust.Ust を ENUNU に渡してwav生成する。
      - wavを生成したら遺言状を処分する。
"""
from os import chdir, getcwd, remove
from os.path import dirname, exists, abspath
from subprocess import run


def first_wavtool_task(path_tempbat: str, path_last_will: str):
    """
    tool1 が1回目に起動されたときの処理。
    いくつノートを処理するのかを調べ、記録するためのファイルをつくる。

    path_tem_bat: 一時ファイル(temp.bat)のパス
    path_last_will_txt: 遺言状(last_will.txt)のパス
    """
    # temp.batを読み取る
    with open(path_tempbat, 'r') as f:
        s = f.read()
    how_many_notes = s.count(r'%helper%') + s.count(r'%tool%')

    # 遺言状を書く
    with open(path_last_will, 'a', encoding='utf-8') as f:
        f.write(f'{how_many_notes} 1')


def usual_wavtool_task(path_last_will):
    """
    遺言状を読んで処理番号を書き直す。
    最後のwavtoolだったときは音声ファイル生成をする。
    """
    # 遺言状を読む
    with open(path_last_will, 'r', encoding='utf-8') as f:
        s = f.read()
    # 選択範囲にいくつノートがあるか、何番目のノートを処理しているかを取得
    how_many_notes, idx = list(map(int, s.strip().split()))

    # 遺言状を書く
    with open(path_last_will, 'w', encoding='utf-8') as f:
        # 実行履歴を増やす
        idx += 1
        # 今から書く遺言状の文字列
        s = f'{how_many_notes} {idx}'
        f.write(s)

    return how_many_notes, idx


def last_wavtool_task(path_tempbat, path_last_will,):
    """
    1. batファイルをustファイルに変換する。
        - これエンジンがやる必要ない。パス渡そう。
    2. ustファイルをlabファイルに変換する。(フルコンテキストラベル)
        - これもエンジンがやる必要ない。パス渡そう。
    3. labファイルをENUNUっぽい外部アプリケーションに渡す。
        - Q. ここの「外部アプリケーション」はENUNUそのもので良くない？
        - A. wavの出力先を変えるべきなので良くない。
        - Q. ENUNUにエンジン用のPythonスクリプトを同梱すれば良いですよね？
        - A. そうですね。
        という脳内会話があったのでENUNUに enunu_for_engine.py っぽいのを仕込んでおきます。
        - これもエンジンがやる必要ない。enunu_for_engineにパス渡そう。
    """
    original_cwd = getcwd()
    path_wavtool = None
    with open(path_tempbat) as fb:
        lines = [line.strip() for line in fb.readlines()]
    # wavtoolのパスを取得する。enutool.exeを選択しているはず。
    for line in lines:
        if line.startswith('@set tool='):
            path_wavtool = line.replace('@set tool=', '')
            break
    # pyinstallerでexe化すると __file__ が取得できなくなるのを対策。
    path_wavtool_dir = dirname(path_wavtool.strip('"'))
    path_python_exe = f'{path_wavtool_dir}/python-3.8.6-embed-amd64/python.exe'
    path_enunu = f'{path_wavtool_dir}/enunu.py'
    args = [path_python_exe, path_enunu, path_tempbat]
    try:
        run(args, check=True)
    except Exception as e:
        print(e)
        print('The exception is from last_wavtool_task at line 85 in enutool.py')
        print('enutoolが実行しようとしたコマンド:', end=' ')
        print(' '.join(args))
        for arg in args:
            print(f'os.path.exist({arg}): {exists(arg)}')
        input('エンターキーを押してください。')
    chdir(original_cwd)
    remove(path_last_will)


def main():
    """
    遺言状を読む。
    無ければ作る。
    自分が最後の実行か調べる。
      - そうだったらwav生成をする。外部アプリケーションにappdata/temp内のutauのフォルダを教える。
      - 役目が終わったら遺言状を消す。USTも消す。
    """
    path_last_will = 'last_will.txt'
    path_tempbat = 'temp.bat'

    # 自分が最初のwavtoolだった時の処理
    if not exists(path_last_will):
        print('Copyright (c) 2020 oatsu')
        print('Copyright (c) 2001-2020 Python Software Foundation')
        first_wavtool_task(path_tempbat, path_last_will)
        return

    # 自分が最初のwavtoolではない時の処理
    how_many_notes, idx = usual_wavtool_task(path_last_will)
    # 自分が最後のwavtoolだった時の処理
    if idx >= how_many_notes:
        # DEBUG: exeで実行すると__file__がおかしい(cwdになる)
        path_python_exe = f'{dirname(abspath(__file__))}/python-3.8.6-embed-amd64/python.exe'
        path_enunu_for_engine = f'{dirname(abspath(__file__))}/enunu.py'
        last_wavtool_task(path_tempbat, path_last_will)


if __name__ == '__main__':
    main()
