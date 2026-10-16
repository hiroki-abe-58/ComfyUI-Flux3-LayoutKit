# ComfyUI FLUX 3 LayoutKit(非公式)

FLUX 3 Image Klein のレイアウト指定(バウンディングボックス表)を ComfyUI で扱うコミュニティ製ノードです。Black Forest Labs、Comfy-Org とは無関係の非公式プロジェクトです。

> **状態: 0.1.0 プレリリース。モデルなしの検証のみ。** 契約(座標の取り決め)・ノード・ワークフローは、公式リファレンスコードと実際の ComfyUI v0.41.0 のキューで検証済みですが、
> **FLUX 3 の重みを使った生成はまだ行っていません**。`remove`(削除)行の挙動は BFL が仕様を公開していません。

## 何を足すのか

ComfyUI v0.41.0 には `Create Bounding Boxes`(描画キャンバス)と `FLUX 3 Image Layout Prompt`(text-to-image 用の表をプロンプトへ追記)が標準で入っています。
描画や通常のレイアウトはそちらを使ってください。本パッケージは標準にない次の部分だけを扱います。

* **参照画像の編集行**(`from` / `src_bbox` / `tgt_bbox`:追加・移動・維持・削除)
* **0〜1 と 0〜1000 の取り違え検出**(標準ノードは 0〜1 の値をそのまま通します)
* 各領域が `<id>` でプロンプトに引用されているかの検査
* 同じ行から公式 CLI の `--boxes` ファイル(0〜1)を出力
* 移動の矢印・削除の×を描くプレビュー

ボックスは `[y_min, x_min, y_max, x_max]`(y が先)。プロンプトの表は 0〜1000、公式 CLI の `--boxes` ファイルは 0〜1 です。ボックスは構図の誘導であり、厳密なマスクではありません。

## インストール

ComfyUI v0.41.0 以上。`custom_nodes` に clone するだけです。モデルは同梱せず、Hugging Face 上の FLUX Kommunity License に各自で同意して取得してください。

## 検証状況

| 項目 | 状態 |
|---|---|
| 公式コンバータ/パーサ(固定コミット)との一致 | 検証済み |
| 標準 `FLUX 3 Image Layout Prompt` と text-to-image 行で同一出力 | 検証済み |
| 実 ComfyUI サーバーでのノード登録、`layout_only` ワークフローのキュー実行 | 検証済み(CPU のみ、Windows 11、ComfyUI v0.41.0) |
| FLUX 3 重みでの生成、削除の挙動、速度・VRAM | **未検証**(数値は記載しません) |

## ライセンス

コードは MIT です(独自コードのみ)。FLUX 3 Image Klein の重みは FLUX Kommunity License、テキストエンコーダとプロンプトアップサンプラは Apache-2.0 で、本リポジトリはそれらを再ライセンスしません。
商用ファインチューニングは許諾の範囲外になり得ます。詳細は `docs/LICENSING.md` を参照してください。
