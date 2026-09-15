from unitree_webrtc_connect.constants import RTC_TOPIC


class Go2Navigation:
    """Go2 내장 USLAM Navigation 제어."""

    def __init__(self, connection):
        self.conn = connection

        self.command_topic = RTC_TOPIC["LIDAR_MAPPING_CMD"]
        self.server_log_topic = RTC_TOPIC["LIDAR_MAPPING_SERVER_LOG"]

        self.navigation_active = False

    def _send_command(self, command: str):
        """USLAM 명령 전송."""
        print(f"[NAV CMD] {command}")

        self.conn.datachannel.pub_sub.publish_without_callback(
            self.command_topic,
            command,
        )

    def subscribe_server_log(self):
        """Navigation/SLAM 상태 메시지 수신 시작."""

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
        """USLAM 상태 메시지 처리."""
        if not isinstance(data, str):
            return

        if "navigation/state_transition/REACHED" in data:
            print("[NAV STATE] GOAL_REACHED")

        elif "navigation/state_transition/NO_PATH" in data:
            print("[NAV STATE] PATH_BLOCKED")

        elif "navigation/state_transition/TIMEOUT" in data:
            print("[NAV STATE] NAV_TIMEOUT")

        elif "navigation/state_transition/GOAL_OCCUPIED" in data:
            print("[NAV STATE] GOAL_OCCUPIED")

        elif "navigation/state_transition/FAILURE" in data:
            print("[NAV STATE] NAV_FAILURE")

        elif "navigation/state_transition/TRACKING" in data:
            print("[NAV STATE] TRACKING")

    def start(self):
        self._send_command("navigation/start")
        self.navigation_active = True

    def stop(self):
        self._send_command("navigation/stop")
        self.navigation_active = False

    def get_status(self):
        self._send_command("navigation/get_status")

    def start_localization(self):
        self._send_command("localization/start")

    def get_localization_status(self):
        self._send_command("localization/get_status")

    def goto(self, x: float, y: float, yaw: float):
        """지도 좌표(x, y, yaw)로 이동."""

        if not self.navigation_active:
            self.start()

        command = (
            f"navigation/set_goal_pose/"
            f"{x:.3f}/{y:.3f}/{yaw:.3f}"
        )

        self._send_command(command)