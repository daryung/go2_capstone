import asyncio

from robot.connection import Go2Connection
from robot.navigation import Go2Navigation
from robot.localization import Go2Localization
from robot.map_manager import Go2MapManager


# =========================================================
# Map / Initial pose / Waypoints
# =========================================================

MAP_ID = "9slQWWk1gZduAEWnEpiUyg"

INITIAL_POSE = (0.013, 0.023, 0.000)

WAYPOINTS = {
    "A": (0.835, 0.298, 0.000),
    "B": (-0.302, 0.307, 0.000),
}


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

    # 지도 파일은 UI에서 미리 로봇에 업로드.
    # Python에서는 기존 map ID만 활성화.
    await map_manager.activate_map(MAP_ID)




    print("\n==============================")
    print("[SYSTEM] Setting initial pose")
    print("==============================")

    # 혹시 이전 실행에서 이벤트가 남아 있다면 제거
    navigation.reset_localization_event()

    localization.set_initial_pose(
        *INITIAL_POSE
    )

    # UI와 동일하게 잠시 대기
    await asyncio.sleep(0.1)



    print("\n==============================")
    print("[SYSTEM] Starting localization")
    print("==============================")

    localization.start()

    # Pose 존재 여부가 아니라
    # [Localization] initialization succeed!
    # 로그를 실제로 기다림.
    ready = await navigation.wait_for_localization(
        timeout=60.0
    )

    if not ready:
        print(
            "[SYSTEM] Cannot start mission."
        )
        return

    # Localization 완료 후 최신 pose가 들어올 시간을
    # 아주 조금 확보
    await asyncio.sleep(0.5)

    pose = localization.get_pose()

    if pose is None:
        print(
            "[ERROR] Localization succeeded "
            "but pose is unavailable."
        )
        return

    print("[CURRENT POSE]", pose)




    print("\n==============================")
    print("[MISSION] Moving to A")
    print("==============================")

    success = await navigation.goto_and_wait(
        *WAYPOINTS["A"],
        timeout=60.0,
    )

    if not success:
        print(
            f"[MISSION] Failed to reach A. "
            f"Reason: {navigation.state}"
        )
        return

    print("[MISSION] Arrived at A.")


    # 목적지 도착 후 USLAM 상태 안정화
    await asyncio.sleep(2.0)

    print("[SYSTEM] Restarting navigation before B...")

    navigation.stop()
    await asyncio.sleep(2.0)

    navigation.start()
    await asyncio.sleep(2.0)


 

    print("\n==============================")
    print("[MISSION] Moving to B")
    print("==============================")

    success = await navigation.goto_and_wait(
        *WAYPOINTS["B"],
        timeout=60.0,
    )

    if not success:
        print(
            f"[MISSION] Failed to reach B. "
            f"Reason: {navigation.state}"
        )
        return

    print("[MISSION] Arrived at B.")


    
    print("\n==============================")
    print("[MISSION] A -> B completed")
    print("==============================")


    # 프로그램 유지
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\n[SYSTEM] Program stopped.")