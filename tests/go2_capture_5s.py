"""Go2 Edu WebRTC 카메라 사진을 5초마다 저장한다.

실행: python go2_capture_5s.py
변경: python go2_capture_5s.py --interval 3 --output captures
종료: Ctrl+C
"""
import argparse
import asyncio
import time
from datetime import datetime
from pathlib import Path

import cv2
from robot.connection import Go2Connection


async def main(interval: float, output: Path, ip: str, quality: int):
    if interval <= 0:
        raise ValueError("interval must be greater than zero")

    output = output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    stopped = asyncio.Event()
    count = 0
    next_capture = None

    async def video_callback(track):
        nonlocal count, next_capture
        print("[CAMERA] Video track connected. Capturing frames...")
        try:
            while not stopped.is_set():
                frame = await track.recv()
                now = time.monotonic()
                if next_capture is None:
                    next_capture = now  # 첫 프레임 즉시 저장
                if now < next_capture:
                    continue

                image = frame.to_ndarray(format="bgr24")
                if image is None or image.size == 0:
                    print("[WARNING] Empty camera frame; skipping")
                    continue

                stamp = datetime.now()
                day_dir = output / stamp.strftime("%Y-%m-%d")
                day_dir.mkdir(parents=True, exist_ok=True)
                filename = day_dir / f"go2_{stamp:%Y%m%d_%H%M%S_%f}.jpg"
                ok = cv2.imwrite(str(filename), image, [cv2.IMWRITE_JPEG_QUALITY, quality])
                if ok:
                    count += 1
                    print(f"[SAVE {count:04d}] {filename}  ({image.shape[1]}x{image.shape[0]})", flush=True)
                else:
                    print(f"[ERROR] Could not save: {filename}")

                # 저장 처리 지연으로 밀린 구간은 건너뛰고 일정한 간격 유지
                while next_capture <= time.monotonic():
                    next_capture += interval
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            print(f"[CAMERA ERROR] {type(exc).__name__}: {exc}")
            stopped.set()
        finally:
            print("[CAMERA] Video callback stopped")

    print("====================================")
    print(" Go2 Edu WebRTC Photo Capture")
    print(f" IP       : {ip}")
    print(f" Interval : {interval:g} seconds")
    print(f" Output   : {output}")
    print(" Stop     : Ctrl+C")
    print("====================================")

    go2 = Go2Connection(ip=ip)
    conn = await go2.connect()
    if not hasattr(conn, "video"):
        raise RuntimeError("Go2 connection has no video channel")

    conn.video.add_track_callback(video_callback)
    conn.video.switchVideoChannel(True)
    print("[CAMERA] Waiting for WebRTC camera stream...")
    try:
        await stopped.wait()
    finally:
        stopped.set()
        try:
            conn.video.switchVideoChannel(False)
        except Exception as exc:
            print(f"[WARNING] Could not disable video channel: {exc}")
        print(f"[DONE] Saved {count} images")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Save Go2 Edu camera frames at fixed intervals")
    parser.add_argument("--interval", type=float, default=5.0, help="Capture interval in seconds (default: 5)")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "captures", help="Image directory")
    parser.add_argument("--ip", default="192.168.0.101", help="Go2 IP address")
    parser.add_argument("--quality", type=int, default=95, choices=range(1, 101), metavar="1-100", help="JPEG quality (default: 95)")
    args = parser.parse_args()
    try:
        asyncio.run(main(args.interval, args.output, args.ip, args.quality))
    except KeyboardInterrupt:
        print("\n[STOP] User interrupted")
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}")
        raise SystemExit(1)
