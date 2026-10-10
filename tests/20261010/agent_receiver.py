import json
import sqlite3
from pathlib import Path

from agent.local_llm import decide


# =========================================================
# 설정
# =========================================================

BASE_DIR = Path(__file__).parent

# WSL main.py가 2회 순회 완료 후 생성
AGENT_REQUEST_FILE = BASE_DIR / "agent_request.json"

# Windows LLM 판단 결과
DECISION_FILE = BASE_DIR / "decision.json"

# Observation Memory
DB_FILE = BASE_DIR / "memory" / "observation_memory.db"


# =========================================================
# Mission Observation 조회
# =========================================================

def get_recent_mission_observations(limit=6):
    """
    SQLite에서 가장 최근 Observation을 가져온다.

    현재 Mission:
        P1_MAIN
        P1_SIDE
        P2_MAIN

    위 3개 지점을 2회 순회하므로
    총 6개의 Observation을 가져온다.

    DB에서는 최신 ID부터 조회하고,
    LLM에는 실제 관측 순서대로 전달하기 위해
    마지막에 reverse한다.
    """

    if not DB_FILE.exists():

        raise FileNotFoundError(
            f"Observation DB not found: {DB_FILE}"
        )

    conn = sqlite3.connect(DB_FILE)

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            timestamp,
            point_id,

            robot_x,
            robot_y,
            robot_yaw,

            navigation_state,

            starfish_count,
            starfish_confidence,

            shell_count,
            shell_confidence,

            situation,
            action,
            reason

        FROM observations

        ORDER BY id DESC

        LIMIT ?
        """,
        (limit,)
    )

    rows = cursor.fetchall()

    conn.close()

    observations = [
        dict(row)
        for row in rows
    ]

    # 현재는 최신순
    #
    # 예:
    # P2 patrol2
    # P1_SIDE patrol2
    # P1 patrol2
    # P2 patrol1
    # ...
    #
    # 이것을 실제 시간순으로 변경한다.

    observations.reverse()

    return observations


# =========================================================
# Mission Observation 출력
# =========================================================

def print_mission_observations(
    observations
):

    print("\n===================================")
    print(" MISSION OBSERVATIONS")
    print("===================================")

    for index, obs in enumerate(
        observations,
        start=1
    ):

        print(
            f"\n[{index}/{len(observations)}]"
        )

        print(
            f"ID         : {obs['id']}"
        )

        print(
            f"Time       : {obs['timestamp']}"
        )

        print(
            f"Point      : {obs['point_id']}"
        )

        print(
            f"Position   : "
            f"({obs['robot_x']:.3f}, "
            f"{obs['robot_y']:.3f})"
        )

        print(
            f"Yaw        : "
            f"{obs['robot_yaw']:.3f}"
        )

        print(
            f"Navigation : "
            f"{obs['navigation_state']}"
        )

        print(
            f"Starfish   : "
            f"{obs['starfish_count']} "
            f"(conf={obs['starfish_confidence']})"
        )

        print(
            f"Shell      : "
            f"{obs['shell_count']} "
            f"(conf={obs['shell_confidence']})"
        )

    print("\n===================================")


# =========================================================
# Mission 데이터 검사
# =========================================================

def validate_mission_observations(
    observations
):
    """
    현재 실험에서는 3개 지점 × 2회 = 6개가
    정상적인 Mission 데이터이다.

    완전히 강제하지는 않고 Warning만 출력한다.
    """

    expected_count = 6

    if len(observations) != expected_count:

        print(
            f"\n[WARNING] "
            f"Expected {expected_count} observations, "
            f"but found {len(observations)}."
        )

        return False

    print(
        f"\n[AGENT] "
        f"{len(observations)} mission observations loaded."
    )

    return True


# =========================================================
# LLM 입력 구성
# =========================================================

def prepare_llm_input(observations):
    """Mission 전체 Observation을 시간순 그대로 LLM에 전달한다."""
    if not observations:
        raise ValueError("No mission observations.")
    return observations


# =========================================================
# Decision JSON 저장
# =========================================================

def save_decision_file(
    decision
):
    """
    Local LLM의 판단 결과를 decision.json으로 저장한다.

    이후 WSL main.py가 이 파일을 읽어
    실제 Robot Action으로 연결한다.
    """

    with open(
        DECISION_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            decision,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(
        "\n[AGENT] decision.json 생성 완료"
    )

    print(
        f"[AGENT] File: "
        f"{DECISION_FILE}"
    )


# =========================================================
# Main
# =========================================================

def main():

    print("===================================")
    print(" Physical AI Agent")
    print(" Mission-level Decision")
    print("===================================")


    # =====================================================
    # 1. agent_request.json 확인
    # =====================================================

    if not AGENT_REQUEST_FILE.exists():

        print(
            "\n[AGENT] "
            "agent_request.json이 없습니다."
        )

        print(
            "[AGENT] "
            "Go2의 2회 순회가 아직 완료되지 않았거나 "
            "판단 요청이 생성되지 않았습니다."
        )

        return


    # =====================================================
    # 2. Agent Request 읽기
    # =====================================================

    try:

        with open(
            AGENT_REQUEST_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            request = json.load(f)

    except Exception as e:

        print(
            f"\n[AGENT ERROR] "
            f"Failed to read agent request: {e}"
        )

        return


    print("\n===================================")
    print(" AGENT REQUEST")
    print("===================================")

    print(
        json.dumps(
            request,
            ensure_ascii=False,
            indent=2
        )
    )


    # =====================================================
    # 3. 요청 종류 확인
    # =====================================================

    request_type = (
        request.get("type")
    )


    if request_type != "MISSION_COMPLETED":

        print(
            f"\n[AGENT ERROR] "
            f"Unsupported request type: "
            f"{request_type}"
        )

        return


    print(
        "\n[AGENT] "
        "Mission completion request received."
    )


    # =====================================================
    # 4. SQLite Observation Memory 읽기
    # =====================================================

    try:

        mission_observations = (
            get_recent_mission_observations(
                limit=6
            )
        )

    except Exception as e:

        print(
            f"\n[MEMORY ERROR] "
            f"{e}"
        )

        return


    # =====================================================
    # 5. Observation 확인
    # =====================================================

    if not mission_observations:

        print(
            "\n[MEMORY ERROR] "
            "No observations found."
        )

        return


    print_mission_observations(
        mission_observations
    )


    validate_mission_observations(
        mission_observations
    )


    # =====================================================
    # 6. Mission-level LLM 입력 생성
    # =====================================================

    try:
        llm_observations = prepare_llm_input(mission_observations)
    except Exception as e:
        print(f"\n[AGENT ERROR] Failed to prepare LLM input: {e}")
        return

    print("\n===================================")
    print(" LLM INPUT")
    print("===================================")
    print(f"Mission observations : {len(llm_observations)}")
    print("Mode                 : FULL MISSION COMPARISON")


    # =====================================================
    # 7. Local LLM 판단
    # =====================================================

    print("\n===================================")
    print(" LOCAL LLM DECISION")
    print("===================================")

    print(
        "[AGENT] "
        "Sending mission observations "
        "to Local LLM..."
    )


    try:

        decision = decide(
            mission_observations=llm_observations
        )

    except Exception as e:

        print(
            f"\n[LLM ERROR] "
            f"{e}"
        )

        return


    # =====================================================
    # 8. LLM 판단 결과 확인
    # =====================================================

    print("\n===================================")
    print(" AGENT DECISION")
    print("===================================")

    print(
        "Situation :",
        decision.get(
            "situation"
        )
    )

    print(
        "Action    :",
        decision.get(
            "action"
        )
    )

    print(
        "Reason    :",
        decision.get(
            "reason"
        )
    )

    # local_llm.py를 나중에 확장하면
    # target_point도 받을 수 있다.

    if "target_point" in decision:

        print(
            "Target     :",
            decision[
                "target_point"
            ]
        )


    # =====================================================
    # 9. decision.json 생성
    # =====================================================

    try:

        save_decision_file(
            decision
        )

    except Exception as e:

        print(
            f"\n[AGENT ERROR] "
            f"Failed to save decision: {e}"
        )

        return


    # =====================================================
    # 10. 완료
    # =====================================================

    print("\n===================================")
    print(" AGENT PROCESS COMPLETED")
    print("===================================")

    print(
        "[AGENT] "
        "The decision is ready for Go2."
    )

    print(
        "[AGENT] "
        "Robot action execution is "
        "NOT connected yet."
    )


# =========================================================
# Entry Point
# =========================================================

if __name__ == "__main__":

    main()