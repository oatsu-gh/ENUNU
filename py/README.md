# py

python scripts for ENUNU

## ファイル紹介

### enunu.py

UTAUプラグインまたはUTAUエンジンとして、全体の動作を行うスクリプト。スタンドアロン実行は実装準備中。

### enusampler.py

UTAUエンジンのうち、tool2 の resampler の代わりの処理をするスクリプト。**enusampler.exe** に変換して実行する。ダミーエンジンとして動作するため、処理は皆無。

### enusampler.c

pyinstallerを使うくらいならC言語でexe作ったほうがいいと思った。ダミーなので何もしない。

### enutool.py

UTAUエンジンのうち、tool1 の wavtool の代わりの処理をするスクリプト。**enutool.exe** に変換して実行する。last_will.txt を実行時に残し、タイミングを見計らって enunu.py を起動する役割を持つ。

### hts2json.py

Sinsy仕様のHTSフルコンテキストラベルの可読性を高めるためにJSONファイルに変換するスクリプト。

### hts2wav.py

Sinsy仕様のHTSフルコンテキストラベルを受け取って、wavファイルを合成するスクリプト。enuenu.py においてモジュールとして import する。単独でも動作する。

### modify_full_label_for_enunu.py

歌声モデル生成用レシピの stage 0 において、step 2 の直後に実行される。フルコンテキストラベルにおける 音符の音程 や 休符 に関するコンテキストを書き換え、ENUNUに適した仕様に変更する。

### ust2hts.py

USTファイルをSinsy仕様のHTSフルコンテキストラベルに変換するスクリプト。

