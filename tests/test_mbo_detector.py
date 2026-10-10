"""
test_mbo_detector.py
모델 파일(mbo_final.pt) 없이도 돌아가는 구조 확인용 테스트.
가짜 모델을 끼워서 "결과 형태"와 "실패 구분"이 맞는지만 본다.
(실제 탐지 성능은 이 테스트로 확인되지 않는다)

실행:  python test_mbo_detector.py
"""

import json
import os
import shutil
import tempfile

import cv2
import numpy as np

from vision.mbo_detector import MBODetector, to_flat_row, to_observation, CLASS_NAMES


# ---------------- 가짜 모델 (Ultralytics 결과 모양만 흉내)
class _Boxes:
    def __init__(self, rows):
        a = np.array(rows, dtype=float).reshape(-1, 6)
        self.xyxy, self.conf, self.cls = a[:, :4], a[:, 4], a[:, 5]

    def __len__(self):
        return len(self.cls)


class _Res:
    def __init__(self, rows):
        self.boxes = _Boxes(rows)


class FakeModel:
    names = dict(CLASS_NAMES)

    def __init__(self, rows=None, crash=False):
        self.rows, self.crash, self.last_kwargs = rows or [], crash, None

    def predict(self, **kwargs):
        self.last_kwargs = kwargs
        if self.crash:
            raise RuntimeError("일부러 낸 추론 오류")
        return [_Res(self.rows)]


def make_frame():
    rng = np.random.default_rng(0)
    return rng.integers(0, 255, size=(480, 640, 3), dtype=np.uint8)


TMP = tempfile.mkdtemp(prefix="det_test_")
passed = 0


def check(name, cond):
    global passed
    assert cond, f"실패: {name}"
    passed += 1
    print(f"  통과  {name}")


# x1, y1, x2, y2, conf, cls
ROWS = [
    [10, 10, 100, 100, 0.91, 3],    # starfish
    [200, 50, 300, 150, 0.55, 3],   # starfish
    [50, 300, 120, 380, 0.40, 2],   # scallop
    [400, 300, 460, 360, 0.30, 1],  # echinus
]

print("[1] ndarray 입력, 정상 탐지")
fake = FakeModel(ROWS)
det = MBODetector(model=fake, save_dir=TMP)
r = det.detect(make_frame(), point_id="P1_MAIN")
check("status OK", r["status"] == "OK" and r["error"] is None)
check("네 클래스 count", r["counts"] == {"holothurian": 0, "echinus": 1, "scallop": 1, "starfish": 2})
check("total_count", r["total_count"] == 4)
check("conf max/mean/values", r["confidence"]["starfish"] == {"max": 0.91, "mean": 0.73, "values": [0.91, 0.55]})
check("탐지 없는 클래스 conf 는 None", r["confidence"]["holothurian"] == {"max": None, "mean": None, "values": []})
check("bbox 형태", r["detections"][0]["bbox_xyxy"] == [10.0, 10.0, 100.0, 100.0])
check("conf/iou/imgsz 기록", (r["model"]["conf"], r["model"]["iou"], r["model"]["imgsz"]) == (0.25, 0.7, 640))
check("모델에 같은 값 전달", (fake.last_kwargs["conf"], fake.last_kwargs["iou"], fake.last_kwargs["imgsz"]) == (0.25, 0.7, 640))
check("원본/박스 이미지 저장", os.path.isfile(r["image"]["image_path"]) and os.path.isfile(r["image"]["annotated_image_path"]))
check("추론 시간 기록", isinstance(r["inference_ms"], float))
check("JSON 변환 가능", bool(json.dumps(r, ensure_ascii=False)))

print("[2] 탐지 0개 (봤는데 없었다)")
r0 = MBODetector(model=FakeModel([]), save_dir=TMP).detect(make_frame(), point_id="P1_SIDE")
check("status OK", r0["status"] == "OK")
check("count 가 전부 0", all(v == 0 for v in r0["counts"].values()) and r0["total_count"] == 0)
check("detections 는 빈 목록", r0["detections"] == [])
check("0개여도 박스 이미지 저장", os.path.isfile(r0["image"]["annotated_image_path"]))

print("[3] 프레임 실패 (보지 못했다)")
d = MBODetector(model=FakeModel(ROWS), save_dir=TMP)
cases = {
    "None": (None, "FRAME_NONE"),
    "없는 파일": (os.path.join(TMP, "nope.jpg"), "FILE_NOT_FOUND"),
    "빈 배열": (np.zeros((0, 0, 3), np.uint8), "FRAME_EMPTY"),
    "검은 화면": (np.zeros((480, 640, 3), np.uint8), "FRAME_BLANK"),
    "깨진 bytes": (b"not an image", "IMAGE_DECODE_FAILED"),
    "이상한 타입": (12345, "FRAME_BAD_TYPE"),
}
for label, (src, code) in cases.items():
    rf = d.detect(src)
    check(f"{label} -> FRAME_FAILED/{code}",
          rf["status"] == "FRAME_FAILED" and rf["error"]["code"] == code
          and all(v is None for v in rf["counts"].values())
          and rf["total_count"] is None and rf["detections"] is None)
bad = os.path.join(TMP, "broken.jpg")
with open(bad, "wb") as f:
    f.write(b"xxxx")
check("깨진 파일 -> IMAGE_DECODE_FAILED", d.detect(bad)["error"]["code"] == "IMAGE_DECODE_FAILED")

print("[4] 추론 실패")
ri = MBODetector(model=FakeModel(crash=True), save_dir=TMP).detect(make_frame())
check("PREDICT_FAILED", ri["status"] == "INFERENCE_FAILED" and ri["error"]["code"] == "PREDICT_FAILED")
check("count 는 None (0 아님)", all(v is None for v in ri["counts"].values()))
rm = MBODetector(weights=os.path.join(TMP, "no_weights.pt"), save_dir=TMP).detect(make_frame())
check("가중치 없음 -> MODEL_LOAD_FAILED", rm["status"] == "INFERENCE_FAILED" and rm["error"]["code"] == "MODEL_LOAD_FAILED")
ru = MBODetector(model=FakeModel([[0, 0, 5, 5, 0.9, 7]]), save_dir=TMP).detect(make_frame())
check("모르는 클래스 번호 -> INFERENCE_FAILED", ru["status"] == "INFERENCE_FAILED")

print("[5] 경로 / bytes / 흑백 입력")
p = os.path.join(TMP, "sample.jpg")
cv2.imwrite(p, make_frame())
rp = d.detect(p)
check("경로 입력 OK, image_path 는 원본 경로", rp["status"] == "OK" and rp["image"]["image_path"] == p)
ok, enc = cv2.imencode(".jpg", make_frame())
check("JPEG bytes 입력 OK", d.detect(enc.tobytes())["status"] == "OK")
check("흑백 ndarray 입력 OK", d.detect(make_frame()[:, :, 0])["status"] == "OK")

print("[6] DB 용 납작한 형태")
row = to_flat_row(r)
check("starfish_count / conf", (row["starfish_count"], row["starfish_conf_max"], row["starfish_conf_mean"]) == (2, 0.91, 0.73))
check("실패 시 count 는 None", to_flat_row(d.detect(None))["starfish_count"] is None)

print("[7] save_observation() 용 4개 값")
check("정상: shell 은 가리비, confidence 는 평균",
      to_observation(r) == {"starfish_count": 2, "starfish_confidence": 0.73, "shell_count": 1, "shell_confidence": 0.4})
check("0개: count 0, confidence 0.0",
      to_observation(r0) == {"starfish_count": 0, "starfish_confidence": 0.0, "shell_count": 0, "shell_confidence": 0.0})
check("실패: 네 값 모두 None", all(v is None for v in to_observation(d.detect(None)).values()))

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n전체 {passed}개 통과")
