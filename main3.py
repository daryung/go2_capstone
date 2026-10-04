import asyncio
from datetime import datetime

from robot.connection import Go2Connection
from robot.navigation import Go2Navigation
from robot.localization import Go2Localization
from robot.map_manager import Go2MapManager


MAP_ID = "ueNNgwm6wbiqCBgPHwqXGw"

INITIAL_POSE = (0.013, 0.023, 0.000)

WAYPOINTS = {
    "HOME": INITIAL_POSE,
    "P1_MAIN": (2.399, -1.307, 0.000),
    "P1_SIDE": (3.272, -2.408, 1.906),
    "P2_MAIN": (2.262, -2.908, -2.946),
}

ROUTE = [
    "P1_MAIN",
    "P1_SIDE",
    "P2_MAIN",
]

PATROL_COUNT = 2

# 목적지 도착 후 로봇이 안정될 때까지 기다리는 시간
OBSERVATION_DELAY = 2.0


def make_robot_observation(
    point_name,
    patrol,
    localization,
    navigation,
):
    """
    현재 로봇의 최신 상태를 하나의 Observation Snapshot으로 생성.
    아직 DB에는 저장하지 않는다.
    """

    pose = localization.get_pose()

    if pose is None:
        return None

    observation = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "patrol": patrol,
        "point_id": point_name,

        "robot_x": pose["x"],
        "robot_y": pose["y"],
        "robot_z": pose["z"],
        "robot_yaw": pose["yaw"],

        "navigation_state": navigation.state,
    }

    return observation


def print_observation(observation):
    """Observation Snapshot 확인용 출력."""

    print("\n--------------------------------------")
    print("[OBSERVATION SNAPSHOT]")
    print("--------------------------------------")

    print(f"time       : {observation['timestamp']}")
    print(f"patrol     : {observation['patrol']}")
    print(f"point_id   : {observation['point_id']}")

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

    print("--------------------------------------")


async def main():

    # =====================================================
    # 1. Connect
    # =====================================================

    robot = Go2Connection()
    conn = await robot.connect()

    navigation = Go2Navigation(conn)
    navigation.subscribe_server_log()

    localization = Go2Localization(conn)
    localization.subscribe_pose()

    map_manager = Go2MapManager(conn)

    print("[SYSTEM] Go2 system ready.")

    # =====================================================
    # 2. Activate map
    # =====================================================

    print("\n==============================")
    print("[SYSTEM] Activating map")
    print("==============================")

    await map_manager.activate_map(MAP_ID)

    # =====================================================
    # 3. Set initial pose
    # =====================================================

    print("\n==============================")
    print("[SYSTEM] Setting initial pose")
    print("==============================")

    navigation.reset_localization_event()

    localization.set_initial_pose(
        *INITIAL_POSE
    )

    await asyncio.sleep(0.1)

    # =====================================================
    # 4. Start localization
    # =====================================================

    print("\n==============================")
    print("[SYSTEM] Starting localization")
    print("==============================")

    localization.start()

    ready = await navigation.wait_for_localization(
        timeout=60.0
    )

    if not ready:
        print("[SYSTEM] Cannot start mission.")
        return

    await asyncio.sleep(0.5)

    pose = localization.get_pose()

    if pose is None:
        print(
            "[ERROR] Localization succeeded "
            "but pose is unavailable."
        )
        return

    print("[CURRENT POSE]", pose)

    # =====================================================
    # 5. Waypoint patrol
    # =====================================================

    print("\n==============================")
    print("[MISSION] Waypoint patrol start")
    print(f"[MISSION] Total patrols: {PATROL_COUNT}")
    print("==============================")

    for patrol in range(1, PATROL_COUNT + 1):

        print("\n======================================")
        print(
            f"[MISSION] PATROL "
            f"{patrol}/{PATROL_COUNT} START"
        )
        print("======================================")

        for index, point_name in enumerate(
            ROUTE,
            start=1,
        ):

            target = WAYPOINTS[point_name]

            print("\n==============================")

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

            print("==============================")

            # ---------------------------------------------
            # Navigation
            # ---------------------------------------------

            success = await navigation.goto_and_wait(
                *target,
                timeout=60.0,
            )

            if not success:

                print("\n==============================")
                print("[MISSION] PATROL FAILED")

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

                print("==============================")

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

            observation = make_robot_observation(
                point_name=point_name,
                patrol=patrol,
                localization=localization,
                navigation=navigation,
            )

            if observation is None:

                print(
                    f"[WARNING] Pose unavailable "
                    f"at {point_name}."
                )

            else:

                print_observation(
                    observation
                )

            # 다음 목적지 이동 전 잠시 대기
            await asyncio.sleep(1.0)

        # =================================================
        # Patrol completed
        # =================================================

        print("\n======================================")

        print(
            f"[MISSION] PATROL "
            f"{patrol}/{PATROL_COUNT} COMPLETED"
        )

        print("======================================")

        if patrol < PATROL_COUNT:

            print(
                "[MISSION] Starting "
                "next patrol: "
                "P2_MAIN -> P1_MAIN"
            )

            await asyncio.sleep(2.0)

    # =====================================================
    # 7. All patrols completed
    # =====================================================

    print("\n======================================")
    print("[MISSION] ALL PATROLS COMPLETED")

    print(
        "P1_MAIN -> P1_SIDE -> "
        "P2_MAIN x 2"
    )

    print("======================================")

    final_pose = localization.get_pose()

    if final_pose is not None:
        print("[FINAL POSE]", final_pose)

    # 연결 유지
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\n[SYSTEM] Program stopped.")