import json
from pathlib import Path

from memory.observation_memory import (
    save_observation,
    get_history,
    save_decision
)

from agent.local_llm import decide


BASE_DIR = Path(__file__).parent

OBSERVATION_FILE = BASE_DIR / "observation.json"
DECISION_FILE = BASE_DIR / "decision.json"


print("===================================")
print(" Physical AI Agent")
print("===================================")


# --------------------------------------------------
# 1. WSL / Go2가 생성한 Observation 읽기
# --------------------------------------------------

with open(OBSERVATION_FILE, "r", encoding="utf-8") as f:
    current_observation = json.load(f)


print("\n[GO2 OBSERVATION]")
print(current_observation)


# --------------------------------------------------
# 2. SQLite 저장
# --------------------------------------------------

observation_id = save_observation(
    point_id=current_observation["point_id"],

    robot_x=current_observation["robot_x"],
    robot_y=current_observation["robot_y"],
    robot_yaw=current_observation["robot_yaw"],

    navigation_state=current_observation["navigation_state"],

    starfish_count=current_observation["starfish_count"],
    starfish_confidence=current_observation["starfish_confidence"],

    shell_count=current_observation["shell_count"],
    shell_confidence=current_observation["shell_confidence"]
)

print(f"\n[MEMORY] Observation 저장: ID={observation_id}")


# --------------------------------------------------
# 3. 같은 관측지점의 과거 기록
# --------------------------------------------------

history = get_history(
    point_id=current_observation["point_id"],
    limit=5,
    exclude_id=observation_id
)

print("\n[HISTORY]")

for obs in history:
    print(
        f"ID={obs['id']} | "
        f"Starfish={obs['starfish_count']} | "
        f"Shell={obs['shell_count']} | "
        f"Situation={obs['situation']} | "
        f"Action={obs['action']}"
    )


# --------------------------------------------------
# 4. Local LLM 판단
# --------------------------------------------------

decision = decide(
    current_observation=current_observation,
    history=history
)

print("\n[AGENT DECISION]")
print("Situation :", decision["situation"])
print("Action    :", decision["action"])
print("Reason    :", decision["reason"])


# --------------------------------------------------
# 5. 판단 SQLite 저장
# --------------------------------------------------

save_decision(
    observation_id=observation_id,
    situation=decision["situation"],
    action=decision["action"],
    reason=decision["reason"]
)


# --------------------------------------------------
# 6. WSL / Go2에게 보낼 Decision 생성
# --------------------------------------------------

with open(DECISION_FILE, "w", encoding="utf-8") as f:
    json.dump(
        decision,
        f,
        ensure_ascii=False,
        indent=2
    )

print("\n[AGENT] decision.json 생성 완료")