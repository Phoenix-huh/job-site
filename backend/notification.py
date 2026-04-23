import asyncio
from typing import AsyncGenerator
import json

class NotificationManager:
    def __init__(self):
        self.queues = []

    async def get_generator(self) -> AsyncGenerator[str, None]:
        queue = asyncio.Queue()
        self.queues.append(queue)
        try:
            while True:
                data = await queue.get()
                yield dict(data=json.dumps(data))
        except asyncio.CancelledError:
            pass
        finally:
            self.queues.remove(queue)

    def publish(self, message: dict):
        for queue in self.queues:
            queue.put_nowait(message)

manager = NotificationManager()
