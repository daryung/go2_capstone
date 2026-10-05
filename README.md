wsl
source ~/go2_capstone/.venv/bin/activate
cd "/mnt/c/Users/SAMSUNG/OneDrive/바탕 화면/go2_capstone"
export GO2_AES_KEY="dabb463013ed140250ebae67bfcfe9ca"
python main.py
python vision.py
python rotation_test.py
python main5.py



cd ~/unitree_ui
python3 -m venv .venv
source .venv/bin/activate
./start.sh

DELETE FROM observations;
DELETE FROM sqlite_sequence WHERE name = 'observations';


dabb463013ed140250ebae67bfcfe9ca
192.168.0.101

py -m tests.memory_llm_test

py -m bridge.robot_sender

python -m bridge.agent_receiver.py




