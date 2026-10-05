from memory.observation_memory import save_observation


# =========================================================
# 가상 2회 순회 데이터
# =========================================================
#
# 1회차:
#   P1_MAIN → P1_SIDE → P2_MAIN
#
# 2회차:
#   P1_MAIN → P1_SIDE → P2_MAIN
#
# P1_MAIN의 2회차에서 일부러 이상 관측을 발생시킨다.
# =========================================================

fake_observations = [

    # -----------------------------------------------------
    # PATROL 1
    # -----------------------------------------------------

    {
        "point_id": "P1_MAIN",
        "robot_x": 2.380,
        "robot_y": -1.344,
        "robot_yaw": -0.020,
        "navigation_state": "GOAL_REACHED",

        "starfish_count": 3,
        "starfish_confidence": 0.91,

        "shell_count": 1,
        "shell_confidence": 0.88,
    },

    {
        "point_id": "P1_SIDE",
        "robot_x": 3.270,
        "robot_y": -2.410,
        "robot_yaw": 1.906,
        "navigation_state": "GOAL_REACHED",

        "starfish_count": 2,
        "starfish_confidence": 0.90,

        "shell_count": 2,
        "shell_confidence": 0.87,
    },

    {
        "point_id": "P2_MAIN",
        "robot_x": 2.260,
        "robot_y": -2.910,
        "robot_yaw": -2.946,
        "navigation_state": "GOAL_REACHED",

        "starfish_count": 4,
        "starfish_confidence": 0.93,

        "shell_count": 1,
        "shell_confidence": 0.91,
    },


    # -----------------------------------------------------
    # PATROL 2
    # -----------------------------------------------------

    # 일부러 P1_MAIN에서 이상 발생
    {
        "point_id": "P1_MAIN",
        "robot_x": 2.381,
        "robot_y": -1.346,
        "robot_yaw": -0.018,
        "navigation_state": "GOAL_REACHED",

        "starfish_count": 0,
        "starfish_confidence": 0.38,

        "shell_count": 1,
        "shell_confidence": 0.86,
    },

    {
        "point_id": "P1_SIDE",
        "robot_x": 3.269,
        "robot_y": -2.409,
        "robot_yaw": 1.905,
        "navigation_state": "GOAL_REACHED",

        "starfish_count": 2,
        "starfish_confidence": 0.92,

        "shell_count": 2,
        "shell_confidence": 0.89,
    },

    {
        "point_id": "P2_MAIN",
        "robot_x": 2.263,
        "robot_y": -2.907,
        "robot_yaw": -2.945,
        "navigation_state": "GOAL_REACHED",

        "starfish_count": 4,
        "starfish_confidence": 0.94,

        "shell_count": 1,
        "shell_confidence": 0.92,
    },
]


# =========================================================
# DB 저장
# =========================================================

print("===================================")
print(" FAKE PATROL TEST")
print("===================================")

for index, observation in enumerate(
    fake_observations,
    start=1
):

    observation_id = save_observation(

        point_id=
            observation["point_id"],

        robot_x=
            observation["robot_x"],

        robot_y=
            observation["robot_y"],

        robot_yaw=
            observation["robot_yaw"],

        navigation_state=
            observation["navigation_state"],

        starfish_count=
            observation["starfish_count"],

        starfish_confidence=
            observation["starfish_confidence"],

        shell_count=
            observation["shell_count"],

        shell_confidence=
            observation["shell_confidence"],
    )

    print(
        f"[{index}/6] "
        f"{observation['point_id']} "
        f"saved. ID={observation_id}"
    )


print("\n===================================")
print(" FAKE PATROL SAVED")
print("===================================")

print("Patrol 1")
print("P1_MAIN -> P1_SIDE -> P2_MAIN")

print("\nPatrol 2")
print("P1_MAIN -> P1_SIDE -> P2_MAIN")

print(
    "\nInjected anomaly:"
    "\nP1_MAIN starfish 3 (0.91)"
    "\n          ↓"
    "\nP1_MAIN starfish 0 (0.38)"
)

print("\nNext:")
print("py agent_receiver.py")