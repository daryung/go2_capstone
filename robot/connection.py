import os

from unitree_webrtc_connect.webrtc_driver import (
    UnitreeWebRTCConnection,
    WebRTCConnectionMethod,
)


class Go2Connection:
    """Go2 WebRTC 연결을 관리하는 클래스."""

    def __init__(self, ip=None):
        self.ip = ip or os.environ.get("UNITREE_ROBOT_IP")
        self.conn = None

    async def connect(self):
        if not self.ip:
            raise ValueError(
                "Go2 IP가 설정되지 않았습니다. "
                "UNITREE_ROBOT_IP 환경변수를 설정해주세요."
            )

        print(f"[GO2] Connecting to {self.ip}...")

        self.conn = UnitreeWebRTCConnection(
            WebRTCConnectionMethod.LocalSTA,
            ip=self.ip,
        )

        await self.conn.connect()

        print("[GO2] Connected successfully.")
        return self.conn

    def get_connection(self):
        if self.conn is None:
            raise RuntimeError("Go2가 아직 연결되지 않았습니다.")

        return self.conn