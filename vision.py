import asyncio
import cv2

from ultralytics import YOLO

# 기존에 만들어둔 Go2 연결 클래스 사용
from robot.connection import Go2Connection


# ============================================================
# 설정
# ============================================================

ROBOT_IP = "192.168.0.101"

MODEL_PATH = "yolo11n.pt"

CONFIDENCE = 0.4


# ============================================================
# YOLO
# ============================================================

print("[YOLO] Loading model...")

model = YOLO(MODEL_PATH)

print("[YOLO] Model loaded.")


# ============================================================
# Video Callback
# ============================================================

async def video_callback(track):

    print("[VISION] Video track received.")
    print("[VISION] Object detection started.")

    try:

        while True:

            # ================================================
            # Go2 카메라 프레임 수신
            # ================================================

            frame = await track.recv()

            # aiortc frame -> OpenCV image
            image = frame.to_ndarray(format="bgr24")


            # ================================================
            # YOLO 객체 탐지
            # ================================================

            results = model.predict(
                source=image,
                conf=CONFIDENCE,
                verbose=False
            )

            result = results[0]


            # ================================================
            # 탐지 결과 터미널 출력
            # ================================================

            if result.boxes is not None:

                detected_objects = []

                for box in result.boxes:

                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])

                    class_name = model.names[class_id]

                    detected_objects.append(
                        f"{class_name} {confidence:.2f}"
                    )

                if detected_objects:

                    print(
                        "[DETECTED]",
                        ", ".join(detected_objects)
                    )


            # ================================================
            # Bounding Box 그리기
            # ================================================

            annotated_frame = result.plot()


            # ================================================
            # 영상 출력
            # ================================================

            cv2.imshow(
                "Go2 YOLO Object Detection",
                annotated_frame
            )


            # Q 누르면 종료
            if cv2.waitKey(1) & 0xFF == ord("q"):

                print("[VISION] Q pressed.")

                break


    except asyncio.CancelledError:

        print("[VISION] Video task cancelled.")


    except Exception as e:

        print(
            f"[VISION ERROR] {type(e).__name__}: {e}"
        )


    finally:

        cv2.destroyAllWindows()


# ============================================================
# Main
# ============================================================

async def main():

    print()
    print("========================================")
    print(" Go2 Real-Time Object Detection")
    print("========================================")
    print()


    # ================================================
    # 기존 connection.py 사용
    # ================================================

    go2 = Go2Connection(
        ip=ROBOT_IP
    )


    # ================================================
    # Go2 연결
    #
    # connection.py 내부에서
    # GO2_AES_KEY를 읽어 AES 인증까지 처리
    # ================================================

    try:

        conn = await go2.connect()

    except Exception as e:

        print()
        print("[GO2 ERROR] Connection failed.")
        print(e)

        return


    print()
    print("[VISION] Go2 connection ready.")


    # ================================================
    # Video Channel 확인
    # ================================================

    if not hasattr(conn, "video"):

        print(
            "[VISION ERROR] "
            "Video channel does not exist."
        )

        return


    print("[VISION] Video channel found.")


    # ================================================
    # Callback 등록
    # ================================================

    conn.video.add_track_callback(
        video_callback
    )

    print(
        "[VISION] Video callback registered."
    )


    # ================================================
    # 카메라 활성화
    # ================================================

    try:

        conn.video.switchVideoChannel(True)

        print(
            "[VISION] Video channel enabled."
        )

    except Exception as e:

        print(
            "[VISION WARNING] "
            f"Video channel switch failed: {e}"
        )


    print()
    print("----------------------------------------")
    print("Waiting for Go2 camera stream...")
    print("Press Q on the video window to quit.")
    print("----------------------------------------")
    print()


    # ================================================
    # 프로그램 유지
    # ================================================

    try:

        while True:

            await asyncio.sleep(1)


    except KeyboardInterrupt:

        print()
        print("[PROGRAM] Ctrl+C")


    finally:

        cv2.destroyAllWindows()


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        cv2.destroyAllWindows()

        print()
        print("[PROGRAM] Stopped.")