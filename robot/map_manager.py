import asyncio
import base64
import time
import random

from unitree_webrtc_connect.constants import (
    RTC_TOPIC,
    DATA_CHANNEL_TYPE,
)


class Go2MapManager:
    def __init__(self, connection):
        self.conn = connection
        self.pub_sub = connection.datachannel.pub_sub
        self.command_topic = RTC_TOPIC["LIDAR_MAPPING_CMD"]

    # -------------------------------------------------
    # USLAM command
    # -------------------------------------------------
    def _send_command(self, command: str):
        print(f"[MAP CMD] {command}")

        self.pub_sub.publish_without_callback(
            self.command_topic,
            command,
        )

    # -------------------------------------------------
    # UUID
    # -------------------------------------------------
    def _generate_upload_uuid(self, chunk_index: int):
        value = (
            int(time.time() * 1000) % (2 ** 31)
            + random.randint(0, 999)
        )

        return f"upload_req_{value}_{chunk_index}"

    # -------------------------------------------------
    # Upload one file
    # -------------------------------------------------
    async def upload_file(
        self,
        local_path: str,
        robot_name: str,
        chunk_size: int = 30 * 1024,
    ):
        print(f"[MAP] Reading {local_path}")

        with open(local_path, "rb") as f:
            raw_data = f.read()

        encoded_data = base64.b64encode(
            raw_data
        ).decode("utf-8")

        print(
            f"[MAP] Uploading {robot_name} "
            f"({len(raw_data) / 1024:.1f} KB)"
        )

        chunks = [
            encoded_data[i:i + chunk_size]
            for i in range(
                0,
                len(encoded_data),
                chunk_size,
            )
        ]

        total_chunks = len(chunks)

        if total_chunks == 0:
            raise RuntimeError(
                f"{robot_name}: empty file"
            )

        print(
            f"[MAP] {robot_name}: "
            f"{total_chunks} chunks"
        )

        # ---------------------------------------------
        # Send chunks sequentially
        # ---------------------------------------------
        for index, chunk in enumerate(chunks):

            # UI/APK 동작과 동일하게
            # 5 chunk마다 잠깐 쉬기
            if index > 0 and index % 5 == 0:
                await asyncio.sleep(0.5)

            req_uuid = self._generate_upload_uuid(
                index
            )

            message = {
                "req_type": "push_static_file",
                "req_uuid": req_uuid,
                "related_bussiness": "uslam_final_pcd",
                "file_md5": "null",
                "file_path": robot_name,
                "file_size_after_b64": len(
                    encoded_data
                ),
                "file": {
                    "chunk_index": index + 1,
                    "total_chunk_num": total_chunks,
                    "chunk_data": chunk,
                    "chunk_data_size": len(chunk),
                },
            }

            try:
                # ★ 중요
                # 실제 로봇 응답을 await
                response = await asyncio.wait_for(
                    self.pub_sub.publish(
                        "",
                        message,
                        DATA_CHANNEL_TYPE[
                            "RTC_INNER_REQ"
                        ],
                    ),
                    timeout=10.0,
                )

            except asyncio.TimeoutError:
                raise RuntimeError(
                    f"{robot_name}: "
                    f"chunk {index + 1}/"
                    f"{total_chunks} ACK timeout"
                )

            # -----------------------------------------
            # Check robot ACK
            # -----------------------------------------
            info = (
                response.get("info", {})
                if isinstance(response, dict)
                else {}
            )

            status = info.get("file_status")

            if status != "ok":
                raise RuntimeError(
                    f"{robot_name}: "
                    f"chunk {index + 1}/"
                    f"{total_chunks} "
                    f"failed, status={status}, "
                    f"response={response}"
                )

            percent = int(
                ((index + 1) / total_chunks) * 100
            )

            print(
                f"[MAP] {robot_name}: "
                f"{percent}% "
                f"(ACK=ok)"
            )

        print(
            f"[MAP] {robot_name}: "
            f"UPLOAD COMPLETE"
        )

    # -------------------------------------------------
    # Upload complete map
    # -------------------------------------------------
    async def upload_map(
        self,
        pcd_path: str,
        pgm_path: str = None,
        txt_path: str = None,
    ):
        print("\n==============================")
        print("[MAP] Starting map upload")
        print("==============================")

        await self.upload_file(
            pcd_path,
            "map.pcd",
        )

        if pgm_path:
            await self.upload_file(
                pgm_path,
                "map.pgm",
            )

        if txt_path:
            await self.upload_file(
                txt_path,
                "map.txt",
            )

        print("\n[MAP] All map files uploaded.")

    # -------------------------------------------------
    # Activate map
    # -------------------------------------------------
    async def activate_map(
        self,
        map_id: str,
    ):
        print(
            f"[MAP] Activating map: {map_id}"
        )

        self._send_command(
            f"common/set_map_id/{map_id}"
        )

        # set_map_id 처리 시간
        await asyncio.sleep(1.0)