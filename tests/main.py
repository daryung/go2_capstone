import asyncio

from robot.connection import Go2Connection
from robot.navigation import Go2Navigation
from robot.localization import Go2Localization
from robot.map_manager import Go2MapManager


MAP_ID = "ueNNgwm6wbiqCBgPHwqXGw"

INITIAL_POSE = (0.013, 0.023, 0.000)

WAYPOINTS = {
    "P1_MAIN": (2.399, -1.307, 0.000),
    "P1_SIDE": (3.272, -2.408, 1.906),
    "P2_MAIN": (2.262, -2.908, -2.946),
}

ROUTE = [
    "P1_MAIN",
    "P1_SIDE",
    "P2_MAIN",
]


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
    print("==============================")

    for index, point_name in enumerate(ROUTE, start=1):

        target = WAYPOINTS[point_name]

        print("\n==============================")
        print(
            f"[MISSION] {index}/{len(ROUTE)} "
            f"Moving to {point_name}"
        )
        print(
            f"[TARGET] "
            f"x={target[0]:.3f}, "
            f"y={target[1]:.3f}, "
            f"yaw={target[2]:.3f}"
        )
        print("==============================")

        success = await navigation.goto_and_wait(
            *target,
            timeout=60.0,
        )

        if not success:
            print(
                f"[MISSION] Failed to reach {point_name}. "
                f"Reason: {navigation.state}"
            )
            return

        print(f"[MISSION] Arrived at {point_name}.")

        # 도착 직후 localization 값 안정화
        await asyncio.sleep(1.0)

        pose = localization.get_pose()

        if pose is not None:
            print(
                f"[POSE @ {point_name}] "
                f"x={pose['x']:.3f}, "
                f"y={pose['y']:.3f}, "
                f"z={pose['z']:.3f}, "
                f"yaw={pose['yaw']:.3f}"
            )
        else:
            print(
                f"[WARNING] Pose unavailable "
                f"at {point_name}."
            )

        # 다음 지점 이동 전 잠시 대기
        await asyncio.sleep(2.0)

    # =====================================================
    # 6. Patrol completed
    # =====================================================

    print("\n==============================")
    print("[MISSION] PATROL COMPLETED")
    print(
        "P1_MAIN -> P1_SIDE -> P2_MAIN"
    )
    print("==============================")

    final_pose = localization.get_pose()

    if final_pose is not None:
        print("[FINAL POSE]", final_pose)

    # 프로그램 유지
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\n[SYSTEM] Program stopped.")