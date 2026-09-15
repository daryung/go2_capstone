wsl
source ~/go2_capstone/.venv/bin/activate
py main.py

navigation.start()
        ↓
Navigation 활성화
        ↓
로봇은 아직 이동 안 함

navigation.goto(x, y, yaw)
        ↓
navigation/set_goal_pose/x/y/yaw
        ↓
Go2가 지도상 목적지까지 경로 계획
        ↓
자율 이동
        ↓
REACHED / NO_PATH / TIMEOUT ...

cd /mnt/c/Users/SAMSUNG/Desktop/go2_capstone


Go2와 PC 준비
Go2를 충전기에서 분리하고 넘어질 물건 없는 넓은 공간에 둔다. PC와 Go2의 네트워크 연결을 확인하고, WSL에서 venv를 켠다.

source ~/go2_capstone/.venv/bin/activate

그리고 기존에 성공했던 UNITREE_ROBOT_IP를 설정한다.

기존 unitree_webrtc_connect 연결부터 확인
전에 성공했던 상태 수신 예제를 먼저 실행해서 WebRTC 자체가 정상인지 확인한다. 여기서 성공해야 이후 문제가 생겨도 “연결 문제”와 “우리 코드 문제”를 구분할 수 있다.

우리 main.py 실행 — 아직 이동시키지 않기
현재처럼 navigation.start()와 navigation.goto()는 주석 상태로 둔다.

python main.py

목표는 [GO2] Connected successfully, USLAM server-log 구독 등 기본 연결이 정상인지 확인하는 것.

Localization만 시작
연결이 정상이라면 다음 테스트에서 localization.start()만 활성화한다. goto()는 계속 주석으로 둔다. 목표는 Python 터미널에

[POSE] x=..., y=..., z=..., yaw=...

가 지속적으로 들어오는지 확인하는 것.

unitree_ui와 Python 좌표 비교 — 중요
네가 보여준 3D LiDAR Mapping UI에서 Localization을 켜고 로봇을 같은 위치에 둔다. UI의 위치/방향과 Python의 (x, y, yaw)가 같은 좌표계를 사용하는지 확인한다.

unitree_ui의 현재 위치
          ↕ 비교
localization.py의 x, y, yaw

이게 맞으면 UI 지도 좌표를 Python Navigation에서 사용할 수 있다는 강한 근거가 된다.

Navigation 모듈만 시작
그다음 navigation.start()를 실행한다. 아직 goto()는 보내지 않는다. navigation/get_status와 server_log를 보면서 Navigation이 정상적으로 시작되는지 확인한다. 이때 목적지가 없으므로 의도하지 않은 이동이 없어야 한다.

첫 실제 자율주행 테스트
주변을 완전히 비운 뒤 UI에서 현재 위치와 아주 가까운 안전한 목표점을 잡는다. 그 좌표를 Python에서

navigation.goto(x, y, yaw)

로 한 번만 전송한다. 처음부터 먼 좌표로 보내지 않는다.

결과 확인
가장 원하는 결과는:

[NAV CMD] navigation/set_goal_pose/...
            ↓
[NAV STATE] TRACKING
            ↓
       Go2 실제 이동
            ↓
[NAV STATE] GOAL_REACHED

이 흐름이다. NO_PATH, TIMEOUT, GOAL_OCCUPIED, FAILURE가 나오더라도 로그를 그대로 저장하면 원인을 분석할 수 있다.

성공하면 이동 테스트 종료
여기까지 되면 내일의 핵심 목표는 달성이다. 여러 번 움직여볼 필요 없어. 이 시점에 Python → Go2 USLAM → 경로계획 → 실제 자율이동 → 결과 수신이 검증된 것이니까.
그 다음 개발 순서 결정
Navigation 성공 이후부터 global_path 수신 → 카메라 스트림 → Vision → 위치 이름/좌표 DB → Mission Manager → LLM → 예외 대응 순으로 가자. 3D 지도는 이미 unitree_ui가 잘 보여주므로 당장 Python으로 다시 렌더링하지 않아도 된다.