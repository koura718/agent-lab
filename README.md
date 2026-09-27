# AI Agent Lab

OpenAI Codex、Claude Code、OpenAI Agents SDK、MCP を利用した  
AI Agent 開発・検証用の再利用可能なスターターテンプレートです。

このリポジトリは、GitHub Template Repository として利用することを想定しています。

---

## Purpose

このテンプレートでは、主に以下の技術を検証・開発します。

- OpenAI Codex CLI
- Claude Code
- OpenAI Agents SDK
- MCP Server / MCP Client
- Python ベースの AI Agent
- Agent の Tool Calling
- AI Agent のテスト
- lint / format / validation
- GitHub Template Repository を利用した再利用可能な開発環境

将来的には、以下への拡張を想定しています。

- Function Tools の追加拡張
- MCP Tools
- Structured Output
- Tracing
- Retry / Timeout
- Application Logging
- Integration Tests
- GitHub Actions CI
- 複数 Agent 構成
- 外部 API / DB 連携

---

## Environment

現在の基準環境です。

| Component | Version |
|---|---:|
| OS | Ubuntu 24.04 |
| Node.js | 24.21.0 |
| pnpm | 12.3.4 |
| Python | 3.14.7 |
| uv | 0.12.12 |
| mise | 2026.9.5 |

実際に使用するランタイムバージョンは、原則として `mise.toml` を正とします。

現在の `mise.toml`:

```toml
[tools]
node = "24.21.0"
pnpm = "12.3.4"
python = "3.14.7"
uv = "0.12.12"
```

---

## Repository Structure

想定する標準構成です。

```text
agent-lab/
├── .github/
│   └── workflows/
├── docs/
│   └── architecture.md
├── scripts/
│   ├── setup.sh
│   └── validate.sh
├── src/
│   └── agent_lab/
│       ├── __init__.py
│       └── main.py
├── tests/
│   └── test_smoke.py
├── .env.example
├── .gitignore
├── AGENTS.md
├── CLAUDE.md
├── README.md
├── mise.toml
├── pyproject.toml
└── uv.lock
```

---

## Requirements

事前に以下が利用可能であることを前提とします。

- Git
- mise
- GitHub CLI
  - GitHub 操作を CLI から行う場合
- OpenAI API Key
  - OpenAI Agents SDK から実 API を呼び出す場合
- Anthropic の認証
  - Claude Code を利用する場合

Python、uv、Node.js、pnpm は、原則として `mise.toml` から導入・管理します。

OS のシステム Python を直接置き換えない方針とします。

---

## Initial Setup

リポジトリを取得します。

```bash
git clone <REPOSITORY_URL>
cd agent-lab
```

初期セットアップを実行します。

```bash
./scripts/setup.sh
```

`setup.sh` では、以下を行う想定です。

1. 必須コマンドの確認
2. `mise.toml` に定義されたツールのインストール
3. Python 依存関係の同期
4. `.env` が存在しない場合に `.env.example` から生成
5. 初期状態の validation

環境を変更せず、前提条件だけ確認する場合:

```bash
./scripts/setup.sh --check
```

---

## Manual Setup

スクリプトを使わず手動でセットアップする場合は、以下を実行します。

```bash
mise install
mise current
```

Python 依存関係を同期します。

```bash
uv sync --frozen
```

`uv.lock` がまだ存在しない初期開発時のみ:

```bash
uv sync
```

---

## Environment Variables

環境変数のテンプレートとして `.env.example` を使用します。

```env
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

実際の環境では `.env` を作成します。

```bash
cp .env.example .env
chmod 600 .env
```

`.env` に必要な値を設定します。

例:

```env
OPENAI_API_KEY=your_api_key_here
ANTHROPIC_API_KEY=
```

### Important

秘密情報は Git にコミットしません。

`.env` が Git 管理対象外になっていることを確認します。

```bash
git check-ignore -v .env
```

API Key、OAuth Token、SSH Private Key などの秘密情報を、画面・ログ・README・Issue・Pull Request に出力しないでください。

---

## Run

`.env` を現在の shell に読み込みます。

```bash
set -a
source .env
set +a
```

OpenAI Agent を実行します。

```bash
uv run python -m agent_lab.main
```

現在の最小構成では、OpenAI Agents SDK を利用してモデルを呼び出します。

動作確認済みの例:

```text
OpenAI Agents SDK は正常に動作しています。
```

---

## Function Tool（Step 3）

APIキーなしで比較できます。.envの読込みも不要です。

```bash
uv run --frozen agent-lab --compare-json '{"source":["A","B","B"],"baseline":["B","C"]}'
```

```json
{"same":["B"],"source_only":["A"],"baseline_only":["C"]}
```

同じ処理は `python -m agent_lab.main --compare-json ...` でも利用できます。
両配列は必須、各1,000要素以下、各文字列1〜256文字です。
重複を除去しソートします。大小文字・空白・Unicode表記は保持します。
不正入力はerror JSONと終了コード2を返します。ログはstderr、結果はstdoutです。

実モデルからToolを使う場合（APIキー設定・課金あり）:

```bash
uv run --frozen agent-lab --tool-mode function --prompt 'compare_listsを使いsource=["A","B"]とbaseline=["B","C"]を比較してください。'
```

モデル指定は `--model` > `AGENT_MODEL` > 明示したTOML > SDK既定値です。.envは自動読込みしません。
引数なし実行は従来のAPI接続確認を行います。
console scriptの `agent-lab` も同じ入口へ統一したため、以前の挨拶表示から動作が変わります。

[入力・Tool契約](docs/tool-contract.md) / [実行・障害対応手順](docs/runbook.md)

---

## MCP Server（Step 4）

compare_listsを別プロセスのstdio Serverで公開します。APIキーは不要です。

```bash
uv run --frozen pytest -m integration -v
```

実SDK ClientがServerを起動し、Tool一覧・比較・エラー・終了を確認します。
Function Toolと同じ比較関数・入力schemaを使用し、ログはstderrに出力します。

Server単体の起動コマンドは次のとおりです（stdinの入力待ちになります）。

```bash
uv run --frozen python -m agent_lab.mcp.server
```

[MCP Server仕様・操作手順](docs/mcp-server.md)を参照してください。

## MCP Client（Step 5）

API不要でTool一覧と比較結果を確認できます。ClientがServerを起動・終了します。

```bash
uv run --frozen agent-lab-mcp-client list-tools
uv run --frozen agent-lab-mcp-client call compare_lists \
  --arguments '{"source":["A","B","B"],"baseline":["B","C"]}'
```

Agentから同じServerを使う場合は `agent-lab --tool-mode mcp --prompt '...'` を使用します
（APIキー・課金あり）。Function Toolとの二重登録は行いません。
設定はCLI > 環境変数 > 明示したTOML > 既定値です。
[MCP Client仕様・設定・検証手順](docs/mcp-client.md)を参照してください。

---

## Validation

基本的な品質確認は、以下でまとめて実行します。

```bash
./scripts/validate.sh
```

個別に実行する場合:

```bash
uv run ruff check .
```

format 確認:

```bash
uv run ruff format --check .
```

テスト:

```bash
uv run pytest -v
```

Python ソースの compile 確認:

```bash
uv run python -m compileall -q src tests
```

Git の whitespace エラー確認:

```bash
git diff --check
```

---

CI結果の取得とmain保護設定は[CI運用手順](docs/ci.md)を参照してください。

## Development Workflow

基本的な開発フローです。

```text
Issue / Task
   ↓
README / AGENTS.md / CLAUDE.md 確認
   ↓
小さな単位で変更
   ↓
Ruff
   ↓
pytest
   ↓
validation
   ↓
git diff 確認
   ↓
commit
```

変更後は、最低限以下を実行します。

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -v
```

または:

```bash
./scripts/validate.sh
```

---

## Development Rules

このプロジェクトでは、以下を基本ルールとします。

- `README.md` をプロジェクト仕様の基準とする
- Python の依存管理には `uv` を使用する
- Node.js の依存管理には `pnpm` を使用する
- ランタイムバージョンは `mise.toml` で管理する
- 秘密情報を Git にコミットしない
- リポジトリ外のファイルを不用意に変更しない
- 小さくレビュー可能な変更を優先する
- 動作変更後はテストと lint を実行する
- 破壊的操作は実行前に影響範囲を確認する
- OS 設定変更や `sudo` を伴う処理は明示的に承認してから実行する
- グローバル依存の追加を避ける
- ローカルのプロジェクト依存を優先する
- 外部設定ファイルによる構成分離を優先する
- 失敗時には終了コードとエラー内容を明確にする

---

## Codex

OpenAI Codex CLI を開発支援 Agent として利用します。

Codex 向けの共通ルールは:

```text
AGENTS.md
```

に定義します。

基本方針:

- 最初に `README.md` を読む
- `mise.toml` を確認する
- リポジトリ外を変更しない
- 秘密情報を扱わない
- 破壊的操作を勝手に実行しない
- 小さな変更を優先する
- 変更後に validation を実行する
- 変更内容と検証結果を要約する

---

## Claude Code

Claude Code を開発支援 Agent として利用します。

Claude Code 向けのルールは:

```text
CLAUDE.md
```

に定義します。

基本方針:

- `README.md` を仕様の基準とする
- `AGENTS.md` の共通ルールにも従う
- sandbox / permissions を安全側で利用する
- リポジトリ外を不用意に変更しない
- 秘密情報を出力しない
- OS 設定変更や `sudo` 操作は事前確認する
- 変更後に lint / test / validation を行う

---

## OpenAI Agents SDK

Python では OpenAI Agents SDK を使用します。

基本構成:

```text
User
  |
  v
Agent
  |
  +-- Model
  |
  +-- Function Tools
  |
  +-- MCP Servers
  |
  +-- External APIs
```

現在は最小 Agent の実行と、OpenAI API への実通信まで確認済みです。

---

## Tests

テストは `pytest` を使用します。

smoke testに加え、compare_listsの境界条件・Function Tool登録・CLI・ScriptedModelによるTool呼出しをAPI不要で検証します。通常テストではネットワーク接続とtracingを無効化します。

```bash
uv run pytest -v
```

### Test Policy

通常のユニットテストでは、可能な限り外部 API を呼び出しません。

Step 3のunit / ScriptedModel、Step 4の実stdio Server、Step 5のAgent経由MCP統合テストを実装済みです。Step 6で両経路の一致・Server異常終了・liveゲートを追加しました。区分は以下です。

| 区分 | 対象 | 通常実行 |
|---|---|---|
| Unit | 関数・入力検証 | 実行 |
| Integration | ローカルMCPの実プロセス・stdio通信 | 実行 |
| Live | 実LLM API | 明示指定時のみ |

通常の `pytest` とCIではlive 2件をスキップします。実API検証には
`--run-live` と `OPENAI_API_KEY` / `AGENT_MODEL` の両方が必要です。
明示指定時の設定不足は終了コード4、API失敗はテスト失敗として扱います。
[テスト運用手順](docs/testing.md)に、区分別コマンド・受入条件・live実行方法を記載しています。

---

## Ruff

lint / format には Ruff を使用します。

lint:

```bash
uv run ruff check .
```

自動修正:

```bash
uv run ruff check . --fix
```

format:

```bash
uv run ruff format .
```

format 確認:

```bash
uv run ruff format --check .
```

### Import Sorting

`I001` が出た場合:

```bash
uv run ruff check . --fix
```

を実行します。

`ruff format` だけでは import sort が修正されない場合があります。

---

## GitHub Template Repository

このリポジトリは、GitHub Template Repository として利用することを想定しています。

GitHub Web UI:

```text
Repository
  ↓
Settings
  ↓
General
  ↓
Template repository
```

`Template repository` を有効化します。

新しいプロジェクトを作成する場合:

```text
Use this template
  ↓
Create a new repository
```

---

## Create a New Project

GitHub CLI からテンプレートを利用する場合:

```bash
gh repo create my-agent \
  --private \
  --template <OWNER>/agent-lab \
  --clone
```

作成後:

```bash
cd my-agent
./scripts/setup.sh
./scripts/validate.sh
```

---

## Template Customization

GitHub Template Repository はファイルをコピーしますが、プロジェクト名や Python package 名は自動置換されません。

例えば、新しいリポジトリ名を:

```text
mcp-file-agent
```

としても、初期状態の Python package は:

```text
src/agent_lab/
```

のままです。

必要に応じて、新しいプロジェクト作成後に package 名を変更します。

将来的には、以下による自動化も検討します。

- `scripts/bootstrap.sh`
- Copier
- Cookiecutter
- 独自 project generator

---

## Architecture

基本アーキテクチャ:

```text
Developer
   |
   +-- Codex
   |    └── AGENTS.md
   |
   +-- Claude Code
   |    └── CLAUDE.md
   |
   v
Repository
   |
   +-- Python
   |    └── uv
   |
   +-- Node.js
   |    └── pnpm
   |
   +-- OpenAI Agents SDK
   |
   +-- MCP
   |
   +-- Tests
   |
   └-- Validation
```

詳細は:

```text
docs/architecture.md
```

を参照します。

---

## Security

以下の情報は Git に保存しません。

- `.env`
- OpenAI API Key
- Anthropic API Key
- GitHub Token
- OAuth Token
- SSH Private Key
- Codex の認証情報
- Claude Code の認証情報
- その他 credential / secret

`.env.example` には、設定項目名だけを記載します。

```env
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

### Privileged Operations

以下の操作は特に注意します。

- `sudo`
- OS 設定変更
- AppArmor 設定変更
- Docker daemon 設定変更
- user / group 変更
- firewall 変更
- SSH 設定変更
- package manager による system-wide install
- recursive delete

必要性と影響範囲を確認してから実行します。

---

## Logging

Agent・Tool・MCPのログ設定を共通化しています。stderrに時刻・レベル・実行ID・イベント・処理時間・エラー分類を出力します。
詳細と確認手順は[Logging運用手順](docs/logging.md)を参照してください。

```text
INFO
WARN
ERROR
```

秘密情報はログへ出力しません。

ログファイルを使用する場合は、原則として:

```text
logs/
```

配下へ保存し、Git 管理対象外にします。

---

## Backup

GitHub Repository を正本として利用します。

必要に応じて `git bundle` でもバックアップします。

作成:

```bash
git bundle create agent-lab.bundle --all
```

確認:

```bash
git bundle verify agent-lab.bundle
```

復元:

```bash
git clone agent-lab.bundle agent-lab-restored
```

`.env` など Git 管理外の秘密情報は `git bundle` には含まれません。

秘密情報は別の安全な手段で管理してください。

---

## Troubleshooting

### Current mise versions

```bash
mise current
```

### mise environment check

```bash
mise doctor
```

### Python

```bash
uv run python --version
```

### Node.js

```bash
node --version
```

### pnpm

```bash
pnpm --version
```

### uv

```bash
uv --version
```

### OpenAI Agents SDK import

```bash
uv run python -c "import agents; print('agents import OK')"
```

### Ruff lint

```bash
uv run ruff check .
```

### Ruff auto-fix

```bash
uv run ruff check . --fix
```

### Ruff format

```bash
uv run ruff format .
```

### Tests

```bash
uv run pytest -v
```

---

## Validation Checklist

Template Repository の変更前後には、以下を確認します。

- [ ] `mise install` が成功する
- [ ] `mise current` が `mise.toml` と一致する
- [ ] `uv sync --frozen` が成功する
- [ ] `.env` が Git 管理対象外
- [ ] `.env.example` に秘密情報がない
- [ ] `uv run ruff check .` が成功する
- [ ] `uv run ruff format --check .` が成功する
- [ ] `uv run pytest -v` が成功する
- [ ] `git diff --check` が成功する
- [ ] OpenAI Agent の実行が成功する
- [ ] README の Setup 手順だけで再構築できる

---

## Current Status

現在、以下まで動作確認済みです。

- Ubuntu 24.04
- mise によるランタイム管理
- Node.js
- pnpm
- Python
- uv
- OpenAI Agents SDK
- Ruff
- pytest
- OpenAI API 実通信
- OpenAI Codex CLI
- Codex sandbox
- Claude Code
- Claude Code permissions / sandbox
- GitHub CLI
- GitHub SSH 認証
- Docker

現在は、AI Agent 開発用 Template Repository の基盤構築段階です。

---

## Next Steps

[Next Steps 3–6 詳細設計](docs/next-steps-3-6.md) に、入出力・構成・実装順序・受入条件をまとめています。
Step 3〜6を実装済みです。通常テストはAPI不要、実API検証は明示実行です。

| Step | 項目 | 状態 / 方針 |
|---|---|---|
| 1 | scripts/setup.sh | ファイルあり |
| 2 | scripts/validate.sh | ファイルあり |
| 3 | Function Tool | 実装済み：compare_lists、入力検証、Agent登録、API不要テスト |
| 4 | MCP Server | 実装済み：Python / stdio / 比較ロジック共有・実プロセステスト |
| 5 | MCP Client | 実装済み：診断CLI・Agent接続・設定・timeout・終了処理 |
| 6 | Integration Tests | 実装済み：経路一致・異常系・live明示ゲート・CI区分 |
| 7 | GitHub Actions | JUnit結果を14日保存・失敗時手順を整備。main保護は別設定 |
| 8 | Tracing | 後続。通常テストでは無効化する設計 |
| 9 | Application Logging | 実装済み：共通stderrログ・実行ID・処理時間・エラー分類 |
| 10 | project rename / bootstrap | scripts/bootstrap.shあり。再利用検証は別途 |

「ファイルあり」は存在確認を示し、本変更で実行検証済みという意味ではありません。

---

## License

必要に応じて、このセクションと `LICENSE` ファイルを追加してください。

