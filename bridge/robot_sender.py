import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
OBSERVATION_FILE = BASE_DIR / "observation.json"

# 지금은 Go2 + YOLO 대신 가짜 데이터
observation = {
    "point_id": "B",

    "robot_x": 0.52,
    "robot_y": 1.21,
    "robot_yaw": 1.57,

    "navigation_state": "REACHED",

    "starfish_count": 0,
    "starfish_confidence": 0.38,

    "shell_count": 1,
    "shell_confidence": 0.42
}

with open(OBSERVATION_FILE, "w", encoding="utf-8") as f:
    json.dump(
        observation,
        f,
        ensure_ascii=False,
        indent=2
    )

print("[GO2] Observation 생성 완료")
print(observation)