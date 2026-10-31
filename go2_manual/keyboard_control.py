"""Hold-to-drive Go2 controller. Default: offline demo.
Run from go2_manual: python keyboard_control.py [--live --ip ADDRESS]
Requires pygame: python -m pip install pygame
Keep the window focused. W/S forward/back, A/D lateral, Q/E rotate.
Hold LEFT SHIFT with direction keys to move; release either to request stop.
Space stops and disarms. Release all controls before driving again. Esc exits.
Network loss or process failure can prevent StopMove delivery: keep the physical
controller ready. This is not a safety-certified emergency-stop implementation.
"""
import argparse
import asyncio
import json
import math
import os
import time


def velocity(held, speed, turn):
    if 'shift' not in held or 'space' in held:
        return (0.0, 0.0, 0.0)
    x = speed * (('w' in held) - ('s' in held))
    y = speed * (('a' in held) - ('d' in held))
    length = math.hypot(x, y)
    if length > speed:
        x, y = x * speed / length, y * speed / length
    z = turn * (('q' in held) - ('e' in held))
    return (x, y, z)


class Sender:
    def __init__(self, conn=None, commands=None):
        self.conn = conn
        self.commands = commands
        self.last_demo = None
        self.seq = 0

    def send(self, vector):
        moving = any(vector)
        if self.conn is None:
            if vector != self.last_demo:
                print('[DEMO]', 'Move' if moving else 'StopMove', vector, flush=True)
                self.last_demo = vector
            return
        from unitree_webrtc_connect.constants import RTC_TOPIC, DATA_CHANNEL_TYPE
        pub = self.conn.datachannel.pub_sub
        if pub.channel.readyState != 'open':
            raise ConnectionError('DataChannel closed; stop delivery is not confirmed')
        self.seq += 1
        payload = {
            'header': {'identity': {
                'id': time.time_ns() % 2147483647,
                'api_id': self.commands['Move' if moving else 'StopMove'],
            }},
            'parameter': json.dumps(dict(zip(('x', 'y', 'z'), vector))) if moving else '',
        }
        # Request envelope matches publish_request_new; do not wait for an RPC
        # response on every velocity update, so key release is not queued behind it.
        pub.publish_without_callback(
            RTC_TOPIC['SPORT_MOD'], payload, DATA_CHANNEL_TYPE['REQUEST']
        )


async def connect(args):
    from robot.connection import Go2Connection
    from unitree_webrtc_connect import constants
    wrapper = Go2Connection(ip=args.ip)
    try:
        conn = await asyncio.wait_for(wrapper.connect(), 30)
        response = await asyncio.wait_for(
            conn.datachannel.pub_sub.publish_request_new(
                constants.RTC_TOPIC['MOTION_SWITCHER'], {'api_id': 1001}), 5)
        if response['data']['header']['status']['code'] != 0:
            raise RuntimeError('Motion mode query rejected')
        data = response['data']['data']
        mode = (json.loads(data) if isinstance(data, str) else data)['name']
        if mode == 'mcf':
            commands = getattr(constants, 'SPORT_CMD_MCF', None)
            if commands is None:
                raise RuntimeError('Installed driver has no SPORT_CMD_MCF')
        elif mode == 'normal':
            commands = constants.SPORT_CMD
        else:
            raise RuntimeError(f'Unsupported mode: {mode}; no automatic mode switch')
        print('Connected; mode:', mode)
        return conn, commands
    except BaseException:
        if wrapper.conn is not None:
            try:
                await asyncio.wait_for(wrapper.conn.disconnect(), 3)
            except Exception:
                pass
        raise


async def main(args):
    import pygame
    pygame.init()
    conn = None
    sender = Sender()
    held = set()
    armed = False
    try:
        screen = pygame.display.set_mode((700, 390))
        pygame.display.set_caption('Go2 hold-to-drive | DEMO' if not args.live else 'Go2 hold-to-drive | LIVE')
        font = pygame.font.Font(None, 28)
        # Render first, then connect. No movement is sent during connection.
        screen.fill((18, 25, 29))
        screen.blit(font.render('Connecting...' if args.live else 'Offline demo', True, (190, 240, 150)), (28, 35))
        pygame.display.flip()
        if args.live:
            conn, commands = await connect(args)
            sender = Sender(conn, commands)
        mapping = {pygame.K_w:'w',pygame.K_s:'s',pygame.K_a:'a',pygame.K_d:'d',
                   pygame.K_q:'q',pygame.K_e:'e',pygame.K_LSHIFT:'shift',pygame.K_SPACE:'space'}
        controls = {'w','s','a','d','q','e','shift','space'}
        last_send = 0.0
        previous = (0.0, 0.0, 0.0)
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False
                elif event.type == pygame.KEYDOWN and event.key in mapping:
                    held.add(mapping[event.key])
                elif event.type == pygame.KEYUP and event.key in mapping:
                    held.discard(mapping[event.key])
                elif event.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWMINIMIZED):
                    held.clear()
                    armed = False
            focused = pygame.key.get_focused()
            if not focused:
                held.clear()
                armed = False
            if 'space' in held:
                armed = False
            # Must fully release controls after focus loss / Space before rearming.
            if focused and not (held & controls):
                armed = True
            vector = velocity(held, args.speed, args.turn) if armed and focused and running else (0.0, 0.0, 0.0)
            now = time.monotonic()
            if vector != previous or now-last_send >= 0.1:
                sender.send(vector)
                previous, last_send = vector, now
            screen.fill((18, 25, 29))
            lines = [
                'LIVE ROBOT CONTROL' if args.live else 'DEMO - NO ROBOT COMMANDS',
                'Hold LEFT SHIFT + direction to move',
                'W / S : forward / backward',
                'A / D : lateral      Q / E : rotate',
                'Release key / Shift : request stop',
                'SPACE : stop + disarm      ESC : exit',
                f'Window focused: {focused}     Armed: {armed}',
                'Command: x=%.2f  y=%.2f  yaw=%.2f' % vector,
                'LIVE: delivery is not a physical stop confirmation.',
                'Keep the physical controller ready.',
            ]
            for i, line in enumerate(lines):
                color = (183, 242, 134) if i in (0, 7) else (219, 226, 231)
                screen.blit(font.render(line, True, color), (28, 24+i*34))
            pygame.display.flip()
            await asyncio.sleep(0.015)
    finally:
        for _ in range(3):
            try:
                sender.send((0.0, 0.0, 0.0))
                await asyncio.sleep(0.03)
            except Exception as exc:
                print('[STOP NOT CONFIRMED]', exc)
                break
        if conn is not None:
            try:
                await asyncio.wait_for(conn.disconnect(), 3)
            except Exception as exc:
                print('[DISCONNECT]', exc)
        pygame.quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--ip', default=os.getenv('UNITREE_ROBOT_IP', '192.168.0.101'))
    parser.add_argument('--speed', type=float, default=0.2)
    parser.add_argument('--turn', type=float, default=0.3)
    args = parser.parse_args()
    if not (0 < args.speed <= 0.5 and 0 < args.turn <= 0.5):
        parser.error('speed: (0,0.5], turn: (0,0.5]')
    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        print('Interrupted; verify robot stopped.')
    except Exception as exc:
        print(f'[ERROR] {type(exc).__name__}: {exc}')
