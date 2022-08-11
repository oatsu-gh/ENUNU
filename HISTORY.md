# 更新履歴

## v0.0.1 (2020-12-03)

- 初リリース
- おふとん P (ENUNU) を同時配布

## v0.0.2 (2020-12-04)

- CUDA のない環境で動作しない不具合を修正
  - python-3.8.6-embed-amd64/Lib/site-packages/torch/lib 以下のファイル不足を修正
- utaupy 1.10.0 の正式版を同梱

## v0.0.3 (2020-12-10)

- 音量ノーマライズ無効かつ 32bit 出力のときに音量が小さいのを修正

## v0.1.0 (2021-02-11)

- utaupy 1.11.4 になる予定の開発版を同梱
- 出力するフルコンテキストラベルに「前の休符からの距離(p18)」を追加
- 出力するフルコンテキストラベルに「次の休符までの距離(p19)」を追加
- ust ファイル名に空白があると、生成した wav ファイルを再生できない不具合を修正
  - 半角スペースを半角アンダーバー `_` に置換して wav 出力
  - 全角スペースを半角アンダーバー `_` に置換して wav 出力
- enuconfig.yaml の内容を簡略化

## v0.2.0 alpha (2021-08-14)

- ライセンスを MIT License に変更
- 学習ツール強化
  - プラグインには同梱しない。
  - UST から学習できるようになった。
  - 学習データ整合性チェックが充実した。
- プラグイン更新
  - UST のフルパスに空白スペースが含まれていると WAV 出力できない不具合を修正
  - WAV 出力を 32bit float に固定
  - WAV 出力フォルダを変更
    - UST のあるフォルダ/曲名\_時刻.wav -> UST のあるフォルダ/曲名\_時刻/曲名\_時刻.wav
  - UST から生成したフルラベルとモノラベルの出力フォルダを変更
    - UST のあるフォルダ/曲名\_時刻/曲名\_時刻\_mono_score.lab
    - UST のあるフォルダ/曲名\_時刻/曲名\_時刻\_full_score.lab
  - timing, f0, mgc, bap のファイル出力機能を追加
    - UST のあるフォルダ/曲名\_時刻/曲名\_時刻\_timing.lab
    - UST のあるフォルダ/曲名\_時刻/曲名\_時刻.f0
    - UST のあるフォルダ/曲名\_時刻/曲名\_時刻.mgc
    - UST のあるフォルダ/曲名\_時刻/曲名\_時刻.bap

## v0.2.0 (2021-09-01)

- 合成時に失敗する不具合を修正
  - 同梱の scikit-learn を v0.23.2 にダウングレード

## v0.2.1 (2021-09-19)

- UST を保存しなくても WAV 合成できるように変更

## v0.2.2 (2021-09-19)

- 初回起動時に PyTorch を自動ダウンロード＆インストールする機能を実装

## v0.2.3 (2021-09-19)

- NVIDIA 製 GPU 非搭載端末で、PyTorch 自動ダウンロードに失敗する不具合を修正
- 選択ノート数が少ないとき（2 ノート未満のとき）に出るエラーを理解しやすくした。
- モデルが適切に指定されていないとき（enuconfig.yaml が音源フォルダにないとき）に出るエラーを理解しやすくした。
- 歌詞がないノートがを休符として扱うようにした。

## v0.2.4 (2021-09-24)

- 出力フォルダが適切に設定されない不具合を修正
- 学習用スクリプトに、音声ファイル点検機能を追加
  - 全ファイルがモノラルであるか確認
  - 全ファイルのサンプリングレートが一致するか確認
  - 全ファイルのビット深度が一致するか確認
- nnmnkwii でのフルラベル読み取り時の文字コードを UTF-8 に固定
- CUDA 10 の環境で PyTorch のバージョン選択が適切でない不具合を修正
- CUDA 11, 10 の環境で自動インストールする PyTorch バージョンを 1.9.0 から 1.9.1 に変更

## v0.2.5 (2021-09-24)

- UST ファイル出力の不具合を修正

## v0.3.0 (2022-03-26)

- mgc, bap, f0 ファイルの出力機能をいったん削除しました。
  - 拡張機能として後日復活実装予定です。
- タイミングや音素を加工するための、拡張機能を呼び出す機能を追加しました。
- enuconfig.yaml の必須項目から以下の項目を削除しました。
  - `trained_for_enunu`
- enuconfig.yaml の任意項目に以下の項目を追加しました。
  - extensions
    - `ust_editor`
    - `ust_converter`
    -  `score_editor`
    - `timelag_calculator`
    - `timelag_calculator`
    - `duration_calculator`
    - `duration_editor`
    - `timing_calculator`
    - `timing_editor`
    - `acoustic_calculator`
    - `acoustic_editor`
    - `wav_synthesizer`
    - `wav_editor`
- USTの子音速度を利用する拡張機能を追加しました。
  - enuconofig.yaml の `extentions` のうち `timing_editor` に `"%e/extensions/velocity_applier.py"` を指定することで利用できます。
- タイミングラベルの不具合を修復する拡張機能を追加しました。
  - enuconofig.yaml の `extentions` のうち `timing_editor` に `"%e/extensions/timing_repairer.py"` を指定することで利用できます。

## v0.3.1 (2022-03-29)

- 外部の timing_editor を呼び出してモノラベルだけを編集した場合に、処理結果が適用されない不具合を修正。

## v0.4.0 (2022-04-24)

- nnsvs を master ブランチの最新版に更新しました。
  - SHA : `4da3adccd42a581b8c69e01d0e15d9e0b4704373`
- f0 ファイルなどを加工できるようにしました。
- enuconfig.yaml の任意項目から以下の項目を削除しました。
  - extensions
    - `timelag_calculator`
    - `timelag_editor`
    - `duration_calculator`
    - `duration_editor`
- 急激なf0変化を滑らかにする拡張機能を追加しました。
  - enuconofig.yaml の `extentions` のうち `acoustic_editor` に `"%e/extensions/f0_smoother.py"` を指定することで利用できます。

## v0.4.1 (2022-07-10)

- 合成後に無音が含まれる場合に、WAV全体がノイズのように出力される不具合を修正
  - 32bit float の形式で出力するときに16bitの値のまま出力する場合があったため、音量が大きすぎてノイズに聞こえる。

## v0.5.0 (2022-08-09)

- Vibratoモデルに対応
- GAN-based mgc postfilter に対応

## v0.5.1 (2022-08-11)

- mgc_postfilter まわりの不具合を修正
