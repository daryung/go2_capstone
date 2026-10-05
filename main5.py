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


            # =============================================
            # Vision 연결 전 임시값
            # =============================================

            starfish_count=0,

            starfish_confidence=0.0,

            shell_count=0,

            shell_confidence=0.0,
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

def request_agent_decision():
    """
    모든 순회가 완료되었음을 Windows Agent에게 알린다.

    이 파일이 생성되면 Windows의 Agent가
    SQLite Observation Memory를 읽어
    Local LLM 판단을 수행한다.

    중요:
    여기서는 Observation 자체를 전달하지 않는다.
    실제 Observation 데이터는 이미 SQLite에 저장되어 있다.
    """

    request = {

        "type":
            "MISSION_COMPLETED",

        "timestamp":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "patrol_count":
            PATROL_COUNT,

        "route":
            ROUTE,
    }


    try:

        with open(
            AGENT_REQUEST_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                request,
                f,
                ensure_ascii=False,
                indent=2
            )


        print(
            "\n======================================"
        )

        print(
            "[AGENT REQUEST]"
        )

        print(
            "======================================"
        )

        print(
            f"[AGENT REQUEST] "
            f"{PATROL_COUNT} patrols completed."
        )

        print(
            "[AGENT REQUEST] "
            "Requesting Local LLM decision."
        )

        print(
            f"[AGENT REQUEST] File: "
            f"{AGENT_REQUEST_FILE}"
        )

        print(
            "======================================"
        )


        return True


    except Exception as e:

        print(
            f"[AGENT REQUEST ERROR] "
            f"{e}"
        )

        return False


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
    # 8. 여기서 처음으로 Agent 판단 요청
    # =====================================================

    request_agent_decision()


    # =====================================================
    # 현재 최종 위치 출력
    # =====================================================

    final_pose = (
        localization.get_pose()
    )


    if final_pose is not None:

        print(
            "[FINAL POSE]",
            final_pose
        )


    # =====================================================
    # 연결 유지
    # =====================================================

    print(
        "[SYSTEM] "
        "Waiting for next step..."
    )


    while True:

        await asyncio.sleep(
            1
        )


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