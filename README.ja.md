# ComfyUI FLUX 3 LayoutKit(非公式)

FLUX 3 Image Klein のレイアウト指定(バウンディングボックス表)を ComfyUI で扱うコミュニティ製ノードです。Black Forest Labs、Comfy-Org とは無関係の非公式プロジェクトです。

> **状態: 0.1.0。1台のマシンで検証済み**(Windows 11、RTX 5090、ComfyUI v0.41.0、distilled INT8 の重み)。2領域の text-to-image、参照画像の移動・削除を実重みで実行しました。
> 観測結果(移動が「複製」になった例を含む)は [docs/VERIFICATION.md](docs/VERIFICATION.md) にあります。それ以外(NVFP4、BF16、他GPU、macOS)は未検証です。

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
| 公式コンバータ/パーサ(固定コミット)との一致 | 検証済み(CI) |
| 標準 `FLUX 3 Image Layout Prompt` と text-to-image 行で同一出力 | 検証済み |
| 実 ComfyUI v0.41.0 でのクリーン導入・キュー実行 | 検証済み(Windows 11 + CUDA。モデル不要のワークフローは CI の Ubuntu/Windows CPU でも実行) |
| 2領域 text-to-image(1回) | 両方の気球がボックス内に入った |
| 参照画像の移動(3回) | 2回は移動。キャプションが「元の位置が空」と書いていない回は、移動でなくコピーが追加された |
| 参照画像の削除(`tgt_bbox` null、1回) | 正しく削除された(BFL は仕様を公開していないため観測結果) |
| 速度・メモリ | コールド 4.7 秒、ウォーム約 2.2 秒(1024x1024、wall clock)。`nvidia-smi` の GPU 全体ピーク 11225 MiB |
| NVFP4、BF16、4枚参照、アップサンプラ、他解像度、公式 CLI との同一 seed 比較、macOS | **未検証** |

編集のキャプションには、BFL の推奨どおり**結果の状態**を書いてください。

## ライセンス

コードは MIT です(独自コードのみ)。FLUX 3 Image Klein の重みは FLUX Kommunity License、テキストエンコーダとプロンプトアップサンプラは Apache-2.0 で、本リポジトリはそれらを再ライセンスしません。
商用ファインチューニングは許諾の範囲外になり得ます。詳細は `docs/LICENSING.md` を参照してください。
