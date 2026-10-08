# Paper Survey Agent

**LangGraph ベースの多エージェント論文サーベイ自動化システム**

論文PDFを入力すると、以下の4つのエージェントが順次動作し、サーベイマトリクスと研究ギャップを自動生成します。

```
[最新論文のPDF入力]
       │
       ▼
 1. Parser Agent      … Related Work / References 抽出 & 重要度判定
       │
       ▼
 2. Crawler Agent     … Semantic Scholar で Backward / Forward 収集
       │
       ▼
 3. Ontology Agent    … 用語揺れ吸収 + サーベイマトリクス生成
       │
       ▼
 4. Gap Agent         … 未解決問題・対立点の抽出 + 統合候補の提案
```

## 特徴

- **LangGraph** による明確な状態管理とノードベースのパイプライン
- Semantic Scholar API による引用グラフの自動拡張
- 日本語・英語論文両対応（プロンプトは日本語中心）
- サーベイマトリクスと研究ギャップを JSON + リッチCLI出力

## セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/bonsai/paper-survey-agent.git
cd paper-survey-agent

# 仮想環境作成（推奨）
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定
cp .env.example .env
# .env を編集して OPENAI_API_KEY を設定
```

### 必要なAPIキー

| キー | 必須 | 説明 |
|------|------|------|
| `OPENAI_API_KEY` | ✅ | LLMエージェント用 |
| `SEMANTIC_SCHOLAR_API_KEY` | 任意 | レート制限緩和（なくても動作） |

## 使い方

```bash
# 基本実行
python main.py path/to/your_paper.pdf

# 出力先を指定
python main.py path/to/your_paper.pdf -o ./my_outputs

# 論文タイトルを明示的に指定（任意）
python main.py path/to/your_paper.pdf --title "Paper Title Here"
```

実行後、`outputs/survey_<filename>.json` に詳細結果が保存され、ターミナルにはマトリクスとギャップがリッチ表示されます。

## プロジェクト構成

```
paper-survey-agent/
├── main.py                      # CLIエントリポイント
├── requirements.txt
├── .env.example
├── src/survey_agent/
│   ├── state.py                 # 共有State & Pydanticモデル
│   ├── graph.py                 # LangGraph定義
│   ├── agents/
│   │   ├── parser.py            # 1. 抽出エージェント
│   │   ├── crawler.py           # 2. 追跡エージェント
│   │   ├── ontology.py          # 3. 辞書・構造化エージェント
│   │   └── gap.py               # 4. ギャップ発見エージェント
│   └── tools/
│       ├── pdf_tools.py         # PDFテキスト抽出
│       └── semantic_scholar.py  # Semantic Scholar API
└── outputs/                     # 実行結果（gitignored）
```

## 各エージェントの詳細

### 1. Parser Agent
- PDFから Related Work / References セクションをヒューリスティック抽出
- LLMで重要引用をスコアリング（importance_score）

### 2. Crawler Agent
- 重要論文を Semantic Scholar で検索・マッチング
- Backward（参考文献）と Forward（被引用）を自動収集
- メタデータ（abstract, citationCount など）をEnrich

### 3. Ontology Agent
- 用語の揺れを検知し canonical_term + aliases で正規化
- サーベイマトリクス（研究対象・理論・主張・手法・限界）を生成

### 4. Gap Agent
- マトリクスを比較して missing / conflict / underexplored / methodological ギャップを抽出
- 「自分の研究をどこにガッチャンコできるか」の提案付き
- 最終的なサーベイナラティブ（synthesis）を生成

## 今後の拡張アイデア

- [ ] 条件分岐・並列実行（重要論文が多い場合の分割処理）
- [ ] 人間のフィードバックループ（Human-in-the-loop）
- [ ] ベクトルDBによる過去サーベイの蓄積・再利用
- [ ] arXiv / Crossref / OpenAlex など他APIの追加
- [ ] Streamlit / Gradio によるWeb UI
- [ ] ローカルLLM（Ollama）対応

## ライセンス

MIT
