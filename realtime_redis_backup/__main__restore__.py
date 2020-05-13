import os
import time
import asyncio
import argparse

from collections import defaultdict

import aioredis

from realtime_redis_backup.shared import *
from realtime_redis_backup.binary_format import unpack_data


async def worker_writer(redis,
                        queue: asyncio.Queue,
                        config: RunningConfig):
    while True:
        # Get 'topic' where was stored new data
        key, value = await queue.get()

        await redis.set(key, value)

        queue.task_done()


async def worker_reader(s3_session,
                        s3_queue: asyncio.Queue,
                        redis_queue: asyncio.Queue,
                        config: RunningConfig):
    #
    # Open s3 session in the worker instead of a separate coroutine to
    # reuse s3 session connection
    #
    async with get_s3_client(s3_session, config) as client:
        while True:
            key = await s3_queue.get()

            response = await client.get_object(
                Bucket=config.s3_bucket,
                Key=key)

            async with response['Body'] as stream:
                content = await stream.read()

            await redis_queue.put(unpack_data(content))

            s3_queue.task_done()


async def worker_indexer(s3_session,
                         queue: asyncio.Queue,
                         config: RunningConfig):
    #
    # Open s3 session in the worker instead of a separate coroutine to
    # reuse s3 session connection
    #
    async with get_s3_client(s3_session, config) as client:

        base_path = config.path or ""
        if base_path:
            if not base_path.endswith("/"):
                base_path = f"{base_path}/"
            if base_path.startswith("/"):
                base_path = base_path[1:]

        paginator = client.get_paginator('list_objects')

        keys = defaultdict(set)
        is_versioned = None

        async for result in paginator.paginate(Bucket=config.s3_bucket,
                                               Prefix=base_path):
            for c in result.get('Contents', []):
                path = c["Key"]

                base_path = os.path.dirname(path)
                file_name = os.path.basename(path)

                #
                # Check if data are versioned or not
                #
                if is_versioned is None:
                    if file_name.count(".") == 2:
                        is_versioned = False
                    else:
                        is_versioned = True

                if is_versioned:
                    await queue.put(c["Key"])
                else:
                    #
                    # We must find the latest version for each key
                    #
                    timestamp, key, ext = file_name.split(".", maxsplit=2)

                    keys[f"{base_path}/{key}.{ext}"].add(timestamp)

        #
        # Once we have all object, we send to load only last versions of them
        #
        for key, timestamps in keys.items():
            base_path = os.path.dirname(key)
            file_name = os.path.basename(key)

            await queue.put(f"{base_path}/{max(timestamps)}.{file_name}")


async def _main_(config: RunningConfig):
    try:
        if not config.quiet:
            print("[*] Connecting to Redis...", end="")

        redis = await aioredis.create_redis_pool(
            config.redis_server,
            maxsize=config.concurrency
        )

        if not config.quiet:
            print("OK!")

    except Exception as e:
        print(f"Can't connect to Redis server: '{e}'!!!")
        exit(1)

    if not config.quiet and config.path:
        print(f"[*] Using S3 base path: '{config.path}'")

    redis_queue = asyncio.Queue()

    # -------------------------------------------------------------------------
    # Redis writers
    # -------------------------------------------------------------------------
    if not config.quiet:
        print("[*] Starting Redis writers...")

    for channel_id in range(config.concurrency):

        if not config.quiet:
            print(f"    > [Writer-{channel_id}] starting...", end="")

        asyncio.create_task(worker_writer(redis, redis_queue, config))

        if not config.quiet:
            print("OK!")

    # -------------------------------------------------------------------------
    # S3 Connection
    # -------------------------------------------------------------------------
    try:
        print("[*] Checking S3 connection...", end="")

        s3_session = await create_s3_session(config)

        print("Ok!")

    except S3TimeoutException as e:
        print("    Can't connect to S3 server. Timeout raised!!!")
        exit(1)
    except AuthException as e:
        print("    Can't connect to S3 server. Auth error raised!!!")
        exit(1)

    queue_s3 = asyncio.Queue()

    # -------------------------------------------------------------------------
    # S3 Readers
    # -------------------------------------------------------------------------
    if not config.quiet:
        print("[*] Starting S3 channels")

    for channel_id in range(config.concurrency):

        if not config.quiet:
            print(f"    > [Channel-{channel_id}] starting...", end="")

        asyncio.create_task(worker_reader(s3_session,
                                          queue_s3,
                                          redis_queue,
                                          config))

        if not config.quiet:
            print("OK!")

    # -------------------------------------------------------------------------
    # S3 Reader Indexer
    # -------------------------------------------------------------------------
    if not config.quiet:
        print("[*] Starting S3 reader...", end="")
    start_time = time.time()
    task_producer = asyncio.create_task(worker_indexer(
        s3_session, queue_s3, config
    ))

    if not config.quiet:
        print("OK!")

    if not config.quiet:
        print("[*] Start restoring S3 backup to redis...")

    await asyncio.gather(task_producer)
    await queue_s3.join()
    await redis_queue.join()

    stop_time = time.time()

    if not config.quiet:
        print(f"[*] All data loaded. Total time: {stop_time-start_time} "
              f"seconds")


def main():
    parser = argparse.ArgumentParser(
        description='Realtime Redis Backup'
    )
    parser.add_argument("REDIS_CONNECTION_STRING",
                        nargs="*",
                        help="redis connection string")
    parser.add_argument("-P", "--path",
                        default="",
                        help="base path to store data")
    parser.add_argument("-c", "--concurrency",
                        type=int,
                        default=2,
                        help="number of concurrent writers to S3")
    parser.add_argument("-q", "--quiet",
                        action="store_true",
                        help="quiet mode")
    parser.add_argument("--debug",
                        action="store_true",
                        help="enable verbose mode")

    parsed = parser.parse_args()

    # Search Redis Server
    if parsed.REDIS_CONNECTION_STRING:
        redis_server = parsed.REDIS_CONNECTION_STRING[0]
    else:
        redis_server = os.environ.get("REDIS_SERVER", None)

    if not redis_server:
        print("[!] Redis server is required. You can specify as cli parameter "
              "or environment var 'REDIS_SERVER'")
        exit(1)
    else:
        parsed.REDIS_CONNECTION_STRING = redis_server

    # Search S3 info
    s3_config = {}
    for s3_info in ("S3_SECRET_KEY", "S3_ACCESS_KEY", "S3_SERVER"):
        try:
            s3_config[s3_info.lower()] = os.environ[s3_info]
        except KeyError:
            print(f"[!] Environment '{s3_info}' is needed")
            exit(1)

    # Other Params
    other_params = {
        x: y for x, y in parsed.__dict__.items()
        if not x.startswith("REDIS")
    }

    running_config = RunningConfig(
        redis_server=redis_server,
        **{**s3_config, **other_params}
    )

    asyncio.run(_main_(running_config))


if __name__ == '__main__':
    main()
