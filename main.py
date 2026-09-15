import asyncio

from robot.connection import Go2Connection
from robot.navigation import Go2Navigation


async def main():
    # 1. Go2 연결
    robot = Go2Connection()
    conn = await robot.connect()

    # 2. Navigation 객체 생성
    navigation = Go2Navigation(conn)

    # 3. USLAM 상태 메시지 구독
    navigation.subscribe_server_log()

    print("[SYSTEM] Go2 Navigation system ready.")

    # 아직 로봇을 움직이지 않는다.
    # navigation.start()
    # navigation.goto(1.0, 0.0, 0.0)

    # 메시지 수신을 위해 프로그램 유지
    await asyncio.sleep(30)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SYSTEM] Program stopped.")