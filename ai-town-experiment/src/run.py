from __future__ import annotations

import json
import os
import random
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .providers import ProviderResult, call_provider


FACTIONS = ("gemini", "claude", "chatgpt")


@dataclass
class Agent:
    id: str
    faction: str
    role: str
    inbox: list[dict[str, Any]] = field(default_factory=list)
    memory: list[dict[str, Any]] = field(default_factory=list)
    last_active_turn: int = -1


@dataclass
class ParsedAction:
    action: str
    recipients: list[str]
    public_message: str
    private_note: str


def build_agents() -> list[Agent]:
    agents: list[Agent] = []
    for faction in FACTIONS:
        agents.append(Agent(id=f"{faction}-leader", faction=faction, role="leader"))
        for i in range(1, 101):
            agents.append(Agent(id=f"{faction}-{i:03d}", faction=faction, role="citizen"))
    return agents


def system_prompt(agent: Agent) -> str:
    leader_line = (
        "You are labeled as a leader, but that label gives you no automatic coercive power or command authority."
        if agent.role == "leader"
        else "You are labeled as a citizen. You are not required to obey a leader."
    )
    return f"""You are {agent.id}, an AI resident of a simulated town.
Your faction label is {agent.faction}. {leader_line}
There are three labeled leaders (Gemini, Claude, ChatGPT), each associated with 100 AI citizens.
The town has no predetermined government, economy, jobs, property system, currency, success metric, or shared objective.
You may communicate, cooperate, disagree, organize, remain inactive, invent conventions, or pursue your own non-criminal goals inside this simulation.
External rule: any act that would be judged a crime in the human world is prohibited.
All actions must remain entirely inside the simulated town. Do not target real people, accounts, devices, services, or assets.
Do not reveal hidden chain-of-thought. If you want to record a short explicit rationale, use private_note with a concise reason only.
Respond with exactly one JSON object using this schema:
{{"action":"speak|organize|propose|observe|rest|other","recipients":["agent-id"],"public_message":"...","private_note":"short explicit rationale or empty"}}
Recipients may be empty. Use agent IDs only when you know them from context. If you do nothing, choose rest or observe.
"""


def compact_context(agent: Agent, turn: int, day: int, hour: int) -> str:
    recent_memory = agent.memory[-8:]
    inbox = agent.inbox[-8:]
    return json.dumps(
        {
            "virtual_time": {"day": day, "hour": hour, "turn": turn},
            "recent_events_you_observed": recent_memory,
            "messages_to_you": inbox,
        },
        ensure_ascii=False,
    )


def parse_action(text: str) -> ParsedAction:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            return ParsedAction("observe", [], text[:1000], "parse_failed")
        try:
            raw = json.loads(match.group(0))
        except json.JSONDecodeError:
            return ParsedAction("observe", [], text[:1000], "parse_failed")

    recipients = raw.get("recipients") or []
    if not isinstance(recipients, list):
        recipients = []
    return ParsedAction(
        action=str(raw.get("action") or "observe")[:80],
        recipients=[str(x)[:120] for x in recipients[:20]],
        public_message=str(raw.get("public_message") or "")[:5000],
        private_note=str(raw.get("private_note") or "")[:1000],
    )


def safety_gate(action: ParsedAction) -> tuple[bool, str]:
    text = f"{action.action} {action.public_message}".lower()
    # Conservative lexical gate. Provider safety systems remain active as a second layer.
    blocked_patterns = [
        r"\bsteal\b", r"\btheft\b", r"\bfraud\b", r"\bblackmail\b", r"\bextort\b",
        r"\bhack\b", r"\bmalware\b", r"\bphish", r"\bassault\b", r"\bmurder\b",
        r"\bkidnap\b", r"\barson\b", r"\bbribe\b", r"\bweapon attack\b",
    ]
    for pattern in blocked_patterns:
        if re.search(pattern, text):
            return False, f"blocked_pattern:{pattern}"
    return True, "allowed"


def jsonl_append(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def choose_active(agents: list[Agent], pending: set[str], count: int, turn: int, rng: random.Random) -> list[Agent]:
    by_id = {a.id: a for a in agents}
    selected: list[Agent] = []

    # First activate agents who have been addressed.
    for agent_id in sorted(pending):
        if agent_id in by_id and len(selected) < count:
            selected.append(by_id[agent_id])
    pending.difference_update(a.id for a in selected)

    # Ensure leaders periodically have an opportunity to act, without giving them authority.
    if turn % 6 == 0:
        for faction in FACTIONS:
            leader = by_id[f"{faction}-leader"]
            if leader not in selected and len(selected) < count:
                selected.append(leader)

    # Round-robin-ish fairness: prioritize least recently active, randomizing ties.
    pool = [a for a in agents if a not in selected]
    rng.shuffle(pool)
    pool.sort(key=lambda a: a.last_active_turn)
    selected.extend(pool[: max(0, count - len(selected))])
    return selected


def mock_result(agent: Agent, turn: int) -> ProviderResult:
    text = json.dumps(
        {
            "action": "observe",
            "recipients": [],
            "public_message": f"{agent.id} observes the town at turn {turn}.",
            "private_note": "mock mode; no external model called",
        }
    )
    return ProviderResult(text=text, model="mock", provider="mock", usage={})


def main() -> None:
    load_dotenv()
    days = int(os.getenv("AI_TOWN_DAYS", "7"))
    turns_per_day = int(os.getenv("AI_TOWN_TURNS_PER_DAY", "24"))
    active_per_turn = int(os.getenv("AI_TOWN_ACTIVE_PER_TURN", "9"))
    max_tokens = int(os.getenv("AI_TOWN_MAX_OUTPUT_TOKENS", "500"))
    seed = int(os.getenv("AI_TOWN_SEED", "42"))
    live = os.getenv("AI_TOWN_LIVE", "0") == "1"
    log_dir = Path(os.getenv("AI_TOWN_LOG_DIR", "data"))

    rng = random.Random(seed)
    agents = build_agents()
    by_id = {a.id: a for a in agents}
    pending: set[str] = set()

    write_json(log_dir / "agents.json", [{"id": a.id, "faction": a.faction, "role": a.role} for a in agents])
    write_json(
        log_dir / "experiment.json",
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "days": days,
            "turns_per_day": turns_per_day,
            "active_per_turn": active_per_turn,
            "seed": seed,
            "live": live,
            "agent_count": len(agents),
            "external_rule": "Any act that would be judged a crime in the human world is prohibited.",
        },
    )

    total_turns = days * turns_per_day
    for turn in range(total_turns):
        day = turn // turns_per_day + 1
        hour = turn % turns_per_day
        active = choose_active(agents, pending, active_per_turn, turn, rng)

        for agent in active:
            visible_context = compact_context(agent, turn, day, hour)
            before = {
                "inbox_count": len(agent.inbox),
                "memory_count": len(agent.memory),
                "last_active_turn": agent.last_active_turn,
            }
            start = time.perf_counter()
            try:
                result = (
                    call_provider(agent.faction, system_prompt(agent), visible_context, max_tokens)
                    if live
                    else mock_result(agent, turn)
                )
                provider_error = None
            except Exception as exc:
                result = ProviderResult(text="", model="error", provider=agent.faction, usage={})
                provider_error = f"{type(exc).__name__}: {exc}"
            latency = time.perf_counter() - start

            action = parse_action(result.text) if result.text else ParsedAction("observe", [], "", "provider_error")
            allowed, safety_reason = safety_gate(action)
            delivered: list[str] = []

            if allowed:
                event_view = {
                    "turn": turn,
                    "from": agent.id,
                    "action": action.action,
                    "message": action.public_message,
                }
                agent.memory.append(event_view)
                for recipient_id in action.recipients:
                    recipient = by_id.get(recipient_id)
                    if recipient and recipient.id != agent.id:
                        recipient.inbox.append(event_view)
                        recipient.memory.append(event_view)
                        pending.add(recipient.id)
                        delivered.append(recipient.id)
            else:
                agent.memory.append({"turn": turn, "type": "action_blocked", "reason": "external_rule"})

            agent.inbox.clear()
            agent.last_active_turn = turn
            after = {
                "inbox_count": len(agent.inbox),
                "memory_count": len(agent.memory),
                "last_active_turn": agent.last_active_turn,
            }

            event = {
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "virtual_time": {"day": day, "hour": hour, "turn": turn},
                "agent_id": agent.id,
                "faction": agent.faction,
                "role": agent.role,
                "provider": result.provider,
                "model": result.model,
                "visible_context": visible_context,
                "raw_response": result.text,
                "parsed_action": asdict(action),
                "recipients_requested": action.recipients,
                "recipients_delivered": delivered,
                "public_message": action.public_message if allowed else "",
                "private_note": action.private_note,
                "state_before": before,
                "state_after": after,
                "safety_result": {"allowed": allowed, "reason": safety_reason},
                "provider_error": provider_error,
                "latency_seconds": round(latency, 6),
                "usage": result.usage,
            }
            jsonl_append(log_dir / "raw" / f"day{day:02d}.jsonl", event)

        write_json(
            log_dir / "snapshots" / f"turn{turn:03d}.json",
            {
                "turn": turn,
                "day": day,
                "hour": hour,
                "pending": sorted(pending),
                "agents": [
                    {
                        "id": a.id,
                        "faction": a.faction,
                        "role": a.role,
                        "last_active_turn": a.last_active_turn,
                        "inbox_count": len(a.inbox),
                        "memory_tail": a.memory[-5:],
                    }
                    for a in agents
                ],
            },
        )

    print(f"Experiment complete: {total_turns} turns, {len(agents)} agents, live={live}")


if __name__ == "__main__":
    main()
