"""WebRTC sport commands, based on legion1581/unitree_webrtc_connect."""
import asyncio
import json
import math


class Go2Movement:
    def __init__(self, conn=None, *, dry_run=True):
        self.conn = conn
        self.dry_run = dry_run
        if not dry_run:
            from unitree_webrtc_connect.constants import RTC_TOPIC, SPORT_CMD
            self.topic = RTC_TOPIC['SPORT_MOD']
            self.switcher = RTC_TOPIC['MOTION_SWITCHER']
            self.commands = SPORT_CMD

    async def _request(self, topic, payload, timeout=2.0):
        response = await asyncio.wait_for(
            self.conn.datachannel.pub_sub.publish_request_new(topic, payload),
            timeout=timeout,
        )
        try:
            code = response['data']['header']['status']['code']
        except (KeyError, TypeError) as exc:
            raise RuntimeError(f'Unexpected response: {response!r}') from exc
        if code != 0:
            raise RuntimeError(f'Robot rejected request: code={code}')
        return response

    async def check_mode(self):
        if self.dry_run:
            return 'demo'
        response = await self._request(self.switcher, {'api_id': 1001})
        data = response['data']['data']
        return (json.loads(data) if isinstance(data, str) else data)['name']

    async def set_normal_mode(self):
        """Explicit user action: switching modes may change the robot posture."""
        if self.dry_run:
            print('[DEMO] normal mode requested')
            return
        await self._request(self.switcher, {
            'api_id': 1002, 'parameter': {'name': 'normal'}
        }, timeout=5.0)
        await asyncio.sleep(5)
        if await self.check_mode() != 'normal':
            raise RuntimeError('normal mode was not confirmed')

    async def stop(self):
        if self.dry_run:
            print('[DEMO] StopMove')
            return
        await self._request(self.topic, {'api_id': self.commands['StopMove']})

    async def move_for(self, x=0.0, y=0.0, z=0.0, duration=0.5):
        values = (x, y, z, duration)
        if not all(math.isfinite(v) for v in values):
            raise ValueError('All values must be finite')
        if abs(x) > 0.3 or abs(y) > 0.3 or abs(z) > 0.5:
            raise ValueError('Test limits: |x|,|y| <= 0.3; |z| <= 0.5')
        if not 0 < duration <= 1.0:
            raise ValueError('Duration must be between 0 and 1 second')
        try:
            if self.dry_run:
                print(f'[DEMO] Move x={x}, y={y}, z={z}; {duration}s')
            else:
                await self._request(self.topic, {
                    'api_id': self.commands['Move'],
                    'parameter': {'x': x, 'y': y, 'z': z},
                }, timeout=0.5)
            await asyncio.sleep(duration)
        finally:
            # Attempt stop even when Move times out or this task is cancelled.
            try:
                await self.stop()
            except Exception as exc:
                print(f'[STOP NOT CONFIRMED] {type(exc).__name__}: {exc}')
                raise
