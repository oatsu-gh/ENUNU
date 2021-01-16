# enutool / enusampler

UTAUでNNSVS用のモデルを動かすエンジン

## 開発目標

UTAUのエンジンとして実行させる。

## 制約

- UTAUがレンダリング時に生成する一時ファイルを改変してはならない。
  - temp.bat
  - temp_helper.bat
  - temp$$$.ust

## データ源に使えるもの

- wav合成時の実行フォルダは `C:\Users\<username>\AppData\Local\Temp\utau1\` など
- 実行フォルダ内に下記のファイルが一時的に生成される。これらはUTAUを閉じると消える。
  - temp.bat
  - temp_helper.bat
  - temp$$$.ust
- キャッシュフォルダの位置は？
  - USTが保存されていれば `ustdir\<basename_of_ust>.cache `フォルダ
  - USTが保存されていなければ `C:\Users\<username>\AppData\Local\Temp\utau1\temp.cache` フォルダ

## 内部設計

### resampler

何もしない。

### wavtool

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



---

## 開発メモ

### エンジンの呼ばれ方

tool2

tool1

tool2

tool1

の順でノートごとに繰り返し呼ばれる。

### エンジン起動時に渡される情報

tool2があればほとんどの情報は獲得できそうだが、休符の情報はtool1にしか渡らない。tool1は音程の情報を取得できない。

#### tool1

`tool1.exe` `path_output_wav` `path_otoini\lyric.wav` `音高(C4とか。休符では0)` `Length@Tempo+.STP` (略) `Tag`

休符のときはタグが0に固定されるので注意

```bat
C:\Users\<username>\Documents\GitHub\ENUNU\engine\dist\dummy1.exe temp.wav C:\Users\<username>\AppData\Local\Temp\utau1\temp.cache\3_い_D4_7B3nV5.wav 0 480@120+.0 0 5 35 0 100 100 0
C:\Users\<username>\Documents\GitHub\ENUNU\engine\dist\dummy1.exe temp.wav C:\Users\<username>\AppData\Local\Temp\utau1\temp.cache\4_う_E4_IzNM1c.wav 0 240@120+.0 0 5 35 0 100 100 0

```

#### tool2

```bat
C:\Users\<username>\Documents\GitHub\ENUNU\engine\dist\dummy2.exe D:\UTAU\voice\uta\い.wav C:\Users\<username>\AppData\Local\Temp\utau1\temp.cache\3_い_D4_7B3nV5.wav D4 100  5.0 550 52.0 87.0 100 0 !120 +c+w/D/V/l/x/6//AA#80#ABAGAPAcAsA+BSBm
C:\Users\<username>\Documents\GitHub\ENUNU\engine\dist\dummy2.exe D:\UTAU\voice\uta\う.wav C:\Users\<username>\AppData\Local\Temp\utau1\temp.cache\4_う_E4_IzNM1c.wav E4 100  5.0 300 50.0 88.0 100 0 !120 +c+w/D/V/l/x/6//AA#33#ADAHANAVAeAoAy
```

### NNSVSを呼んでwavを合成するタイミング

batファイルを読み取ることで、選択範囲の最後のコマンドまたはwavファイル名がわかる。

休符のときはwavtool2が呼ばれなくなるから、呼ばれたかどうかを遺言で残すといいかも。

### 選択範囲内のノート数

休符を含めたい。

ノート数 =n(`"%tool%"`) +n(`"%helper%"`)



