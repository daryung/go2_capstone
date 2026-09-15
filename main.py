import asyncio

from robot.connection import Go2Connection
from robot.navigation import Go2Navigation


async def main():

    robot = Go2Connection()
    conn = await robot.connect()

    navigation = Go2Navigation(conn)

    navigation.subscribe_server_log()

    print("[SYSTEM] Go2 Navigation system ready.")

   
    # navigation.start()
    # navigation.goto(1.0, 0.0, 0.0)

    
    await asyncio.sleep(30)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SYSTEM] Program stopped.")