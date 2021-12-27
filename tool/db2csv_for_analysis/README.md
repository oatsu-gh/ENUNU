# db2csv for analysis

ENUNU用の歌唱データベースの音素データを、分析しやすい形式のCSVファイルにまとめる。

## 使い方

1. 歌唱DBを選択する
2. 待つ
3. CSVをExcelとかで適当に編集する

## 処理内容

1. USTからフルラベル（full_score）を生成する。
2. モノラベル（mono_align）とフルラベル（full_score）の整合性を点検する。
3. モノラベル（mono_align）とフルラベル（full_score）を列方向に結合する。
4. 列 `songname` を追加して、全曲のデータを行方向に結合する。
5. 列 `index` を追加する。
6. いったん保存する。
7. 列 `start_round`, `end_round`, `duration`, `duration_round`, `timelag`, `timelag_round` などを追加する。
8. 列 `p3_p4`, `p4_p5 `, `p2_p3_p4`, `p3_p4_p5`, `p4_p5_p6`, `p2_p3_p4_p5`, `p3_p4_p5_p6`, `p2_p3_p4_p5_p6` を追加する。（音素出現パターン解析用）
9. もう一度保存する。
10. xx を空白に置き換えたCSVも生成すると良さそう。
11. NULLだけの列を削除する。（dropna）
11. 生成したファイルをExcelなどで分析する。
