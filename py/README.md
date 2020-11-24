# py

python scripts for ENUNU

## ファイル紹介

### enunu.py

USTファイルを受け取って動作するスタンドアロンまたはUTUAプラグインとして、全体の動作を行うスクリプト。

### hts2json.py

Sinsy仕様のHTSフルコンテキストラベルの可読性を高めるためにJSONファイルに変換するスクリプト。

### hts2wav.py

Sinsy仕様のHTSフルコンテキストラベルを受け取って、wavファイルを合成するスクリプト。enuenu.py においてモジュールとして import する。単独でも動作する。

### modify_full_label_for_enunu.py

歌声モデル生成用レシピの stage 0 において、step 2 の直後に実行される。フルコンテキストラベルにおける 音符の音程 や 休符 に関するコンテキストを書き換え、ENUNUに適した仕様に変更する。

### ust2hts.py

USTファイルをSinsy仕様のHTSフルコンテキストラベルに変換するスクリプト。

