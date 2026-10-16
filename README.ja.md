# ComfyUI FLUX 3 LayoutKit(非公式)

Small, strict FLUX 3 layout/bbox interoperability utilities for ComfyUI.(FLUX 3 のレイアウト/bbox を厳格に扱う小さな相互運用ユーティリティです)

バウンディングボックスのエディタではありません。FLUX 3 Image Klein がプロンプトから読むレイアウト表を変換・検証し、実重みで使ったときの観測結果を記録します。
Black Forest Labs・Comfy-Org とは無関係の非公式プロジェクトです。

## 目的

1. **0〜1 と 0〜1000 の相互変換**:公式 CLI の `--boxes` は 0〜1、Diffusers/ComfyUI はプロンプト内で 0〜1000。どちらも `[y_min, x_min, y_max, x_max]`。リージョンの `scale` と compose ノードの `cli_boxes_json` が公式と同じ丸め(`round(v * 1000)`)で変換します。
2. **厳格な検証**:`bbox` / `src_bbox` / `tgt_bbox` / `from`(`target` または `ref_image_N`)/ 参照 index / id / 説明文。座標系の取り違え(0〜1 を 0〜1000 として渡す等)はクランプせず拒否します。
3. **検証の証拠**:公式パーサ(固定コミット)との一致テストと、RTX 5090 での実生成の記録([docs/VERIFICATION.md](docs/VERIFICATION.md))。期待どおりにならなかった例も含みます。

## 既存プロジェクトとの棲み分け

ボックスの描画・編集ワークフローは、次の既存プロジェクトを使ってください(各 README の記述に基づく要約で、動作は私は未検証です)。

| プロジェクト | 性格 |
|---|---|
| [ComfyUI 本体](https://github.com/Comfy-Org/ComfyUI)(`Create Bounding Boxes` など) | 標準のキャンバスと text-to-image 用レイアウト行 |
| [InpaintCanvas](https://github.com/DenRakEiw/ComfyUI-InpaintCanvas) | リッチなキャンバス/エディタ中心のワークフロー |
| [ComfyUI-EditUtils](https://github.com/lrzjason/ComfyUI-EditUtils) | 包括的な編集ユーティリティ(FLUX.3 Klein の bbox キャンバスを含む) |
| [NKD Klein Tools](https://github.com/Nekodificador/ComfyUI-NKD-Klein-Tools) | 高レベルな Klein ワークフローユーティリティ |
| [Comfyui-Flux3-PE-GGUF-T8](https://github.com/T8mars/Comfyui-Flux3-PE-GGUF-T8) | GGUF によるローカルのプロンプト強化(参照画像・レイアウト対応) |
| **本リポジトリ** | スキーマ/座標の検証と相互運用に限定。一致テストと検証の証拠 |

## 検証状況

| 項目 | 状態 |
|---|---|
| 公式コンバータ/パーサ(固定コミット)との一致 | 検証済み(CI) |
| 標準 `FLUX 3 Image Layout Prompt` と text-to-image 行で同一出力 | 検証済み |
| 実 ComfyUI v0.41.0 でのクリーン導入・キュー実行 | 検証済み(Windows 11 + CUDA。モデル不要のワークフローは CI の Ubuntu/Windows CPU でも実行) |
| 2領域 text-to-image(1回) | 両方の気球がボックス内に入った |
| 編集行 `move`(3回) | 2回は移動。キャプションが「元の位置が空」と書いていない回は、移動でなくコピーが追加された |
| 編集行 `remove`(`tgt_bbox` null、1回) | 正しく削除された(BFL は仕様を公開していないため観測結果) |
| 速度・メモリ | コールド 4.7 秒、ウォーム約 2.2 秒(1024x1024、wall clock)。`nvidia-smi` の GPU 全体ピーク 11225 MiB |
| NVFP4、BF16、4枚参照、アップサンプラ、他解像度、公式 CLI との同一 seed 比較、macOS | **未検証** |

編集のキャプションには、BFL の推奨どおり**結果の状態**を書いてください。Comfy Registry には登録していません。GitHub から導入してください。

## ライセンス

コードは MIT です(独自コードのみ)。FLUX 3 Image Klein の重みは FLUX Kommunity License、テキストエンコーダとプロンプトアップサンプラは Apache-2.0 で、本リポジトリはそれらを再ライセンスしません。
商用ファインチューニング等は別途 BFL のライセンスが必要になり得ます(法的助言ではありません)。詳細は `docs/LICENSING.md` を参照してください。
