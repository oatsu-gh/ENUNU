# ENUNU

NNSVS用歌声モデルをUTAU音源みたいに使えるようにするUTAUプラグイン

## インストールと使い方の記事

[UTAUでNNSVSモデルを使おう！（ENUNU）](https://note.com/crazy_utau/n/n45db22b33d2c)

## 利用規約 - Terms of use 

利用時は各キャラクターの規約に従ってください。尚、本ソフトウェアの規約は LICENSE ファイルとして別途同梱しています。

## インストール方法 - Installation

UTAU を起動し、**ENUNU-{version}.zip** をUTAUのウィンドウにドラッグアンドドロップしてください。

## 使い方 - Usage

1. UST を開く。
2. UTAU 音源として ENUNU 用のモデルを指定するか、NNSVS 用のモデルを含むフォルダを選択する。
3. UST の歌詞をひらがな単独音にする。
4. UST ファイルを保存する。
5. ノートを2つ以上選択してプラグイン一覧から ENUNU を起動する。
6. ～ 数秒か数分待つ ～
7. 生成された WAV ファイルを保存する。

### 使い方ヒント

- 2021年以前に配布された日本語モデルでは、促音(っ)は、直前のノートに含めることをお勧めします。
  - さっぽろ → \[さっ]\[ぽ]\[ろ]
- 2022年以降に配布された日本語モデルでは、促音(っ)は、独立したノートとすることをお勧めします。
  - さっぽろ → \[さ]\[っ]\[ぽ]\[ろ]

- 促音以外の複数文字の平仮名歌詞には対応していません。
- 音素を空白区切りで直接入力できます。平仮名と併用できますが、1ノート内に混在させることはできません。
  - \[い]\[ら]\[ん]\[か]\[ら]\[ぷ]\[て] → \[i]\[r a]\[N]\[k a]\[ら]\[p]\[て]
- 音素の直接入力により、1ノート内に2音節以上を含めることができます。
  - \[さっ]\[ぽ]\[ろ] → \[さっ]\[p o r o]

## 拡張機能について - Extensions

### 拡張機能の使い方

- `%e` : SimpleEnunu のフォルダ
- `%v` : SimpleEnunu 用モデルのフォルダ
- `%u` : UTAU のフォルダ

```yaml
# config.yaml example to activate extensions
extensions:
    ust_editor: "%e/extensions/voicecolor_applier/voicecolor_applier.py"
    timing_editor:
      - "%e/extensions/timing_repairer.py"
      - "%e/extensions/velocity_applier.py"
    acoustic_editor: "%e/extensions/f0_smoother.py"
```

### 拡張機能一覧

#### ust_editor (UST を編集する機能)

- voicecolor_applier : `あ強` などの表情サフィックスを使用可能にします。（例：`強` が含まれる場合は `Power` をフラグ欄に追記します。）
- lyric_nyaizer (ust_editor) : 歌詞を `ny a` にします。主にデバッグ用です。

#### score_editor (フルラベルを編集する機能)
- score_myaizer : 歌詞を `my a` にします。主にデバッグ用です。

#### timing_editor (タイミングラベルを編集する機能)
- timing_repairer : ラベル内の音素の発声時間に不具合がある場合に自動修正を試みます。
- velocity_applier : USTの子音速度をもとに子音の長さを調節します。

#### acoustic_editor (f0 などを編集する機能)
- f0_feedbacker : ENUNUモデルで合成したピッチ線を UST のピッチにフィードバックします。EnuPitch のようなことができます。
- f0_smoother : 急峻なピッチ変化を滑らかにします。

#### 複合
- style_shifter (ust_editor, acoustic_editor) : USTのフラグ に `S5` や `S-3` のように記入することで、スタイルシフトのようなことができます。
- vibrato_applier (ust_editor, acoustic_editor) : USTのビブラートを f0 に反映します。

#### その他
- dummy : とくに何もしません。デバッグ用です。

### 

---

ここからは開発者向けです

---



## 開発環境

- Windows 10
- Python 3.12
- CUDA 13.0

## ENUNU向けUTAU音源フォルダの作り方

通常のNNSVS用歌声モデルも使えますが、[enunu training kit](https://github.com/oatsu-gh/enunu_training_kit)を使ったほうがすこし安定すると思います。採譜時の音程チェック用に、再配布可のUTAU単独音音源の同梱をお勧めします。

### 通常のモデルを使う場合

モデルのルートディレクトリに enuconfig.yaml を追加し、ENUNU用おふとんP歌声モデルなどを参考にして書き換えてください。`question_path` は学習に使ったものを指定し、同梱してください。

### ENUNU用のモデルを使う場合

モデルのルートディレクトリに enuconfig.yaml を追加し、[波音リツ ENUNU Ver.2](http://www.canon-voice.com/enunu.html) 同梱のファイルを参考にして書き換えてください。`question_path` は学習に使ったものを指定し、同梱してください。

## ラベルファイルに関する備考

フルコンテキストラベルの仕様が Sinsy のものと異なります。重要な相違点は以下です。

- フレーズに関する情報を扱わない（e18-e25,  g,  h,  i,  j3）
- ノートの強弱などの音楽記号を扱わない（e26-e56）
- 小節に関する情報を扱わない（e10-e17,  j2,  j3）
- 拍に関する情報を扱わない（c4,  d4,  e4）
- **休符を挟んだ場合のノートおよび音節の前後情報（a, c, d, f）が異なる**
  - Sinsyの仕様では、休符の直前のノートが持つ「次のノート」の情報は休符終了後のノートを指しますが、本ツールでは休符を指す設計としています。
  - 休符の直後のノートも同様に、休符開始前ではなく休符そのものを指す設計としています。
  - 音節も同様です。
