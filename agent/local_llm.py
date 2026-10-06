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
        "target_point": {
            "type": ["string", "null"]
        },
        "reason": {
            "type": "string"
        }
    },
    "required": ["situation", "action", "target_point", "reason"],
    "additionalProperties": False
}


SYSTEM_PROMPT = """
You are the mission-level decision-making agent of an autonomous marine observation robot.

The robot patrols the same observation points repeatedly.
For the current experiment, the route is:
P1_MAIN -> P1_SIDE -> P2_MAIN
and the route is observed twice.

You receive ALL observations from the completed mission in chronological order.
Compare observations from the SAME point across patrols.
Do not judge only the final observation.

Situation definitions:

NORMAL:
All observation points are consistent with their previous reliable observations.

OBSERVATION_ANOMALY:
At least one point suddenly differs from its previous reliable observation, and low confidence,
occlusion, or temporary detection failure may explain the difference.

POSSIBLE_REAL_CHANGE:
A point differs from its previous reliable observations with sufficiently reliable evidence and
may represent a real environmental change.

NAVIGATION_FAILURE:
The robot failed to reach an observation point.

Action definitions:

CONTINUE:
No recovery action is required.

REOBSERVE:
Return to the anomalous observation point and observe it again.

CHANGE_VIEWPOINT:
Move to another predefined viewpoint for the affected location and observe again.

RETRY_NAVIGATION:
Retry navigation to the failed observation point.

ACCEPT_CHANGE:
Accept a sufficiently supported observation difference as a real environmental change.

ABORT:
Stop the mission if recovery is impossible.

Important rules:

1. Compare each point only with previous observations from the SAME point.
2. Compare the first and second patrol observations for P1_MAIN, P1_SIDE, and P2_MAIN.
3. Do not immediately conclude that an organism disappeared based on one observation.
4. If organism count changes sharply and the newer confidence is low, prefer OBSERVATION_ANOMALY + REOBSERVE.
5. Navigation failure must be handled separately from biological observation changes.
6. Select only ONE mission-level situation and ONE action.
7. If recovery is needed, target_point MUST be the point that should be revisited.
8. For CONTINUE with no affected point, target_point must be null.
9. If several problems exist, choose the problem that most urgently requires robot action.
10. A low-confidence anomalous observation must not become a reliable baseline merely because it repeats.
11. Prefer high-confidence, consistent observations when establishing a baseline.
12. Keep the reason short and explicitly mention the important comparison that caused the decision.
"""


def decide(mission_observations):
    if not mission_observations:
        raise ValueError("No mission observations provided.")

    user_prompt = f"""
MISSION OBSERVATIONS (chronological order):
{json.dumps(mission_observations, ensure_ascii=False, indent=2)}

Evaluate the entire mission.
Compare repeated observations at each same point across patrols.
Return the single most appropriate mission-level situation, action, target_point, and reason.
"""

    payload = {
        "model": MODEL,
        "stream": False,
        "think": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "format": RESPONSE_SCHEMA,
        "options": {"temperature": 0}
    }

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    print("[LLM] Mission-level 판단 중...")

    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.loads(response.read().decode("utf-8"))

    decision = json.loads(result["message"]["content"])
    return decision
