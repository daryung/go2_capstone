import asyncio
import math


class Go2Rotation:
    def __init__(self, connection, localization, sport):
        self.conn = connection
        self.localization = localization
        self.sport = sport

    @staticmethod
    def angle_diff(target, current):
        """-pi ~ +pi 범위의 최단 각도 차이"""
        return math.atan2(
            math.sin(target - current),
            math.cos(target - current)
        )

    async def rotate(self, degrees, yaw_speed=0.3, tolerance_deg=3.0):
        """
        현재 위치에서 지정한 각도만큼 회전.

        degrees > 0 : 한쪽 방향
        degrees < 0 : 반대 방향
        """

        pose = self.localization.get_pose()

        if pose is None:
            raise RuntimeError("Localization pose가 없습니다.")

        current_yaw = pose["yaw"]

        target_yaw = current_yaw + math.radians(degrees)

        # -pi ~ pi 정규화
        target_yaw = math.atan2(
            math.sin(target_yaw),
            math.cos(target_yaw)
        )

        tolerance = math.radians(tolerance_deg)

        print(
            f"[ROTATE] {degrees:.1f}° 회전 시작 "
            f"({math.degrees(current_yaw):.1f}° "
            f"→ {math.degrees(target_yaw):.1f}°)"
        )

        try:
            while True:
                pose = self.localization.get_pose()

                if pose is None:
                    await asyncio.sleep(0.05)
                    continue

                current_yaw = pose["yaw"]

                error = self.angle_diff(
                    target_yaw,
                    current_yaw
                )

                # 목표 각도 도달
                if abs(error) <= tolerance:
                    break

                # 목표 방향에 따라 회전
                direction = 1.0 if error > 0 else -1.0

                await self.sport.move(
                    0.0,
                    0.0,
                    direction * yaw_speed
                )

                await asyncio.sleep(0.05)

        finally:
            await self.sport.stop_move()

        final_yaw = self.localization.get_pose()["yaw"]

        print(
            f"[ROTATE] 완료: "
            f"{math.degrees(final_yaw):.1f}°"
        )

        return True