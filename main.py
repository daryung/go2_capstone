import asyncio

from robot.connection import Go2Connection
from robot.navigation import Go2Navigation
from robot.localization import Go2Localization


async def main():

    # 1. Go2 연결
    robot = Go2Connection()
    conn = await robot.connect()

    # 2. Navigation
    navigation = Go2Navigation(conn)
    navigation.subscribe_server_log()

    # 3. Localization
    localization = Go2Localization(conn)
    localization.subscribe_pose()

    print("[SYSTEM] Go2 system ready.")

    # 상태 확인만 요청
    localization.get_status()
    navigation.get_status()

    # 아직 로봇을 움직이지 않음
    # localization.start()
    # navigation.start()
    # navigation.goto(1.0, 0.0, 0.0)

    # 메시지 수신 대기
    await asyncio.sleep(30)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SYSTEM] Program stopped.")