import asyncio
from unitree_webrtc_connect.constants import RTC_TOPIC


class Go2Navigation:
    def __init__(self, connection):
        self.conn = connection

        self.command_topic = RTC_TOPIC["LIDAR_MAPPING_CMD"]
        self.server_log_topic = RTC_TOPIC["LIDAR_MAPPING_SERVER_LOG"]

        self.navigation_active = False

        # Navigation 이벤트
        self.goal_reached = asyncio.Event()
        self.nav_failed = asyncio.Event()

        # Localization 실제 초기화 완료 이벤트
        self.localization_ready = asyncio.Event()

        self.state = "IDLE"


    def _send_command(self, command: str):
        print(f"[NAV CMD] {command}")

        self.conn.datachannel.pub_sub.publish_without_callback(
            self.command_topic,
            command,
        )


    def subscribe_server_log(self):
        def callback(message):
            data = message.get("data")

            print(f"[USLAM] {data}")

            self._handle_server_log(data)

        self.conn.datachannel.pub_sub.subscribe(
            self.server_log_topic,
            callback,
        )

        print("[NAV] USLAM server log subscribed.")

    def _handle_server_log(self, data):
        if not isinstance(data, str):
            return



        if "[Localization] initialization succeed!" in data:
            print("[LOC STATE] LOCALIZATION_READY")

            self.localization_ready.set()

            # Localization 메시지는 여기까지만 처리
            return



        if "navigation/state_transition/REACHED" in data:
            self.state = "GOAL_REACHED"

            print("[NAV STATE] GOAL_REACHED")

            self.goal_reached.set()

        elif "navigation/state_transition/NO_PATH" in data:
            self.state = "PATH_BLOCKED"

            print("[NAV STATE] PATH_BLOCKED")

            self.nav_failed.set()

        elif "navigation/state_transition/GOAL_OCCUPIED" in data:
            self.state = "GOAL_OCCUPIED"

            print("[NAV STATE] GOAL_OCCUPIED")

            self.nav_failed.set()

        elif "navigation/state_transition/FAILURE" in data:
            self.state = "NAV_FAILURE"

            print("[NAV STATE] NAV_FAILURE")

            self.nav_failed.set()

        elif "navigation/state_transition/TRACKING" in data:
            self.state = "TRACKING"

            print("[NAV STATE] TRACKING")

        elif "navigation/state_transition/WAITING" in data:
            self.state = "WAITING"

            print("[NAV STATE] WAITING")


        elif "navigation/state_transition/TIMEOUT_POINTCLOUD" in data:
            print("[NAV WARNING] POINTCLOUD_TIMEOUT")

        elif "navigation/state_transition/TIMEOUT_ODOMETRY" in data:
            print("[NAV WARNING] ODOMETRY_TIMEOUT")

        # 정말 generic TIMEOUT이 따로 오는 경우
        elif data.strip() == "navigation/state_transition/TIMEOUT":
            self.state = "NAV_TIMEOUT"

            print("[NAV STATE] NAV_TIMEOUT")

            self.nav_failed.set()

        elif "navigation/state_transition/ABNORMAL" in data:
            self.state = "ABNORMAL"

            print("[NAV STATE] ABNORMAL")


    def reset_localization_event(self):
        self.localization_ready.clear()

    async def wait_for_localization(self, timeout=20.0):
        print(
            "[SYSTEM] Waiting for REAL "
            "localization initialization..."
        )

        try:
            await asyncio.wait_for(
                self.localization_ready.wait(),
                timeout=timeout,
            )

            print(
                "[SYSTEM] Localization REALLY ready."
            )

            return True

        except asyncio.TimeoutError:
            print(
                "[ERROR] Localization "
                "initialization timeout."
            )

            return False


    def start(self):
        self._send_command("navigation/start")

        self.navigation_active = True

    def stop(self):
        self._send_command("navigation/stop")

        self.navigation_active = False

    def get_status(self):
        self._send_command("navigation/get_status")

    def goto(
        self,
        x: float,
        y: float,
        yaw: float,
    ):
        # 이전 목적지 결과 제거
        self.goal_reached.clear()
        self.nav_failed.clear()

        if not self.navigation_active:
            self.start()

        command = (
            f"navigation/set_goal_pose/"
            f"{x:.3f}/{y:.3f}/{yaw:.3f}"
        )

        self._send_command(command)

    async def goto_and_wait(
        self,
        x: float,
        y: float,
        yaw: float,
        timeout: float = 60.0,
    ):
        self.goto(x, y, yaw)

        print("[NAV] Waiting for result...")

        reached_task = asyncio.create_task(
            self.goal_reached.wait()
        )

        failed_task = asyncio.create_task(
            self.nav_failed.wait()
        )

        done, pending = await asyncio.wait(
            [
                reached_task,
                failed_task,
            ],
            timeout=timeout,
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()

        # timeout
        if not done:
            self.state = "NAV_TIMEOUT"

            print("[NAV] Navigation timeout.")

            return False

        # 목적지 도착
        if self.goal_reached.is_set():
            print("[NAV] Destination reached.")

            return True

        # 실패
        print(
            f"[NAV] Navigation failed: "
            f"{self.state}"
        )

        return False