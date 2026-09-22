import asyncio
import json
import math
import os

from unitree_webrtc_connect.webrtc_driver import (
    UnitreeWebRTCConnection,
    WebRTCConnectionMethod,
)
from unitree_webrtc_connect.constants import RTC_TOPIC, SPORT_CMD


ROBOT_IP = "192.168.0.101"

YAW_SPEED = 0.5
TARGET_DEG = 360.0
MAX_TIME = 40.0


# sportmodestate 예제와 동일한 방식
current_yaw = None


def sportmodestatus_callback(message):
    global current_yaw

    try:
        # ★ 공식 예제의 핵심
        current_message = message["data"]

        imu_state = current_message["imu_state"]
        rpy = imu_state["rpy"]

        # roll = rpy[0]
        # pitch = rpy[1]
        # yaw = rpy[2]

        current_yaw = rpy[2]

    except Exception as e:
        print("[STATE ERROR]", e)


def angle_diff(new_angle, old_angle):
    """
    +pi / -pi 경계를 넘어가도
    실제 작은 회전량을 계산
    """
    return math.atan2(
        math.sin(new_angle - old_angle),
        math.cos(new_angle - old_angle)
    )


async def stop_robot(conn):

    await conn.datachannel.pub_sub.publish_request_new(
        RTC_TOPIC["SPORT_MOD"],
        {
            "api_id": SPORT_CMD["StopMove"]
        }
    )

    print("\n[ROTATE] STOP")


async def main():

    global current_yaw

    # =====================================
    # WebRTC 연결
    # =====================================

    aes_key = os.environ.get("GO2_AES_KEY")

    if not aes_key:
        raise RuntimeError(
            "GO2_AES_KEY가 설정되지 않았습니다."
        )

    print(f"[GO2] Connecting to {ROBOT_IP}...")

    conn = UnitreeWebRTCConnection(
        WebRTCConnectionMethod.LocalSTA,
        ip=ROBOT_IP,
        aes_128_key=aes_key,
    )

    await conn.connect()

    print("[GO2] Connected.")

    # =====================================
    # SportModeState 구독
    # ★ 예제와 동일
    # =====================================

    print("[STATE] Subscribe SportModeState")

    conn.datachannel.pub_sub.subscribe(
        RTC_TOPIC["LF_SPORT_MOD_STATE"],
        sportmodestatus_callback
    )

    # =====================================
    # yaw 들어올 때까지 기다림
    # =====================================

    print("[STATE] Waiting for yaw...")

    for _ in range(100):

        if current_yaw is not None:
            break

        await asyncio.sleep(0.1)

    if current_yaw is None:
        raise RuntimeError(
            "SportModeState yaw 수신 실패"
        )

    print(
        f"[STATE] yaw = "
        f"{math.degrees(current_yaw):.2f}°"
    )

    # =====================================
    # Motion mode 확인
    # =====================================

    response = await conn.datachannel.pub_sub.publish_request_new(
        RTC_TOPIC["MOTION_SWITCHER"],
        {
            "api_id": 1001
        }
    )

    original_mode = None

    try:

        data = json.loads(
            response["data"]["data"]
        )

        original_mode = data["name"]

        print(
            f"[MODE] Current = {original_mode}"
        )

    except Exception as e:

        print("[MODE ERROR]", e)

    # =====================================
    # normal mode
    # =====================================

    if original_mode != "normal":

        print(
            f"[MODE] {original_mode} -> normal"
        )

        await conn.datachannel.pub_sub.publish_request_new(
            RTC_TOPIC["MOTION_SWITCHER"],
            {
                "api_id": 1002,
                "parameter": {
                    "name": "normal"
                }
            }
        )

        await asyncio.sleep(5)

    # =====================================
    # 360도 회전
    # =====================================

    previous_yaw = current_yaw

    total_angle = 0.0

    loop = asyncio.get_running_loop()
    start_time = loop.time()

    print()
    print("==========================")
    print("      ROTATE 360")
    print("==========================")

    try:

        while True:

            elapsed = loop.time() - start_time

            if elapsed > MAX_TIME:

                print(
                    "\n[SAFETY] Timeout"
                )

                break

            # -----------------------------
            # 회전 명령
            # -----------------------------

            await conn.datachannel.pub_sub.publish_request_new(
                RTC_TOPIC["SPORT_MOD"],
                {
                    "api_id": SPORT_CMD["Move"],
                    "parameter": {
                        "x": 0.0,
                        "y": 0.0,
                        "z": YAW_SPEED
                    }
                }
            )

            # -----------------------------
            # SportModeState yaw
            # -----------------------------

            new_yaw = current_yaw

            if new_yaw is None:

                await asyncio.sleep(0.05)
                continue

            delta = angle_diff(
                new_yaw,
                previous_yaw
            )

            # 현재 회전 방향만 누적
            if delta > 0:
                total_angle += delta

            previous_yaw = new_yaw

            total_deg = math.degrees(
                total_angle
            )

            print(
                f"\r"
                f"[ROTATE] "
                f"yaw={math.degrees(new_yaw):7.2f}° | "
                f"total={total_deg:7.2f}° / 360°",
                end="",
                flush=True
            )

            # -----------------------------
            # 360도
            # -----------------------------

            if total_deg >= TARGET_DEG:

                print()
                print(
                    "[ROTATE] 360° reached!"
                )

                break

            await asyncio.sleep(0.05)

    finally:

        await stop_robot(conn)

    # =====================================
    # 결과
    # =====================================

    print(
        f"[RESULT] Total rotation = "
        f"{math.degrees(total_angle):.2f}°"
    )

    print(
        f"[RESULT] Final yaw = "
        f"{math.degrees(current_yaw):.2f}°"
    )

    # =====================================
    # 원래 mode 복귀
    # =====================================

    if (
        original_mode
        and original_mode != "normal"
    ):

        print(
            f"[MODE] normal -> "
            f"{original_mode}"
        )

        await conn.datachannel.pub_sub.publish_request_new(
            RTC_TOPIC["MOTION_SWITCHER"],
            {
                "api_id": 1002,
                "parameter": {
                    "name": original_mode
                }
            }
        )

        await asyncio.sleep(3)

        print(
            f"[MODE] Restored = "
            f"{original_mode}"
        )

    print("[TEST] Finished.")


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\n[STOP] Ctrl+C")
