import math

from unitree_webrtc_connect.constants import RTC_TOPIC


class Go2Localization:
    """Go2 USLAM Localization 및 로봇 위치 관리."""

    def __init__(self, connection):
        self.conn = connection

        self.command_topic = RTC_TOPIC["LIDAR_MAPPING_CMD"]

        # unitree_webrtc_connect constants에 이름이 없을 경우를 대비해
        # 실제 USLAM topic을 직접 사용한다.
        self.odom_topic = "rt/uslam/localization/odom"

        self.x = None
        self.y = None
        self.z = None
        self.yaw = None

    def _send_command(self, command: str):
        print(f"[LOC CMD] {command}")

        self.conn.datachannel.pub_sub.publish_without_callback(
            self.command_topic,
            command,
        )

    def start(self):
        self._send_command("localization/start")

    def stop(self):
        self._send_command("localization/stop")

    def get_status(self):
        self._send_command("localization/get_status")

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
            print("[LOC] Unknown odometry format:", data)

    def get_pose(self):
        if self.x is None:
            return None

        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "yaw": self.yaw,
        }