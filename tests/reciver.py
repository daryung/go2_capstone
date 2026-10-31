"""Windows에서 상시 실행하는 시나리오 1 Agent.
기존 agent_receiver.py는 수정하지 않는다.
프로젝트 루트에서: python agent_receiver_loop.py
"""
import json
import sqlite3
import time
import urllib.request
from pathlib import Path

from agent.local_llm import decide

BASE = Path(__file__).resolve().parent
REQUEST_FILE = BASE / "agent_request.json"
DECISION_FILE = BASE / "decision.json"
DB_FILE = BASE / "memory" / "observation_memory.db"
POLL_INTERVAL_S = 0.5
ALLOWED_POINTS = {"P1_MAIN", "P1_SIDE", "P2_MAIN"}


def write_json_atomic(path, value):
    temp = path.with_name(path.name + ".tmp")
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
    temp.replace(path)


def load_observations(ids):
    if not isinstance(ids, list) or len(ids) not in (6, 7):
        raise ValueError("Expected 6 mission IDs or 7 including reobservation")
    if any(type(v) is not int or v <= 0 for v in ids) or len(set(ids)) != len(ids):
        raise ValueError("Invalid observation IDs")

    with sqlite3.connect(DB_FILE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"SELECT * FROM observations WHERE id IN ({placeholders})", ids
        ).fetchall()
    by_id = {row["id"]: dict(row) for row in rows}
    if len(by_id) != len(ids):
        raise ValueError("Some observation IDs are missing")
    return [by_id[i] for i in ids]


def validate_decision(decision, *, reobserve=False):
    if not isinstance(decision, dict):
        raise ValueError("LLM response is not an object")
    action = decision.get("action")
    target = decision.get("target_point")
    allowed = {"CONTINUE", "REOBSERVE"} if not reobserve else {"CONTINUE", "REOBSERVE", "ACCEPT_CHANGE"}
    if action not in allowed:
        raise ValueError(f"Unsupported decision action: {action}")
    if action == "REOBSERVE" and target not in ALLOWED_POINTS:
        raise ValueError(f"REOBSERVE requires a known target: {target}")
    return decision


def decide_reobservation(observations, target):
    """재관측의 맥락을 LLM에 명시하여 판단한다."""
    relevant = [o for o in observations if o["point_id"] == target]
    if len(relevant) < 3:
        raise ValueError("Need baseline, anomaly and reobservation at target")
    schema = {
        "type": "object",
        "properties": {
            "situation": {"type": "string", "enum": ["NORMAL", "OBSERVATION_ANOMALY", "POSSIBLE_REAL_CHANGE"]},
            "action": {"type": "string", "enum": ["CONTINUE", "REOBSERVE", "ACCEPT_CHANGE"]},
            "target_point": {"type": ["string", "null"]},
            "reason": {"type": "string"},
        },
        "required": ["situation", "action", "target_point", "reason"],
        "additionalProperties": False,
    }
    payload = {
        "model": "qwen3.5:4b",
        "stream": False,
        "think": False,
        "format": schema,
        "options": {"temperature": 0},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You evaluate marine organism observations at one point in chronological order. "
                    "The last observation is an explicit REOBSERVATION after an anomaly. "
                    "If the original high-confidence baseline is recovered with high confidence, "
                    "return situation NORMAL, action CONTINUE, target_point null. "
                    "If a genuine decrease is repeatedly confirmed with high confidence, "
                    "return POSSIBLE_REAL_CHANGE and ACCEPT_CHANGE. "
                    "Otherwise return OBSERVATION_ANOMALY and REOBSERVE. "
                    "Do not treat a low-confidence anomalous reading as baseline."
                ),
            },
            {
                "role": "user",
                "content": "Target: " + target + "\nChronological observations:\n"
                + json.dumps(relevant, ensure_ascii=False, indent=2),
            },
        ],
    }
    request = urllib.request.Request(
        "http://localhost:11434/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=150) as response:
        result = json.loads(response.read().decode("utf-8"))
    return json.loads(result["message"]["content"])


def process(request):
    request_type = request.get("type")
    observations = load_observations(request.get("observation_ids"))
    if request_type == "MISSION_COMPLETED":
        if len(observations) != 6:
            raise ValueError("Mission must have exactly six observations")
        expected = ["P1_MAIN", "P1_SIDE", "P2_MAIN"] * 2
        if [o["point_id"] for o in observations] != expected:
            raise ValueError("Unexpected patrol point sequence")
        decision = decide(mission_observations=observations)
        return validate_decision(decision)

    if request_type == "REOBSERVATION_COMPLETED":
        if len(observations) != 7:
            raise ValueError("Reobservation requires seven observations")
        target = request.get("target_point")
        if target not in ALLOWED_POINTS or observations[-1]["point_id"] != target:
            raise ValueError("Reobservation target mismatch")
        decision = decide_reobservation(observations, target)
        return validate_decision(decision, reobserve=True)

    raise ValueError(f"Unknown request type: {request_type}")


def main():
    print("[AGENT] Windows worker started; waiting for WSL requests...")
    print("[AGENT] Ollama must be running at localhost:11434")
    last_processed_id = None
    while True:
        try:
            if not REQUEST_FILE.exists():
                time.sleep(POLL_INTERVAL_S)
                continue
            try:
                request = json.loads(REQUEST_FILE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                time.sleep(POLL_INTERVAL_S)
                continue

            request_id = request.get("request_id")
            if not isinstance(request_id, str) or not request_id:
                # 이전 버전 요청을 자동 처리하지 않는다.
                time.sleep(POLL_INTERVAL_S)
                continue
            if request_id == last_processed_id:
                time.sleep(POLL_INTERVAL_S)
                continue

            # 현재 요청을 처리 중이라는 사실을 기억한다.
            last_processed_id = request_id
            print(f"[AGENT] Processing {request.get('type')} / {request_id}")
            try:
                decision = process(request)
                response = {"request_id": request_id, "status": "ok", "decision": decision}
                print(f"[AGENT] Decision: {decision}")
            except Exception as exc:
                response = {"request_id": request_id, "status": "error", "error": str(exc)}
                print(f"[AGENT ERROR] {exc}")

            write_json_atomic(DECISION_FILE, response)
            # 요청을 삭제하면 이후의 새 요청을 확실하게 구분할 수 있다.
            try:
                current = json.loads(REQUEST_FILE.read_text(encoding="utf-8"))
                if current.get("request_id") == request_id:
                    REQUEST_FILE.unlink(missing_ok=True)
            except (OSError, json.JSONDecodeError):
                pass
        except KeyboardInterrupt:
            print("\n[AGENT] Stopped")
            break
        except OSError as exc:
            print(f"[AGENT] File access error: {exc}")
            time.sleep(1)


if __name__ == "__main__":
    main()
