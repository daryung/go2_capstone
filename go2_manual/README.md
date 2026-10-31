# Go2 WebRTC 수동 조종 테스트

기존 connection(3).py를 robot/connection.py에 그대로 포함했습니다.
새 기능은 robot/movement.py와 manual_control.py입니다. 기존 파일을 덮어쓰지 않고 별도 폴더에서 실행할 수 있습니다.

## 로봇 없이 테스트

```bash
cd go2_manual
python3 manual_control.py
```

w 입력 후 Enter: 전진 명령을 출력하고 0.5초 후 정지를 출력합니다.
exit + Enter: 종료. 키를 누르는 동안 조종하는 방식이 아니라 짧은 이동 테스트입니다.

## 실제 연결

기존 WebRTC 연결에 성공했던 Python 환경에서 실행하세요. PC·Go2는 같은 Wi-Fi에 있어야 하며 IP는 현재 로봇 주소를 사용합니다.
GO2_AES_KEY는 기존 연결 클래스가 요구하는 환경변수입니다. 키는 코드나 공유 파일에 넣지 마세요.
설정된 환경에서:

```bash
python3 manual_control.py --live --ip 192.168.0.101
```

기존 connection.py가 요구하는 라이브러리를 그대로 사용하며 강제 업그레이드는 하지 않습니다.
normal 모드가 확인되지 않으면 이동을 막습니다. normal 명령은 명시적으로 모드 전환을 요청하며 로봇 자세가 바뀔 수 있습니다.
자동 일어서기·특수 동작·저수준 제어는 넣지 않았습니다.

## 명령

w/s 전진·후진, a/d 좌우 이동, q/e 회전, stop 이동 정지, mode 모드 조회, normal 일반 모드 전환, exit 종료.
방향 명령은 기본 0.5초 후 StopMove를 요청합니다. 속도 명령은 정확한 이동 거리를 보장하지 않습니다.
응답 확인 후 0.5초를 대기하므로 실제 이동 시간은 통신 지연·펌웨어에 따라 달라집니다.
연결이 끊기면 정지 명령도 전달되지 않을 수 있습니다. 물리 리모컨 정지를 준비하고 넓은 모의 환경에서 시험하세요.
장애물 회피·안전 정지를 보장하는 제어기가 아닙니다.

## 기존 영상 코드와 결합

같은 프로세스에서 한 번 연결한 conn을 Go2Movement(conn, dry_run=False)에 전달합니다.
예: await movement.move_for(x=0.2, duration=0.5)
영상과 조종이 각각 별도 WebRTC 연결을 만들지 않도록 합니다.
영상 루프의 YOLO 동기 추론은 별도 작업으로 분리한 후 UI 제어와 통합해야 합니다.
이 번들은 영상/UI 통합이 아니라 이동 전송을 분리해 확인하는 단계입니다.

## 출처와 검증 범위

참고 저장소: https://github.com/legion1581/unitree_webrtc_connect
commit: e0abc5780761539eff89a382a79319e5cf6ad1f4
examples/go2/data_channel/sportmode/sportmode.py
unitree_webrtc_connect/constants.py, msgs/pub_sub.py, webrtc_driver.py

Move: RTC_TOPIC["SPORT_MOD"], SPORT_CMD["Move"], parameter={x,y,z}
StopMove: 같은 토픽, SPORT_CMD["StopMove"]
모드 조회/전환: RTC_TOPIC["MOTION_SWITCHER"], api_id 1001/1002
사용자 연결 클래스의 GO2_AES_KEY를 유지했습니다. 저장소 예제의 환경변수 이름과 다릅니다.
이 저장소는 Unitree 공식 DDS SDK와 별개의 커뮤니티 드라이버입니다.
문법·오프라인 입출력·가짜 연결에서 명령 형식/오류 시 정지 시도를 검증했습니다.
실제 Go2·펌웨어·설치 패키지 호환성과 물리 동작은 검증하지 못했습니다.
