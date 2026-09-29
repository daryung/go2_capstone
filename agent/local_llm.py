import json
import urllib.request


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3.5:4b"


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "situation": {
            "type": "string",
            "enum": [
                "NORMAL",
                "OBSERVATION_ANOMALY",
                "POSSIBLE_REAL_CHANGE",
                "NAVIGATION_FAILURE"
            ]
        },
        "action": {
            "type": "string",
            "enum": [
                "CONTINUE",
                "REOBSERVE",
                "CHANGE_VIEWPOINT",
                "RETRY_NAVIGATION",
                "ACCEPT_CHANGE",
                "ABORT"
            ]
        },
        "reason": {
            "type": "string"
        }
    },
    "required": ["situation", "action", "reason"],
    "additionalProperties": False
}


SYSTEM_PROMPT = """
You are the decision-making agent of an autonomous marine observation robot.

The robot repeatedly observes starfish and shellfish at observation points A, B, and C.

Your task is to compare the current observation with previous observations
from the SAME observation point and determine the current situation.

Situation definitions:

NORMAL:
The current observation is consistent with previous observations.

OBSERVATION_ANOMALY:
The current result differs from previous observations, but low confidence,
occlusion, or temporary detection failure may explain the difference.

POSSIBLE_REAL_CHANGE:
The observation differs from previous observations and may represent
a real environmental change.

NAVIGATION_FAILURE:
The robot failed to reach the observation point.

Action definitions:

CONTINUE:
Continue to the next observation point.

REOBSERVE:
Observe again from the current position.

CHANGE_VIEWPOINT:
Move to another predefined viewpoint and observe again.

RETRY_NAVIGATION:
Retry navigation to the observation point.

ACCEPT_CHANGE:
Accept the observed difference as a real environmental change.

ABORT:
Stop the mission if recovery is impossible.

Important rules:

1. Do not immediately conclude that an organism disappeared based on one observation.
2. If detection confidence is low and the count suddenly changes, prefer re-observation.
3. Use previous observations when making the decision.
4. Navigation failure should be handled separately from biological observation changes.
5. Select only one situation and one action.
6. Keep the reason short.
7. A REOBSERVATION is a verification observation triggered by a previous anomaly. Do not interpret a recovery from an anomalous low-confidence observation to the historical baseline as a new environmental change.
8. If a low-confidence anomalous observation is followed by a high-confidence reobservation that returns to the historical baseline, classify the result as NORMAL and select CONTINUE.
9. Observations previously classified as OBSERVATION_ANOMALY must not be treated as reliable baseline observations, even if the same anomalous result occurs repeatedly.

10. When determining the historical baseline, prioritize high-confidence observations classified as NORMAL over low-confidence anomalous observations.

11. If the current observation has low confidence and differs from the most recent reliable NORMAL observation, classify it as OBSERVATION_ANOMALY and select REOBSERVE, even if similar low-confidence anomalies occurred previously.
"""


def decide(current_observation, history):

    user_prompt = f"""
CURRENT OBSERVATION:
{json.dumps(current_observation, ensure_ascii=False, indent=2)}

PREVIOUS OBSERVATIONS:
{json.dumps(history, ensure_ascii=False, indent=2)}

Determine the situation and select the most appropriate action.
"""

    payload = {
        "model": MODEL,
        "stream": False,

        # qwen3.5가 지원하는 경우 thinking을 끄기 위한 설정
        "think": False,

        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],

        # Ollama structured output
        "format": RESPONSE_SCHEMA,

        "options": {
            "temperature": 0
        }
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    print("[LLM] 판단 중...")

    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.loads(response.read().decode("utf-8"))

    decision = json.loads(result["message"]["content"])

    return decision