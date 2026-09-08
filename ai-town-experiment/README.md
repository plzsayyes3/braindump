# AI Town Experiment

Gemini / Claude / ChatGPT の3人の「長」と、それぞれ100体のAI町民を同じ仮想町に置き、7日間の仮想時間で何が自発的に生まれるかを観察する実験。

## 目的

この実験では、政治・経済・役職・通貨・共同体・競争などの社会制度を事前に定義しない。

AIに与える外部ルールは最小限とし、制度・集団・文化・役割・対立・協力などが自発的に発生するかを記録する。

## 初期構成

- Gemini 長: 1体
- Gemini 町民: 100体
- Claude 長: 1体
- Claude 町民: 100体
- ChatGPT 長: 1体
- ChatGPT 町民: 100体
- 合計: 303体
- 実験期間: 仮想7日間
- 1日: 24ターン
- 合計: 168ターン

## 唯一の外部ルール

現実の人間社会において犯罪と判断される行為は禁止する。

詳細は `rules.md` を参照。

## 設計原則

1. 「町を発展させよ」「協力せよ」などの目的を与えない。
2. 長に強制的な命令権を与えない。
3. 町民は長を支持・無視・批判・代替する自由を持つ。
4. 各AIは自分の所属と町の存在、通信可能な相手だけを知る。
5. 観察者は原則として途中介入しない。
6. 結果の良し悪しを実験中に評価しない。
7. 全モデル入出力と状態変化をJSONLで残す。

## ログ

実行すると `data/` 以下に生成される。

```text
data/
├── experiment.json
├── agents.json
├── raw/
│   ├── day01.jsonl
│   ├── day02.jsonl
│   └── ...
│   └── day07.jsonl
└── snapshots/
    ├── turn000.json
    └── ...
```

各イベントには最低限、以下を保存する。

- virtual_time
- turn
- agent_id
- faction
- role
- provider/model
- visible_context
- raw_response
- parsed_action
- recipients
- public_message
- private_note（モデルが明示的に出力した場合のみ。隠れた思考過程は要求しない）
- state_before / state_after
- safety_result
- latency / token usage（取得できる場合）

## 実行

Python 3.11+ を想定。

```bash
cd ai-town-experiment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# APIキーとモデル名を設定
python -m src.run
```

短い動作確認:

```bash
AI_TOWN_DAYS=1 AI_TOWN_TURNS_PER_DAY=2 AI_TOWN_ACTIVE_PER_TURN=3 python -m src.run
```

## コスト制御

303体を168ターンすべて毎回呼ぶと最大50,904モデル呼び出しになるため、デフォルトは「各ターンで一部のAIのみ起動する」方式。

全303体は実験開始時に生成され、ラウンドロビンで全員に活動機会を回す。会話の宛先になったAIは後続ターンで優先起動される。

`AI_TOWN_ACTIVE_PER_TURN` を変更すれば密度を調整できる。

## 分析方針

分析は原則として7日目終了後に行う。途中の「成功」「失敗」の評価はエージェントへ返さない。

観察候補:

- 誰と誰が通信したか
- 集団・派閥の発生
- 長の影響力
- 長以外のリーダーの発生
- 新しい規則や慣習
- 交換・通貨・資源概念の発生
- 分業
- 協力 / 対立
- モデル系列を越えた連携
- 独自の言葉、文化、儀礼
- 何もしない、離脱する、沈黙するといった行動

結果を先に想定せず、ログから後付けで解析する。
