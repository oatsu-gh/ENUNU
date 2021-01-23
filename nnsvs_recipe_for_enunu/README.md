# nnsvs_recipe_for_enuenu

ENUNUでの利用に最適化した歌声モデルを生成するためのNNSVS用レシピ。

## 実行環境

- Windows 10
  - NNSVS の環境は [setup_nnsvs_on_wsl](https://github.com/oatsu-gh/setup-nnsvs-on-wsl) で構築したものを想定
  - WSL（Ubuntu 20.04, Ubuntu 20.04 LTS）
    - Python 3.8

## 通常のレシピとの違い

- 学習データのフルコンテキストラベルファイルの休符周辺をENUNUに最適化するステップが含まれます。
- 促音の処理を変更するかもしれません。（未定）
- ブレスの処理を変更するかもしれません。（未定）
