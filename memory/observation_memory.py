import sqlite3
from datetime import datetime
from pathlib import Path


# observation_memory.py와 같은 폴더의 DB 사용
DB_PATH = Path(__file__).parent / "observation_memory.db"


def connect_db():
    return sqlite3.connect(DB_PATH)


def save_observation(
    point_id,
    robot_x,
    robot_y,
    robot_yaw,
    navigation_state,
    starfish_count=None,
    starfish_confidence=None,
    shell_count=None,
    shell_confidence=None
):
    """현재 관측 결과를 SQLite에 저장"""

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO observations (
            timestamp,
            point_id,
            robot_x,
            robot_y,
            robot_yaw,
            navigation_state,
            starfish_count,
            starfish_confidence,
            shell_count,
            shell_confidence
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(timespec="seconds"),
        point_id,
        robot_x,
        robot_y,
        robot_yaw,
        navigation_state,
        starfish_count,
        starfish_confidence,
        shell_count,
        shell_confidence
    ))

    observation_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return observation_id


def get_history(point_id, limit=5, exclude_id=None):
    """특정 관측지점의 최근 관측 기록 조회"""

    conn = connect_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if exclude_id is None:
        cursor.execute("""
            SELECT *
            FROM observations
            WHERE point_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (point_id, limit))
    else:
        cursor.execute("""
            SELECT *
            FROM observations
            WHERE point_id = ?
              AND id != ?
            ORDER BY id DESC
            LIMIT ?
        """, (point_id, exclude_id, limit))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def save_decision(observation_id, situation, action, reason):
    """LLM의 판단 결과를 해당 Observation에 저장"""

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE observations
        SET situation = ?,
            action = ?,
            reason = ?
        WHERE id = ?
    """, (
        situation,
        action,
        reason,
        observation_id
    ))

    conn.commit()
    conn.close()


# 단독 실행 테스트
if __name__ == "__main__":

    print("=== Observation Memory Test ===")

    observation_id = save_observation(
        point_id="B",
        robot_x=0.52,
        robot_y=1.21,
        robot_yaw=1.57,
        navigation_state="REACHED",
        starfish_count=0,
        starfish_confidence=0.38,
        shell_count=1,
        shell_confidence=0.42
    )

    print(f"\n현재 Observation 저장 완료: ID={observation_id}")

    history = get_history(
        point_id="B",
        limit=5,
        exclude_id=observation_id
    )

    print("\n=== B 지점 과거 Observation ===")

    for obs in history:
        print(
            f"ID={obs['id']} | "
            f"time={obs['timestamp']} | "
            f"starfish={obs['starfish_count']} "
            f"(conf={obs['starfish_confidence']}) | "
            f"shell={obs['shell_count']} "
            f"(conf={obs['shell_confidence']})"
        )