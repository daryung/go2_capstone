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