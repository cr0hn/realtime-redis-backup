import uuid
import asyncio

import aioredis


async def main():
    redis = await aioredis.create_redis_pool('redis://localhost:6500')

    for x in range(10000):
        v = await redis.set(f'users:profile:user-{x}', uuid.uuid4().hex)
        print("writing: ", x)
        # break
        # await asyncio.sleep(1)
        await asyncio.sleep(0.001)


if __name__ == '__main__':
    asyncio.run(main())
