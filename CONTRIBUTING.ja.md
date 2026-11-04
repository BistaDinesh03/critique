# Critique にコントリビュートする

参加していただきありがとうございます！Critique は意図的にシンプルで保守しやすいものを目指しています。

> この文書は Critique のコントリビュートガイドの日本語訳です。**正典は英語版の
> [CONTRIBUTING.md](CONTRIBUTING.md)** です；内容が食い違う場合は英語版が優先されます。
> メンテナー向けの自動化スクリプト（`scripts/review_pr.py`、`scripts/contributor.py`）
> といったより深い内容は英語版を参照してください。

## はじめに

1. リポジトリをフォークする
2. 自分のフォークをクローンする
3. 変更用のブランチを作る
4. 変更を加える
5. テストを実行する
6. プルリクエストを送る

### 開発環境のセットアップ

```bash
git clone https://github.com/YOUR_USERNAME/critique.git
cd critique
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
cd backend
uvicorn app.main:app --reload
```

http://127.0.0.1:8000 を開いてください。ローカルの閲覧に認証プロバイダの設定は
不要です —— 変更がログイン後のフローを伴う場合は
[docs/github-oauth-setup.md](docs/github-oauth-setup.md) を参照してください。

### テストの実行

```bash
cd backend
python -m pytest tests/ -q
```

期待値：**pytest passes**。まず [Node.js](https://nodejs.org) をインストールしてください ——
フロントエンドのレンダリングテストは `node` が PATH 上にあることを必要とし、
無いとスキップされます。

新しいフロントエンドレンダリングテストモジュールを追加する場合は、次のモジュールレベルの `pytestmark` をコピーしてください：

```python
pytestmark = [
    pytest.mark.frontend_render,
    pytest.mark.skipif(
        shutil.which("node") is None,
        reason="node is required to run the frontend rendering harness",
    ),
]
```

CI の collection guard は `frontend_render` マーカーを使用してフロントエンドレンダリングテストを識別します。CI で `node` が見つからず、マークされたレンダリングテストがスキップされる場合、CI は失敗します。マーカーがないモジュールは、現在のところ自動的には検出されません（[#154](https://github.com/BistaDinesh03/critique/issues/154) を参照してください）。

ローカルでフロントエンドレンダリングテストだけを実行するには：

```bash
python -m pytest tests/ -m frontend_render -q
```

より速いフィードバックが欲しい場合は、単一のテストファイル、特定のテスト関数、
またはキーワードで絞り込めます：

```bash
python -m pytest tests/test_main.py -q
python -m pytest tests/test_main.py::test_health_check -q
python -m pytest tests/ -q -k health_check
```

## 開発ガイドライン

### シンプルを保つ

Critique は意図的に複雑さを避けます。何かを足す前に自問してください：

- これは本当に問題を解決するのか？
- 依存を減らして実現できないか？
- V1 で必要なのか？

### コードスタイル

- 既存のパターンに従う
- 意味のある名前を使う
- 関数を小さく保つ
- 役立つ箇所にのみコメントを書く
- 死にコードを残さない

### テスト

- 送信前にすべてのテストを実行する
- 新機能にはテストを追加する
- テストは 0 失敗で通ること

### プルリクエスト

- PR は集中させ、小さく保つ
- 何を、なぜ変えたかを説明する
- 関連する issue をリンクする
- 要慮深く、辛抱強くあること

## 何か探す

[`good first issue`](https://github.com/BistaDinesh03/critique/labels/good%20first%20issue)
ラベルの付いたオープンな issue は良い出発点です。コードベースや方針について質問が
ありますか？始める前に [issue #1](https://github.com/BistaDinesh03/critique/issues/1) で
尋ねてください —— 小さな質問でも歓迎します。

issue は領域別にもラベル付けされています —— `frontend`、`backend`、`tests`、
`accessibility`、`security`、`performance` —— ですから、自分の知見に合った仕事に
絞ることも、意図的に新しい領域に挑戦することもできます。

レビュー済みの厳選された 50 個の issue 計画は
[docs/issue-roadmap.md](docs/issue-roadmap.md) にあります。それぞれに難易度、
解決する問題、触れるファイルが書かれています。具体的なことを探しているなら、
そこから始めてください。

## Critique での協力のしかた

Critique は、作り手がひとつの質問を投げ、他の人がそれに答えるサイトです。
コントリビューターには、他の人が自分の製品を使うのと同じように製品を使うことを
お願いしています —— これがプロジェクトの目的を理解する最速の方法です。

典型的なコード貢献の場合：

1. **Issue を主張する。** その issue に取り組むつもりだとコメントで伝えてください。
   二人が同じ作業をするのを防ぎ、方針の見直しが必要ならメンテナーが早くから
   助言できます。
2. **Critique を一度使う。** ひとつの質問を添えてプロジェクトを投稿するか、他の人の
   プロジェクトに有用なフィードバックを送ってください。監査ではありません ——
   最初のプルリクエストを、コードだけでなく製品から得た理解に裏づけてもらうためです。
3. **フォークしてブランチを作る。** リポジトリをフォークし、ブランチを作り、
   issue を実装します。
4. **テストし、必要なら実地で試す。** 関連するテストを実行してください。変更が
   訪問者の目に触れるものなら、Critique 自身で試し、他の作り手にも確かめて
   もらってください。
5. **プルリクエストを送る。** 何を、なぜ変えたか、どのテストを実行したかを説明
   してください。

### 例外をはっきりと

このガイドラインは意図的に軽量で、**門番ではありません**。以下には適用されません：

- **ドキュメント、アクセシビリティ、セキュリティの修正** —— こうした修正は、
   他の人と同じようにサイトを使えない人々を助けます。先に製品への参加を要求することは、
   まさに間違いぬ場所に壁を置くことになります。
- **最初の貢献** —— 一人一回の貢献で十分です。歓迎され続けるために繰り返し参加する
   よう求めることはありません。
- **バグ報告と issue のトリアージ** —— それ自体が貢献です。

参加に費用はなく、決して支払いを求められることもなく、GitHub アカウント以外の
個人情報は必要ありません。GitHub 上のどこにも、あなたがサイトを使ったことを
検証するものはなく、私たちがあなたに証明を求めることも決してありません —— この一歩は
あなたを監視するためではなく、あなたを助けるためのものです。

## コミュニケーション

- 優しく、建設的に
- 相手の意図は善意であると前提にする
- 人ではなく仕事に焦点を当てる

## セキュリティ問題の報告

脆弱性について公開の issue を開かないでください。[SECURITY.md](SECURITY.md) に
記された非公開の手順に従ってください（同文書はプロジェクトのセキュリティ関連の挙動も
記録しています）。脆弱性以外のことは、[issue #1](https://github.com/BistaDinesh03/critique/issues/1)
で尋ねるのが良いでしょう。

## ライセンス

コントリビュートすることで、あなたの作品が MIT ライセンスの下でライセンスされることに
同意したことになります。
