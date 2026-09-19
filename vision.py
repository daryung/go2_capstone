import asyncio
import cv2

from ultralytics import YOLO

# 기존에 만들어둔 Go2 연결 클래스 사용
from robot.connection import Go2Connection



ROBOT_IP = "192.168.0.101"

MODEL_PATH = "yolo11n.pt"

CONFIDENCE = 0.4

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



            annotated_frame = result.plot()


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