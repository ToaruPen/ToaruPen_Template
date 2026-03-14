# Harness Kernel Design

Status: draft
Updated: 2026-03-14

## 1. この文書の目的

このリポジトリでは、特定ベンダー向けの設定ファイルを先に増やすのではなく、
どのコーディングエージェントにも投影できる vendor-agnostic な
`Harness Kernel` を正本として設計する。

今回の目的は実装開始ではなく、既存のハーネスエンジニアリング知見を確認し、
このリポジトリで採用する前提・境界・初手の順序を明確にすることにある。

## 2. 現時点で確認できた事実

この設計整理の着手時点では、このリポジトリ `/Users/toarupen/Dev/template` に
`.DS_Store` 以外の実質的な設計資産は存在せず、`AGENTS.md`、`README.md`、`docs/`、
`plans/`、`harness/` などの既存ルールや構成も存在しなかった。
したがって、この設計作業は既存規約への追従ではなく、初期方針の確定として始まった。

また、一次情報として次の傾向を確認した。

- OpenAI Codex は layered な `AGENTS.md`、`PLANS.md`、Skills、MCP を持つ。
- Anthropic Claude Code は hooks、subagents、settings scope を持つ。
- Cursor は Rules、Skills、Hooks、Plan Mode、dynamic context discovery を持つ。
- MCP は open protocol であり、tools / prompts / resources を標準化する。
- GitHub Copilot coding agent は `AGENTS.md` の custom instructions をサポートする。

ここまでが観測事実である。

ここから先は、この repo で採用する設計判断として扱う。
各製品は surface は揃っていないが、
instructions / tools / context / verification / extensibility という観点では
共通 capability に射影しやすい、ということである。

## 3. この要約で妥当だった主張

上記のまとめの中核主張は妥当である。

### 3.1 vendor file ではなく capability を中心に据える

`AGENTS.md`、`.claude/`、`.cursor/` のような vendor 固有 surface は、
正本ではなく projection として扱うのがよい。

理由は二つある。

1. 各社とも instructions、plans、skills、hooks、MCP、permissions のような
   近い概念を持つが、表現形式は一致していない。
2. surface は変化しやすい一方で、repo 内の capability vocabulary の方が変更管理しやすい。

したがって、このリポジトリでは vendor adapter より前に、
共通 capability vocabulary を定義する方針を採用する。

### 3.2 kernel は model prompt ではなく control plane を担う

kernel の責務は、モデルごとのプロンプト最適化ではなく、
以下の control plane を repo の正本として持つことにある。

- context
- policy
- verification
- review
- trace
- rollout order

これは OpenAI の `AGENTS.md` / `PLANS.md` の運用や、
Cursor の dynamic context discovery と整合しうる。

### 3.3 static context を薄くし dynamic context を前提にする

always-on context を巨大化させると腐りやすく、token 効率も悪い。
このため、常時注入する指示は pointer / map に寄せ、
詳細は skill、plan、ADR、review spec、context index から都度引く設計を採る。

### 3.4 verification と rules を first-class artifact として持つ

docs だけでは一貫性を維持しにくい。
そのため、将来的な kernel では `rules` と `oracles` を
独立 artifact として持つ、というこの repo の設計仮説は妥当である。

## 4. そのまま採用せず、慎重に言い換えるべき点

今回のまとめは方向性として強いが、初期設計メモでは次の点を明確に弱める。

### 4.1 「普遍性」は surface の統一ではない

普遍性とは、全エージェントで完全に同じ UX を実現することではない。
意味するのは、共通 capability に射影し、不足を repo 側の運用や
補助機構で補完する余地を残すことである。

### 4.2 vendor support の差分は capability matrix で扱う

`native / emulated / unsupported` の三値評価を前提にする。
つまり、すべてを native に載せる前提ではなく、
projection ごとに不足を明示する設計が必要である。

### 4.3 Copilot については instruction support は確認済みだが、
全 capability を同列に置くには追加確認が必要

今回の確認で `AGENTS.md` 対応は確認できたが、
custom agents や MCP の扱いは adapter 設計前に別途 matrix へ切り出して確認する。

### 4.4 初手から full kernel を実装しない

この repo はまだ空である。したがって、最初の成果物は framework 実装ではなく、
語彙、責務分離、段階的 rollout を定義した設計文書で十分である。

## 5. このリポジトリで採用する中核方針

### 5.1 Source of Truth の分離

SoT は次の 3 層に分ける。

1. Product SoT
   - 将来の `src/`, `schemas/`, `tests/`, `examples/` など
   - 製品やライブラリの振る舞いそのものの正本

2. Workflow SoT
   - `harness/`, `plans/`, `docs/adr/`, `review` など
   - 人と agent がどう作業するかの正本

3. Runtime Artifacts
   - `progress`, `traces`, `reports`, `eval-results` など
   - セッション継続と検証ログのための副生成物

この分離により、説明文書が product spec を侵食することを防ぐ。

### 5.2 共通 capability vocabulary

初版では、少なくとも次の項目を kernel vocabulary として持つ。

- `instructions`
- `plans`
- `skills`
- `hooks`
- `subagents`
- `mcp_tools`
- `approvals`
- `sandbox`
- `traces`
- `background_jobs`
- `review`
- `oracles`

以後の adapter は、この語彙から各 vendor surface へ射影する。

### 5.3 projection は leaf adapter として扱う

以下は正本ではなく生成対象、または派生対象とする。

- `AGENTS.md`
- `CLAUDE.md`
- `.claude/settings.json`
- `.cursor/rules/*`
- 各種 hooks / skill / agent definition

つまり「最初に vendor file を書く」のではなく、
「kernel から必要な vendor file を派生させる」順序を採る。

### 5.4 dynamic context discovery を前提にする

常時読み込ませる文書は短く保つ。
長い context、長い command 出力、長い MCP response は file 化し、
必要時に検索・参照する方針を標準にする。

### 5.5 rules と oracles を documentation の外へ押し出す

ルールは長文の説明ではなく、最終的には machine-checkable な artifact へ昇格させる。
oracle は後付けのテストメモではなく、repo type ごとの検証パックとして扱う。

## 6. 初版の kernel イメージ

まだ作成しないが、正本の最小構成の例として次を想定する。

```text
harness/
  manifest.yaml
  capability-profile.yaml
  policy.yaml
  context-index.yaml
  rules.yaml
  oracles.yaml
  review.yaml
  compatibility-matrix.yaml
  projections/
```

ただし、この時点で重要なのはファイルを増やすことではなく、
それぞれの責務を混ぜないことである。

- `manifest`: この repo が何を作るか
- `capability-profile`: この repo で必要な capability
- `policy`: 許可・禁止・承認条件
- `context-index`: どこを見れば durable context が取れるか
- `rules`: custom lint / structural rule の正本
- `oracles`: 検証パックの定義
- `review`: review 入力と観点
- `compatibility-matrix`: vendor ごとの native / emulated / unsupported
- `projections`: vendor surface への射影契約

## 7. 共通 agent loop の初期方針

将来の実装 loop は次を基本とする。

`Plan -> Execute -> Critique -> Oracle -> Gate -> Learn`

ただし、現段階では loop 実装よりも、
各段階で何を artifact 化するかの定義が先である。

- Plan: Goal / Context / Constraints / DoneWhen
- Execute: slice-based な実装
- Critique: 反証、過剰変更、境界逸脱の検査
- Oracle: lint / tests / browser / security / perf などの独立検証
- Gate: 高影響操作のみ人間承認
- Learn: 再発した失敗を rule / ADR / review spec へ昇格

## 8. ADR の扱い

ADR は product specification の正本にしない。
役割は decision log に限定する。

特に次のような判断だけを ADR 化する。

- 境界の追加や変更
- 依存導入 / 置換
- error policy の変更
- fallback 戦略の導入
- public API / schema / migration の互換性判断
- auth / payment / privacy / security の例外
- perf budget の変更

## 9. このリポジトリでの初期 rollout

最初から全 vendor adapter を作らない。順序は以下とする。

### Phase 0: 設計整理

- この `DESIGN.md` を正本として置く
- capability vocabulary を固定する
- 強い主張と慎重に扱う主張を分ける

### Phase 1: kernel の最小 artifact 定義

- `harness/capabilities.schema.json`
- `harness/compatibility-matrix.yaml`
- `harness/policy.yaml`
- `harness/rules.yaml`
- `harness/oracles.yaml`

### Phase 2: repo-side runtime / wrapper 候補

- before / after interception
- approval gate
- trace collection
- long output file 化
- progress / report 更新

### Phase 3: first adapters

- OpenAI / Claude Code のような 2 系統から開始
- Cursor / Copilot などは matrix を育ててから追加

## 10. 今の時点での結論

このまとめは、方向性としてかなり良い。
特に「vendor file を正本にしない」「capability を中心に据える」
「static context を薄くし dynamic context を前提にする」
「rules / oracles / review を独立 artifact として持つ」という軸は、
このリポジトリの初期方針として採用してよい。

一方で、今すぐ full framework を実装するのは早い。
この repo は空の状態から始まったため、まず capability vocabulary と rollout order を
文書で固定し、その後に最小 schema と matrix を作る順序が最も安全だった。

## 11. 次に作るべきもの

初版として次は完了済みである。

1. `harness/capabilities.schema.json` の初版
2. `harness/compatibility-matrix.yaml` の partial draft
3. `harness/policy.yaml` / `harness/rules.yaml` / `harness/oracles.yaml` の雛形
4. `harness/manifest.yaml` と `harness/capability-profile.yaml`
5. `harness/projections/openai-agents.yaml` と projection 規約
6. `harness/context-index.yaml` と `harness/review.yaml`
7. 最初の `AGENTS.md` leaf adapter
8. `CLAUDE.md` を `AGENTS.md` へ向ける symlink adapter

次の実作業は、以下の順で進める。

1. `harness/compatibility-matrix.yaml` の coverage を広げる
2. projection spec と leaf adapter の同期方法を安定化する
3. symlink で共有できない leaf adapter 候補を 1 つずつ追加する

引き続き vendor adapter はまだ増やしすぎない。
adapter は matrix と policy の裏付けができてから着手する。

## 12. 参照した一次情報

- OpenAI Developers: Custom instructions with AGENTS.md
  https://developers.openai.com/codex/guides/agents-md/
- OpenAI Cookbook: Using PLANS.md for multi-hour problem solving
  https://developers.openai.com/cookbook/articles/codex_exec_plans/
- OpenAI Developers: Best practices
  https://developers.openai.com/codex/learn/best-practices/
- Anthropic Claude Code Docs: Hooks reference
  https://docs.anthropic.com/en/docs/claude-code/hooks
- Anthropic Claude Code Docs: Create custom subagents
  https://docs.anthropic.com/en/docs/claude-code/subagents
- Anthropic Claude Code Docs: Claude Code settings
  https://docs.anthropic.com/en/docs/claude-code/settings
- Cursor Blog: Best practices for coding with agents
  https://cursor.com/blog/agent-best-practices
- Cursor Blog: Dynamic context discovery
  https://cursor.com/blog/dynamic-context-discovery
- Cursor Blog: Hooks for security and platform teams
  https://cursor.com/blog/hooks-partners
- Model Context Protocol Specification
  https://modelcontextprotocol.io/specification/2025-11-25
- GitHub Changelog: Copilot coding agent now supports AGENTS.md custom instructions
  https://github.blog/changelog/2025-08-28-copilot-coding-agent-now-supports-agents-md-custom-instructions/
