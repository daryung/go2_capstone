"""Terminal pulse control: each direction moves briefly, then requests stop."""
import argparse
import asyncio
import os

from robot.movement import Go2Movement

DIRECTIONS = {
    'w': (0.2, 0, 0),
    's': (-0.2, 0, 0),
    'a': (0, 0.2, 0),
    'd': (0, -0.2, 0),
    'q': (0, 0, 0.3),
    'e': (0, 0, -0.3),
}


def configure_motion_mode(movement, mode):
    """Choose the matching API table without changing the robot mode."""
    if movement.dry_run:
        return mode == 'demo'
    from unitree_webrtc_connect import constants
    if mode == 'mcf':
        commands = getattr(constants, 'SPORT_CMD_MCF', None)
        if commands is None:
            print('MCF command table is missing in the installed package; movement blocked.')
            return False
    elif mode == 'normal':
        commands = constants.SPORT_CMD
    else:
        return False
    movement.commands = commands
    return True


async def main(args):
    conn = None
    movement = Go2Movement()
    ready = not args.live
    try:
        if args.live:
            from robot.connection import Go2Connection
            print('LIVE: commands will be sent to the robot. Keep the physical controller ready.')
            conn = await asyncio.wait_for(Go2Connection(ip=args.ip).connect(), 30)
            movement = Go2Movement(conn, dry_run=False)
            mode = await movement.check_mode()
            ready = configure_motion_mode(movement, mode)
            print(f'Connected; motion mode={mode}')
            if not ready:
                print('Movement disabled: unsupported mode or missing command table. No automatic mode change.')
        else:
            print('DEMO: no SDK, network, or robot commands used.')

        print('w/s: forward/back | a/d: lateral | q/e: rotate')
        print('Each command + Enter: 0.5 second pulse, then StopMove.')
        print('stop: stop | mode: query | normal: change mode | exit: quit')
        print('Lateral/rotation signs must be verified on your robot before UI integration.')
        while True:
            command = (await asyncio.to_thread(input, '> ')).strip().lower()
            if not command:
                continue
            if command == 'exit':
                break
            if command == 'stop':
                await movement.stop()
            elif command == 'mode':
                mode = await movement.check_mode()
                ready = configure_motion_mode(movement, mode)
                print('Motion mode:', mode)
            elif command == 'normal':
                await movement.set_normal_mode()
                mode = await movement.check_mode()
                ready = configure_motion_mode(movement, mode)
                print(f'Motion mode after request: {mode}; movement enabled={ready}')
            elif command in DIRECTIONS:
                if not ready:
                    print('Supported mode and command table are not confirmed; movement blocked.')
                    continue
                await movement.move_for(*DIRECTIONS[command])
                print('Demo complete.' if not args.live else 'Command responses received; verify motion visually.')
            else:
                print('Unknown command; no movement sent.')
    except EOFError:
        pass
    except Exception as exc:
        print(f'[ERROR] {type(exc).__name__}: {exc}')
    finally:
        if conn is not None:
            try:
                await movement.stop()
            except Exception as exc:
                print(f'[STOP NOT CONFIRMED] {exc}; use the physical controller.')
            await asyncio.wait_for(conn.disconnect(), 5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Send commands to real Go2')
    parser.add_argument('--ip', default=os.environ.get('UNITREE_ROBOT_IP', '192.168.0.101'))
    args = parser.parse_args()
    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        print('\nInterrupted. If connected, verify the robot has stopped.')
