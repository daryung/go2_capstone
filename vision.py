import asyncio
import cv2

from ultralytics import YOLO

# 기존에 만들어둔 Go2 연결 클래스 사용
from robot.connection import Go2Connection



ROBOT_IP = "192.168.0.101"

MODEL_PATH = "yolo11n.pt"

CONFIDENCE = 0.4

# 찾을 물건 카테고리 (COCO class)
TARGET_CLASS = "refrigerator"

#종료 q



print("[YOLO] Loading model...")

model = YOLO(MODEL_PATH)

print("[YOLO] Model loaded.")


async def video_callback(track):

    print("[VISION] Video track received.")
    print("[VISION] Object detection started.")

    try:

        while True:



            frame = await track.recv()
            image = frame.to_ndarray(format="bgr24")


            results = model.predict(
                source=image,
                conf=CONFIDENCE,
                verbose=False
            )

            result = results[0]


            # -------------------------------------------------
            # 하드코딩된 목표물(refrigerator) 탐지 상태 계산
            # -------------------------------------------------
            target_count = 0
            target_confidences = []

            if result.boxes is not None:
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    class_name = model.names[class_id]

                    if class_name == TARGET_CLASS:
                        target_count += 1
                        target_confidences.append(confidence)

            if target_count > 0:
                target_status = "FOUND"
                status_text = f"FOUND | refrigerator count: {target_count}"
                print(
                    f"\r[TARGET] status={target_status} | "
                    f"category={TARGET_CLASS} | count={target_count}",
                    end="",
                    flush=True,
                )
            else:
                target_status = "NOT_FOUND"
                status_text = "NOT_FOUND | refrigerator count: 0"
                print(
                    f"\r[TARGET] status={target_status} | "
                    f"category={TARGET_CLASS} | count=0",
                    end="",
                    flush=True,
                )

            annotated_frame = result.plot()

            # 영상 화면에도 상태값/개수 표시
            cv2.putText(
                annotated_frame,
                f"TARGET: {TARGET_CLASS}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            cv2.putText(
                annotated_frame,
                status_text,
                (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )


            cv2.imshow(
                "Go2 YOLO Object Detection",
                annotated_frame
            )

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



async def main():

    print()
    print("========================================")
    print(" Go2 Real-Time Object Detection")
    print("========================================")
    print()

    go2 = Go2Connection(
        ip=ROBOT_IP
    )



    try:

        conn = await go2.connect()

    except Exception as e:

        print()
        print("[GO2 ERROR] Connection failed.")
        print(e)

        return


    print()
    print("[VISION] Go2 connection ready.")


    if not hasattr(conn, "video"):

        print(
            "[VISION ERROR] "
            "Video channel does not exist."
        )

        return


    print("[VISION] Video channel found.")


    conn.video.add_track_callback(
        video_callback
    )

    print(
        "[VISION] Video callback registered."
    )

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


    try:

        while True:

            await asyncio.sleep(1)


    except KeyboardInterrupt:

        print()
        print("[PROGRAM] Ctrl+C")


    finally:

        cv2.destroyAllWindows()


if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        cv2.destroyAllWindows()

        print()
        print("[PROGRAM] Stopped.")