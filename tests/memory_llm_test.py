from memory.observation_memory import (
    save_observation,
    get_history,
    save_decision
)

from agent.local_llm import decide


print("===================================")
print(" Physical AI Agent Closed-loop Test")
print("===================================")


current_observation = {
    "point_id": "B",

    "robot_x": 0.52,
    "robot_y": 1.21,
    "robot_yaw": 1.57,

    "navigation_state": "REACHED",

    "starfish_count": 0,
    "starfish_confidence": 0.38,

    "shell_count": 1,
    "shell_confidence": 0.42
}


print("\n[CURRENT OBSERVATION]")
print(current_observation)


observation_id = save_observation(
    point_id=current_observation["point_id"],

    robot_x=current_observation["robot_x"],
    robot_y=current_observation["robot_y"],
    robot_yaw=current_observation["robot_yaw"],

    navigation_state=current_observation["navigation_state"],

    starfish_count=current_observation["starfish_count"],
    starfish_confidence=current_observation["starfish_confidence"],

    shell_count=current_observation["shell_count"],
    shell_confidence=current_observation["shell_confidence"]
)

print("\n[MEMORY] 현재 Observation 저장 완료")
print(f"ID = {observation_id}")


history = get_history(
    point_id=current_observation["point_id"],
    limit=5,
    exclude_id=observation_id
)


print("\n[OBSERVATION HISTORY]")

for obs in history:
    print(
        f"ID={obs['id']} | "
        f"Starfish={obs['starfish_count']} "
        f"(conf={obs['starfish_confidence']}) | "
        f"Shell={obs['shell_count']} "
        f"(conf={obs['shell_confidence']})"
    )


decision = decide(
    current_observation=current_observation,
    history=history
)


print("\n[FIRST AGENT DECISION]")
print(f"Situation : {decision['situation']}")
print(f"Action    : {decision['action']}")
print(f"Reason    : {decision['reason']}")


save_decision(
    observation_id=observation_id,
    situation=decision["situation"],
    action=decision["action"],
    reason=decision["reason"]
)

print("\n[MEMORY] 첫 번째 Agent 판단 결과 저장 완료")



if decision["action"] == "REOBSERVE":

    print("\n===================================")
    print(" ACTION : REOBSERVE")
    print("===================================")

    print("\n[ROBOT] 현재 관측지점에서 재관측을 수행합니다.")


    reobservation = {
        "point_id": current_observation["point_id"],

        "robot_x": current_observation["robot_x"],
        "robot_y": current_observation["robot_y"],
        "robot_yaw": current_observation["robot_yaw"],

        "navigation_state": "REACHED",

        "starfish_count": 3,
        "starfish_confidence": 0.92,

        "shell_count": 4,
        "shell_confidence": 0.90
    }


    print("\n[REOBSERVATION]")
    print(reobservation)


    reobservation_id = save_observation(
        point_id=reobservation["point_id"],

        robot_x=reobservation["robot_x"],
        robot_y=reobservation["robot_y"],
        robot_yaw=reobservation["robot_yaw"],

        navigation_state=reobservation["navigation_state"],

        starfish_count=reobservation["starfish_count"],
        starfish_confidence=reobservation["starfish_confidence"],

        shell_count=reobservation["shell_count"],
        shell_confidence=reobservation["shell_confidence"]
    )


    print("\n[MEMORY] 재관측 Observation 저장 완료")
    print(f"ID = {reobservation_id}")


    new_history = get_history(
        point_id=reobservation["point_id"],
        limit=5,
        exclude_id=reobservation_id
    )


    print("\n[UPDATED OBSERVATION HISTORY]")

    for obs in new_history:

        print(
            f"ID={obs['id']} | "
            f"Starfish={obs['starfish_count']} "
            f"(conf={obs['starfish_confidence']}) | "
            f"Shell={obs['shell_count']} "
            f"(conf={obs['shell_confidence']}) | "
            f"Situation={obs['situation']} | "
            f"Action={obs['action']}"
        )



    print("\n[AGENT] 재관측 결과를 기반으로 다시 판단합니다.")

    second_decision = decide(
        current_observation=reobservation,
        history=new_history
    )


    print("\n[SECOND AGENT DECISION]")
    print(f"Situation : {second_decision['situation']}")
    print(f"Action    : {second_decision['action']}")
    print(f"Reason    : {second_decision['reason']}")



    save_decision(
        observation_id=reobservation_id,
        situation=second_decision["situation"],
        action=second_decision["action"],
        reason=second_decision["reason"]
    )


    print("\n[MEMORY] 두 번째 Agent 판단 결과 저장 완료")


    if second_decision["action"] == "CONTINUE":

        print("\n===================================")
        print(" CLOSED-LOOP TEST SUCCESS")
        print("===================================")

        print(
            "[ROBOT] 관측 이상이 재관측을 통해 해소되었습니다."
        )

        print(
            "[ROBOT] 다음 관측지점으로 이동합니다."
        )

    else:

        print("\n===================================")
        print(" ADDITIONAL ACTION REQUIRED")
        print("===================================")

        print(
            f"[ROBOT] 추가 행동 필요: "
            f"{second_decision['action']}"
        )


elif decision["action"] == "CONTINUE":

    print("\n[ACTION] CONTINUE")
    print("[ROBOT] 다음 관측지점으로 이동합니다.")


elif decision["action"] == "CHANGE_VIEWPOINT":

    print("\n[ACTION] CHANGE_VIEWPOINT")
    print("[ROBOT] 다른 관측 위치로 이동합니다.")


elif decision["action"] == "RETRY_NAVIGATION":

    print("\n[ACTION] RETRY_NAVIGATION")
    print("[ROBOT] 목표지점 이동을 다시 시도합니다.")


elif decision["action"] == "ACCEPT_CHANGE":

    print("\n[ACTION] ACCEPT_CHANGE")
    print("[ROBOT] 실제 환경 변화로 기록합니다.")


elif decision["action"] == "ABORT":

    print("\n[ACTION] ABORT")
    print("[ROBOT] 임무를 중단합니다.")


else:

    print("\n[WARNING]")
    print(f"처리되지 않은 Action: {decision['action']}")