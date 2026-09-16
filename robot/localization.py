import math
from unitree_webrtc_connect.constants import RTC_TOPIC


class Go2Localization:
    """Go2 USLAM Localization 및 로봇 위치 관리."""

    def __init__(self, connection):
        self.conn = connection

        self.command_topic = RTC_TOPIC["LIDAR_MAPPING_CMD"]
        self.odom_topic = "rt/uslam/localization/odom"

        self.x = None
        self.y = None
        self.z = None
        self.yaw = None

    # =====================================================
    # Command
    # =====================================================

    def _send_command(self, command: str):
        print(f"[LOC CMD] {command}")

        self.conn.datachannel.pub_sub.publish_without_callback(
            self.command_topic,
            command,
        )

    # =====================================================
    # Localization 명령
    # =====================================================

    def start(self):
        # 이전 localization에서 남아 있던 pose 제거
        self.x = None
        self.y = None
        self.z = None
        self.yaw = None

        self._send_command("localization/start")

    def stop(self):
        self._send_command("localization/stop")

    def get_status(self):
        self._send_command("localization/get_status")

    def set_initial_pose(
        self,
        x: float,
        y: float,
        yaw: float,
    ):
        """
        기존 지도에서 로봇의 초기 위치 지정.
        UI의 Set Initial Pose와 동일한 명령.
        """

        command = (
            f"localization/set_initial_pose/"
            f"{x:.3f}/{y:.3f}/{yaw:.3f}"
        )

        self._send_command(command)

    # =====================================================
    # Pose 수신
    # =====================================================

    def subscribe_pose(self):
        self.conn.datachannel.pub_sub.subscribe(
            self.odom_topic,
            self._pose_callback,
        )

        print("[LOC] Localization odometry subscribed.")

    def _pose_callback(self, message):
        data = message.get("data", {})

        try:
            pose = data["pose"]["pose"]

            position = pose["position"]
            orientation = pose["orientation"]

            self.x = float(position["x"])
            self.y = float(position["y"])
            self.z = float(position["z"])

            qx = float(orientation["x"])
            qy = float(orientation["y"])
            qz = float(orientation["z"])
            qw = float(orientation["w"])

            self.yaw = math.atan2(
                2.0 * (qw * qz + qx * qy),
                1.0 - 2.0 * (qy * qy + qz * qz),
            )

            print(
                f"[POSE] "
                f"x={self.x:.3f}, "
                f"y={self.y:.3f}, "
                f"z={self.z:.3f}, "
                f"yaw={self.yaw:.3f}"
            )

        except (KeyError, TypeError, ValueError):
            print(
                "[LOC] Unknown odometry format:",
                data,
            )

    # =====================================================
    # 현재 Pose
    # =====================================================

    def get_pose(self):
        if self.x is None:
            return None

        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "yaw": self.yaw,
        }