import asyncio
import json

from datetime import datetime
from pathlib import Path

from robot.connection import Go2Connection
from robot.navigation import Go2Navigation
from robot.localization import Go2Localization
from robot.map_manager import Go2MapManager

from memory.observation_memory import save_observation


# =========================================================
# 기본 설정
# =========================================================

MAP_ID = "ueNNgwm6wbiqCBgPHwqXGw"

INITIAL_POSE = (
    0.013,
    0.023,
    0.000
)


WAYPOINTS = {

    "HOME": INITIAL_POSE,

    "P1_MAIN": (
        2.399,
        -1.307,
        0.000
    ),

    "P1_SIDE": (
        3.272,
        -2.408,
        1.906
    ),

    "P2_MAIN": (
        2.262,
        -2.908,
        -2.946
    ),
}


ROUTE = [
    "P1_MAIN",
    "P1_SIDE",
    "P2_MAIN",
]


# 총 순회 횟수
PATROL_COUNT = 2


# 목적지 도착 후 안정화 시간
OBSERVATION_DELAY = 2.0


# =========================================================
# Windows Agent 통신 파일
# =========================================================

BASE_DIR = Path(__file__).parent

AGENT_REQUEST_FILE = (
    BASE_DIR / "agent_request.json"
)


# =========================================================
# 시나리오 1: 가상 Vision 출력 (실제 Go2 위치는 그대로 사용)
# =========================================================
# 1차 순회: 모든 지점 정상
# 2차 순회: P1_SIDE(B)에서 일시적 가림으로 저신뢰·개체수 감소
# 이후 재관측 단계는 다음 통합 작업에서 추가한다.
MOCK_VISION = {
    (1, "P1_MAIN"): (3, 0.92, 2, 0.90),
    (1, "P1_SIDE"): (3, 0.91, 2, 0.89),
    (1, "P2_MAIN"): (3, 0.93, 2, 0.91),
    (2, "P1_MAIN"): (3, 0.90, 2, 0.88),
    (2, "P1_SIDE"): (0, 0.38, 2, 0.88),
    (2, "P2_MAIN"): (3, 0.91, 2, 0.90),
}

# =========================================================
# Observation 생성
# =========================================================

def make_robot_observation(
    point_name,
    patrol,
    localization,
    navigation,
):
    """
    현재 Go2 상태를 하나의 Observation으로 생성한다.
    """

    pose = localization.get_pose()

    if pose is None:
        return None


    observation = {

        "timestamp":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "patrol":
            patrol,

        "point_id":
            point_name,

        "robot_x":
            pose["x"],

        "robot_y":
            pose["y"],

        "robot_z":
            pose["z"],

        "robot_yaw":
            pose["yaw"],

        "navigation_state":
            navigation.state,
    }


    return observation


# =========================================================
# Observation 출력
# =========================================================

def print_observation(
    observation
):

    print(
        "\n--------------------------------------"
    )

    print(
        "[OBSERVATION SNAPSHOT]"
    )

    print(
        "--------------------------------------"
    )

    print(
        f"time       : "
        f"{observation['timestamp']}"
    )

    print(
        f"patrol     : "
        f"{observation['patrol']}"
    )

    print(
        f"point_id   : "
        f"{observation['point_id']}"
    )

    print(
        f"position   : "
        f"x={observation['robot_x']:.3f}, "
        f"y={observation['robot_y']:.3f}, "
        f"z={observation['robot_z']:.3f}"
    )

    print(
        f"yaw        : "
        f"{observation['robot_yaw']:.3f}"
    )

    print(
        f"nav_state  : "
        f"{observation['navigation_state']}"
    )

    print(
        "--------------------------------------"
    )


# =========================================================
# SQLite Observation Memory 저장
# =========================================================

def save_robot_observation(
    observation
):
    """
    실제 Go2 Observation을 SQLite에 저장한다.

    현재 Vision 연결 전이므로
    생물 탐지값은 임시값을 사용한다.
    """

    try:

        observation_id = save_observation(

            point_id=
                observation["point_id"],

            robot_x=
                observation["robot_x"],

            robot_y=
                observation["robot_y"],

            robot_yaw=
                observation["robot_yaw"],

            navigation_state=
                observation["navigation_state"],


            # 시나리오 1 가상 Vision 결과
            starfish_count=observation["starfish_count"],
            starfish_confidence=observation["starfish_confidence"],
            shell_count=observation["shell_count"],
            shell_confidence=observation["shell_confidence"],
        )


        print(
            f"[MEMORY] "
            f"Observation saved successfully. "
            f"ID={observation_id}"
        )


        return observation_id


    except Exception as e:

        print(
            f"[MEMORY ERROR] "
            f"Failed to save observation: {e}"
        )

        return None


# =========================================================
# Agent 판단 요청
# =========================================================

def write_json_atomic(path, payload):
    temp = path.with_name(path.name + ".tmp")
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    temp.replace(path)


async def ask_agent(request_type, observation_ids, *, target_point=None):
    """요청 ID를 이용한 Windows Agent 왕복 통신 (최대 180초)."""
    import uuid
    import time

    request_id = uuid.uuid4().hex
    request = {
        "request_id": request_id,
        "type": request_type,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "observation_ids": observation_ids,
        "route": ROUTE,
    }
    if target_point is not None:
        request["target_point"] = target_point

    # 이전 실행에서 남은 응답은 절대 사용하지 않는다.
    if DECISION_FILE.exists():
        DECISION_FILE.unlink()

    write_json_atomic(AGENT_REQUEST_FILE, request)
    print(f"[BRIDGE] Request sent: {request_type} / {request_id}")

    deadline = time.monotonic() + AGENT_TIMEOUT_S
    while time.monotonic() < deadline:
        if DECISION_FILE.exists():
            try:
                response = json.loads(DECISION_FILE.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                await asyncio.sleep(0.5)
                continue

            if response.get("request_id") == request_id:
                DECISION_FILE.unlink(missing_ok=True)
                if response.get("status") != "ok":
                    raise RuntimeError(f"Agent failed: {response.get('error')}")
                decision = response.get("decision")
                if not isinstance(decision, dict):
                    raise ValueError("Invalid Agent decision")
                print(f"[BRIDGE] Agent decision: {decision}")
                return decision
        await asyncio.sleep(0.5)
    raise TimeoutError("Agent response timeout; robot will not move")


# =========================================================
# Main
# =========================================================

async def main():

    # =====================================================
    # 1. Go2 연결
    # =====================================================

    robot = Go2Connection()

    conn = await robot.connect()


    navigation = Go2Navigation(
        conn
    )

    navigation.subscribe_server_log()


    localization = Go2Localization(
        conn
    )

    localization.subscribe_pose()


    map_manager = Go2MapManager(
        conn
    )


    print(
        "[SYSTEM] Go2 system ready."
    )


    # =====================================================
    # 2. Map 활성화
    # =====================================================

    print(
        "\n=============================="
    )

    print(
        "[SYSTEM] Activating map"
    )

    print(
        "=============================="
    )


    await map_manager.activate_map(
        MAP_ID
    )


    # =====================================================
    # 3. Initial Pose 설정
    # =====================================================

    print(
        "\n=============================="
    )

    print(
        "[SYSTEM] Setting initial pose"
    )

    print(
        "=============================="
    )


    navigation.reset_localization_event()


    localization.set_initial_pose(
        *INITIAL_POSE
    )


    await asyncio.sleep(
        0.1
    )


    # =====================================================
    # 4. Localization 시작
    # =====================================================

    print(
        "\n=============================="
    )

    print(
        "[SYSTEM] Starting localization"
    )

    print(
        "=============================="
    )


    localization.start()


    ready = (
        await navigation.wait_for_localization(
            timeout=60.0
        )
    )


    if not ready:

        print(
            "[SYSTEM] Cannot start mission."
        )

        return


    await asyncio.sleep(
        0.5
    )


    pose = localization.get_pose()


    if pose is None:

        print(
            "[ERROR] Localization succeeded "
            "but pose is unavailable."
        )

        return


    print(
        "[CURRENT POSE]",
        pose
    )


    # =====================================================
    # 5. Waypoint Patrol
    # =====================================================

    print(
        "\n=============================="
    )

    print(
        "[MISSION] Waypoint patrol start"
    )

    print(
        f"[MISSION] Total patrols: "
        f"{PATROL_COUNT}"
    )

    print(
        "=============================="
    )


    for patrol in range(
        1,
        PATROL_COUNT + 1
    ):

        print(
            "\n======================================"
        )

        print(
            f"[MISSION] PATROL "
            f"{patrol}/{PATROL_COUNT} START"
        )

        print(
            "======================================"
        )


        # =================================================
        # 각 Waypoint 순회
        # =================================================

        for index, point_name in enumerate(
            ROUTE,
            start=1
        ):

            target = (
                WAYPOINTS[point_name]
            )


            print(
                "\n=============================="
            )

            print(
                f"[MISSION] PATROL "
                f"{patrol}/{PATROL_COUNT} | "
                f"{index}/{len(ROUTE)}"
            )

            print(
                f"[MISSION] Moving to "
                f"{point_name}"
            )

            print(
                f"[TARGET] "
                f"x={target[0]:.3f}, "
                f"y={target[1]:.3f}, "
                f"yaw={target[2]:.3f}"
            )

            print(
                "=============================="
            )


            # =================================================
            # Navigation
            # =================================================

            success = (
                await navigation.goto_and_wait(
                    *target,
                    timeout=60.0
                )
            )


            if not success:

                print(
                    "\n=============================="
                )

                print(
                    "[MISSION] PATROL FAILED"
                )

                print(
                    f"[MISSION] Patrol: "
                    f"{patrol}/{PATROL_COUNT}"
                )

                print(
                    f"[MISSION] Point: "
                    f"{point_name}"
                )

                print(
                    f"[MISSION] Reason: "
                    f"{navigation.state}"
                )

                print(
                    "=============================="
                )

                return


            print(
                f"[MISSION] Arrived at "
                f"{point_name}."
            )


            # =================================================
            # 6. Observation
            # =================================================

            print(
                f"[OBSERVATION] Waiting "
                f"{OBSERVATION_DELAY:.1f}s "
                f"for robot stabilization..."
            )


            await asyncio.sleep(
                OBSERVATION_DELAY
            )


            observation = (
                make_robot_observation(
                    point_name=point_name,
                    patrol=patrol,
                    localization=localization,
                    navigation=navigation
                )
            )


            if observation is None:

                print(
                    f"[WARNING] "
                    f"Pose unavailable "
                    f"at {point_name}."
                )


            else:

                mock = MOCK_VISION.get((patrol, point_name))
                if mock is None:
                    raise ValueError(f"Missing mock Vision data: {patrol}, {point_name}")
                observation.update({
                    "starfish_count": mock[0],
                    "starfish_confidence": mock[1],
                    "shell_count": mock[2],
                    "shell_confidence": mock[3],
                })
                print(f"[VISION-MOCK] patrol={patrol}, point={point_name}, "
                      f"starfish={mock[0]} (conf={mock[1]:.2f}), "
                      f"shell={mock[2]} (conf={mock[3]:.2f})")

                # -----------------------------------------
                # Observation 출력
                # -----------------------------------------

                print_observation(
                    observation
                )


                # -----------------------------------------
                # SQLite에 즉시 저장
                #
                # 여기서는 LLM을 호출하지 않는다.
                # -----------------------------------------

                save_robot_observation(
                    observation
                )


            # =================================================
            # 다음 Waypoint 이동 전 대기
            # =================================================

            await asyncio.sleep(
                1.0
            )


        # =====================================================
        # 현재 Patrol 완료
        # =====================================================

        print(
            "\n======================================"
        )

        print(
            f"[MISSION] PATROL "
            f"{patrol}/{PATROL_COUNT} COMPLETED"
        )

        print(
            "======================================"
        )


        # -----------------------------------------------------
        # 1회차가 끝났다면
        # 판단하지 않고 바로 2회차로 진행
        # -----------------------------------------------------

        if patrol < PATROL_COUNT:

            print(
                "[MISSION] "
                "Observations saved."
            )

            print(
                "[MISSION] "
                "LLM decision is NOT requested yet."
            )

            print(
                "[MISSION] "
                "Starting next patrol: "
                "P2_MAIN -> P1_MAIN"
            )


            await asyncio.sleep(
                2.0
            )


    # =====================================================
    # 7. 두 번의 Patrol 모두 완료
    # =====================================================

    print(
        "\n======================================"
    )

    print(
        "[MISSION] ALL PATROLS COMPLETED"
    )

    print(
        "P1_MAIN -> P1_SIDE -> "
        "P2_MAIN x 2"
    )

    print(
        "======================================"
    )


    # =====================================================
    # 8. Windows Agent와 자동 통신
    # =====================================================
    if len(mission_ids) != PATROL_COUNT * len(ROUTE):
        raise RuntimeError("Missing mission observations; stopping safely")

    try:
        decision = await ask_agent("MISSION_COMPLETED", mission_ids)

        action = decision.get("action")
        target_point = decision.get("target_point")

        if action == "REOBSERVE":
            if target_point not in ROUTE:
                raise ValueError(f"Unapproved reobservation point: {target_point}")

            # 안전을 위해 최대 한 번만 재관측 이동
            for attempt in range(MAX_REOBSERVATIONS):
                print(f"[RECOVERY] REOBSERVE {target_point} ({attempt + 1})")
                success = await navigation.goto_and_wait(
                    *WAYPOINTS[target_point], timeout=60.0
                )
                if not success:
                    print(f"[RECOVERY] Navigation failed: {navigation.state}")
                    return

                await asyncio.sleep(OBSERVATION_DELAY)
                observation = make_robot_observation(
                    point_name=target_point,
                    patrol=PATROL_COUNT + 1,
                    localization=localization,
                    navigation=navigation,
                )
                if observation is None:
                    raise RuntimeError("Pose unavailable during reobservation")

                # 시나리오 1: B의 일시적 가림이 해소된 관측값
                observation.update({
                    "starfish_count": 3,
                    "starfish_confidence": 0.92,
                    "shell_count": 2,
                    "shell_confidence": 0.90,
                })
                print("[VISION-MOCK] Reobservation: starfish=3, shell=2")
                new_id = save_robot_observation(observation)
                if new_id is None:
                    raise RuntimeError("Reobservation DB save failed")

                decision = await ask_agent(
                    "REOBSERVATION_COMPLETED",
                    mission_ids + [new_id],
                    target_point=target_point,
                )
                if decision.get("action") == "CONTINUE":
                    print("[MISSION] Scenario 1 closed loop completed")
                else:
                    print("[MISSION] Recovery unresolved; manual review required")
                break
        elif action == "CONTINUE":
            print("[MISSION] Agent chose CONTINUE; no recovery movement")
        else:
            print(f"[MISSION] Unsupported automatic action: {action}; no movement")

    except (TimeoutError, RuntimeError, ValueError, OSError) as exc:
        print(f"[MISSION] Stopped safely: {exc}")

    print("[SYSTEM] Finished. Press Ctrl+C to exit if necessary.")


# =========================================================
# Entry Point
# =========================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print(
            "\n[SYSTEM] Program stopped."
        )