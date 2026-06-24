# auto_coder アーキテクチャ壁打ち

日時: 2026-06-17T16:19:10.849532
model: gpt-5.4
usage: {"prompt_tokens": 941, "completion_tokens": 5030, "total_tokens": 5971, "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 8, "audio_tokens": 0, "accepted_prediction_tokens": 0, "rejected_prediction_tokens": 0}}

---

結論：**この方針で十分実装可能です。CLI 代替として成立します。**  
ただし、**「Claude Code CLI の完全再現」を狙うのではなく、SES業務で必要な最小自動実装エージェントとして割り切る**のが成功条件です。  
来週月曜までのMVPなら、**Anthropic Messages API + 自前 tool loop + 既存 task_auto_runner を活かすアダプタ方式**が最短です。

以下、設計レビューを結論ファーストで整理します。

---

# 1. このアーキテクチャで CLI 代替として十分か?

## 結論
**十分です。むしろ今の要件には CLI より適しています。**

理由は3つです。

1. **停止要因だった承認UI依存を排除できる**
   - Claude Code CLI は対話承認前提に寄っている
   - API直叩き + 自前ツール実行なら完全自動化できる

2. **task_auto_runner の既存運用に自然に載る**
   - `pending_tasks/` を拾う
   - 実装する
   - 終了後 `done/` へ
   - 失敗時 `blocked_tasks/`
   - 既存の再試行やスキャン周期も維持可能

3. **安全制御とコスト制御を自前で持てる**
   - CostGuard
   - 実行コマンド allowlist
   - 書き込み範囲制限
   - ターン数/コスト/時間上限

---

## ただし前提
**CLIのような高度な開発体験は最初から求めないこと。**

MVPで必要なのは以下だけです。

- 指示書を読む
- リポジトリを調査する
- ファイルを編集する
- テストを走らせる
- 失敗したらログを見て再修正する
- 完了メッセージを返す

この範囲なら十分現実的です。

---

# 2. tool use ループ実装の注意点・エッジケース

## 結論
最大の論点は **「無限ループ防止」「ツール実行の決定性」「コンテキスト肥大化」** です。

以下を必須で入れてください。

---

## A. 無限ループ防止

### 必須対策
- **最大ターン数**: 20〜30で十分、MVPは 25 推奨
- **同一ツール呼び出しの連続検知**
  - 同じ `read_file(path)` を何度も繰り返す
  - 同じ `edit_file` を失敗し続ける
- **進捗なし判定**
  - 直近Nターンでファイル変更なし
  - テスト結果が改善していない
- **最終回答強制**
  - あるターン数到達時に system/tool_result で「結論を出せ」と促す

### 実装例
- `turn_count >= 25` → 打ち切り
- `same_tool_signature >= 3` → 打ち切り
- `file_write_count == 0 and turn_count >= 8` → 異常終了寄り

---

## B. ツール呼び出し失敗時の扱い

### よくある失敗
- `edit_file` の `old_str` が一致しない
- Windowsパス区切り問題
- ファイルエンコーディング問題
- コマンドタイムアウト
- `pytest` が環境未整備で落ちる

### 必須ルール
ツール失敗を**例外で落とさず、tool_result としてモデルへ返す**こと。

例:
```json
{
  "ok": false,
  "error": "old_str not found in file",
  "path": "app/main.py"
}
```

これでモデルが次の手を考えられます。

---

## C. コンテキスト肥大化

Messages API で一番危険なのは、**毎回巨大なファイル内容やテスト出力を会話に積み続けること**です。

### 対策
- `read_file` はサイズ上限を設ける
  - 例: 50KB まで全文
  - それ以上は先頭/末尾 or chunk 対応
- `run_command` の出力はトリミング
  - 例: 20KB上限
- 大きなディレクトリ一覧も制限
  - 例: 200件まで
- `search_files` も最大ヒット数制限
  - 例: 100件

### 推奨
tool_result に
- `truncated: true`
- `total_bytes`
- `shown_bytes`
を含める

---

## D. 完了判定

`"IMPL_COMPLETE"` の文字列判定だけに依存するのは危険です。

### 推奨判定
優先順位をこうしてください。

1. **モデルが最終テキストで `IMPL_COMPLETE` を返す**
2. **stop_reason=end_turn かつ直前ターンで実ファイル更新あり**
3. **stop_reason=end_turn かつ完了サマリあり**
4. それ以外は未完了扱い

### さらに良い方法
最終出力をJSON風に固定する。

例:
```text
IMPL_COMPLETE
STATUS: success
SUMMARY:
- 変更点1
- 変更点2
TEST:
- pytest tests/test_x.py passed
```

---

## E. ツールの冪等性・競合

5分スキャン運用だと、同一タスクの重複実行や途中中断再開が起こりえます。

### 必須
- タスク開始時に `.lock` または `in_progress/` へ移す
- 同一タスクを二重起動しない
- タスクごとの work log を残す

---

## F. run_command の危険性

最も危険です。  
MVPでは **最小 allowlist + 引数制限 + cwd固定** にしてください。

### 推奨
許可する実行コマンドは最初これだけ:
- `python`
- `pytest`
- `git status`
- `git diff`

**`pip` はMVPでは外した方が安全**です。  
依存追加は破壊力が高く、環境差異も大きいです。

---

# 3. system prompt 設計: CLAUDE.md を読ませる vs 直接埋め込み

## 結論
**MVPは「system prompt に必要最小限を直接埋め込み」一択です。**  
`CLAUDE.md` を都度読ませる方式は、後で拡張すればよいです。

---

## 理由
`CLAUDE.md` 読み込み方式は柔軟ですが、MVPでは次の問題があります。

- 毎回読ませるとトークン増
- 読み忘れ/解釈ブレが起こる
- ファイルが肥大化すると無駄が多い

---

## MVP推奨構成

### system prompt に固定で埋め込むもの
- あなたは自動コーディングエージェント
- 作業ディレクトリは `ses_work`
- 必ず既存コードを読んでから編集
- 最小変更を優先
- 書き込みはツール経由のみ
- テスト可能なら実行
- 失敗時は原因をログから特定
- 完了時は `IMPL_COMPLETE` を返す
- 不明点があっても停止せず、合理的仮定で前進
- 破壊的変更禁止
- 日本語で要約

### user prompt に入れるもの
- 指示書本文
- タスクID
- 対象プロジェクトパス
- 期待成果物
- 成功条件

---

## 将来拡張
後でこうすると良いです。

- system prompt: 固定ルール
- `CLAUDE.md`: リポジトリ固有規約
- 必要なら agent が `read_file("CLAUDE.md")` する

つまり、**規約本体を system に埋め込むのではなく、まず system で「必要なら CLAUDE.md を読め」と教える**形です。

---

# 4. task_auto_runner / claude_invoker.py は全面書き換えか、アダプタ方式か

## 結論
**アダプタ方式にしてください。全面書き換えは不要です。**

最短・安全な構成はこうです。

---

## 推奨構成

### 既存維持
- `task_auto_runner.py`
  - 5分スキャン
  - pending → 実行
  - 3回リトライ
  - blocked 退避
  - done へ移動

### 差し替え
- `claude_invoker.py`
  - 旧: Claude Code CLI 呼び出し
  - 新: `agentic_coder.py` 呼び出しの薄いアダプタ

---

## 役割分離

### `task_auto_runner.py`
- タスク発見
- 実行状態管理
- retry制御
- ファイル移動
- ログ保存

### `claude_invoker.py`
- 共通インターフェース維持
- `invoke(task_path, worktree_path, ...) -> Result`
- 将来 CLI に戻す/他LLMへ差し替える余地を残す

### `agentic_coder.py`
- Anthropic API 呼び出し
- tool loop
- CostGuard integration
- 実ファイル編集
- コマンド実行
- 完了判定

---

## Result オブジェクト例
```python
@dataclass
class InvokeResult:
    success: bool
    status: str  # success / retryable_error / fatal_error
    summary: str
    turns: int
    cost_usd: float
    files_changed: list[str]
    test_summary: str | None
    raw_output: str
```

この形なら runner 側をほぼ変えずに済みます。

---

# 5. 見落としている必須機能・リスク

## 結論
見落としやすいが必須なのは、**監査ログ、差分可視化、文字コード、部分編集戦略、タスクの再現性**です。

---

## A. 監査ログ
後で「なぜこの変更になったか」を追えないと運用崩壊します。

### 必須保存
タスクごとに `logs/auto_coder/{task_id}/` を作り、以下を保存:
- 指示書コピー
- 各API request/response の要約
- tool call 履歴
- run_command 出力
- 変更ファイル一覧
- 最終サマリ
- コスト情報

**生の全文レスポンスはサイズに注意**しつつ必要最低限保存。

---

## B. 差分の取得
done 移動前に差分を取るべきです。

### 推奨
- `git diff -- .`
- もしくは変更ファイルの before/after ハッシュ記録

Cursor 手動運用時との比較やレビューがしやすくなります。

---

## C. 文字コード/改行
Windows 環境なのでここは重要です。

### 必須
- UTF-8 読み書き基本
- 失敗時は `utf-8-sig`, `cp932` を試す
- 改行コードは元ファイルを維持
  - CRLF / LF を壊さない

---

## D. edit_file の戦略
`old_str -> new_str` 置換だけだと脆いです。

### 最低限必要
- 一致件数が0なら失敗
- 一致件数が複数なら失敗
- 失敗時は read_file を再度使ってモデルに再判断させる

### 将来的には
- 行番号指定編集
- unified diff 適用
- ASTベース編集
があると強くなります

ただしMVPは不要です。

---

## E. テスト戦略
「pytest 実行」を過信しないこと。

### 現実的には
- プロジェクトによって pytest がない
- 重い
- 環境依存
- DB/外部APIが必要

### MVP方針
`run_command` は次の順で試すとよいです。
1. 指示書に明示された確認コマンド
2. `pytest -q`（存在する場合のみ）
3. `python -m py_compile ...` 的な軽量確認
4. テスト不能ならその旨を最終報告

---

## F. Git汚染
既に作業ツリーが汚れていると事故ります。

### 最低限
タスク開始前に `git status --short` を取る  
done ログに保存する

### 理想
- タスクごとに git worktree / 別コピー
- ただし月曜MVPには重い

---

## G. API障害/レート制限
Anthropic API の一時障害に備える必要があります。

### 必須
- exponential backoff
- 429/5xx リトライ
- ただしタスク全体の時間上限内

---

# 6. 来週月曜までに動かす最小 MVP 範囲

## 結論
**機能を絞れば十分間に合います。**  
MVPは「安全に1タスクを最後まで自動実装できる最小線」に寄せるべきです。

---

## MVPで入れるべきもの

### 必須機能
1. `pending_tasks/*.md` を拾う
2. Anthropic Messages API で tool loop
3. ツールは以下のみ
   - `read_file`
   - `write_file`
   - `edit_file`
   - `list_directory`
   - `search_files`
   - `run_command`
4. CostGuard integration
5. 書込パス制限
6. run_command allowlist
7. 最大ターン数
8. タスク時間上限
9. ログ保存
10. 完了後 `done/` 移動、失敗時 retry / blocked

---

## MVPで削るべきもの
- `pip install` 自動実行
- CLAUDE.md 動的読み込み
- 複数プロジェクト横断最適化
- 高度な差分適用
- 長文コンテキスト圧縮
- 自動ブランチ作成
- 並列実行
- 人間承認フロー

---

# 推奨MVP設計

## ファイル構成
```text
ses_work/
  task_auto_runner.py
  claude_invoker.py
  agentic_coder.py
  tools/
    fs_tools.py
    command_tools.py
  pending_tasks/
  done/
  blocked_tasks/
  logs/
```

---

## 処理フロー
```text
task_auto_runner
  -> pending task 検知
  -> claude_invoker.invoke(task)
      -> agentic_coder.run_task(task_markdown, repo_path)
          -> system prompt 構築
          -> messages.create(tools=...)
          -> tool_use loop
          -> 完了/失敗判定
          -> Result返却
  -> success なら done/
  -> retryable なら retry count 加算
  -> 3回失敗で blocked/
```

---

## system prompt 叩き台
MVPならこんな内容で十分です。

```text
あなたは ses_work 配下のコードベースを自動実装するコーディングエージェントです。

目的:
- 与えられたタスク指示書に従って、既存コードを調査し、必要最小限の変更で実装を完了すること。

行動規則:
- まず関連ファイルを探索し、理解してから編集すること。
- 変更は必ず提供されたツール経由で行うこと。
- 書き込み可能なのは ses_work 配下のみ。
- 既存の構造・命名・実装方針を尊重すること。
- 不明点があっても停止せず、合理的な仮定で前進すること。
- テストや検証コマンドが実行可能なら実行し、結果を確認すること。
- コマンド失敗や編集失敗時は、原因を分析して別の方法を試すこと。
- 大きな破壊的変更は避けること。
- タスク完了時は必ず "IMPL_COMPLETE" を含む最終メッセージを返すこと。
- 最終メッセージでは、変更内容、変更ファイル、テスト結果、残課題を簡潔にまとめること。
```

---

# 実装上の具体提案

## 1. tool schema
Anthropic tool use 用に、各ツールの引数を厳格にしてください。

例:
```python
TOOLS = [
    {
        "name": "read_file",
        "description": "Read a text file within ses_work",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"}
            },
            "required": ["path"]
        }
    },
    ...
]
```

---

## 2. path validation
Windows では絶対に `Path.resolve()` ベースでチェックしてください。

```python
def ensure_within_root(root: Path, target: Path) -> Path:
    root = root.resolve()
    target = target.resolve()
    if root not in [target, *target.parents]:
        raise ValueError("Path outside root")
    return target
```

`..` 回避、シンボリックリンク考慮のため必須です。

---

## 3. run_command 実装
`shell=True` は避ける。  
`subprocess.run([...], cwd=root, timeout=...)` を使う。

### さらに
- 文字列コマンドではなく **配列引数** に寄せる
- ただしモデルに配列を作らせるのは難しいので、MVPでは文字列受け取り→安全パーサで分解でも可
- Windows なので `shlex.split(..., posix=False)` 検討

---

## 4. CostGuard 連携
各API call ごとに
- 実行前 `allowed(...)`
- 実行後 `finalize(...)`

に加えて、**タスク累積コスト**も別管理してください。

### 推奨
- 1 call 見積上限
- 1 task 実績累積上限
- 1日 ledger 上限

3層で止めると安全です。

---

## 5. モデル選定
`claude-sonnet-4-6` で問題ありません。  
MVPはこれ一本でよいです。

Haiku へのフォールバックは後回しで大丈夫です。  
今は構成複雑化の方が損です。

---

# 改修方針の最終提案

## 推奨判断
**全面書き換えしない。**
**`claude_invoker.py` を API バックエンド化する。**
**`agentic_coder.py` を新設する。**

---

## 優先度順タスクリスト

### Day 1
1. `agentic_coder.py` 骨格作成
2. Anthropic API 接続
3. tool loop 実装
4. `read/list/search/write/edit` 実装

### Day 2
5. `run_command` 実装
6. CostGuard 統合
7. ログ保存
8. task_auto_runner から invoke 接続

### Day 3
9. 失敗系ハンドリング
10. blocked/retry 連携確認
11. 実タスク1〜2件でE2E検証
12. プロンプト調整

---

# 各質問への短答

## 1. このアーキテクチャで十分か?
**はい。十分です。**  
CLI代替として実用になります。MVPはむしろこちらが正解です。

## 2. tool use ループの注意点
**無限ループ、ツール失敗の返し方、出力肥大化、完了判定、Windowsパス/文字コード**が重要です。

## 3. system prompt 設計
**MVPは直接埋め込み。**  
`CLAUDE.md` 動的読込は第2段階で十分です。

## 4. 既存改修方針
**アダプタ方式。**  
`task_auto_runner` は活かし、`claude_invoker.py` の中身を差し替えるのが最適です。

## 5. 見落とし
**監査ログ、差分記録、改行/文字コード、git汚染、run_command制限、再試行時の冪等性**です。

## 6. 最小MVP
**Anthropic API直叩き + 6ツール + CostGuard + ログ + 既存runner接続**まで。  
`pip` 自動実行や CLAUDE.md 動的読込は切ってよいです。

---

必要なら次に、  
**「agentic_coder.py のクラス設計・主要関数シグネチャ・疑似コード」** まで落として出します。
