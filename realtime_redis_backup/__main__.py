import os
import time
import asyncio
import hashlib
import argparse

from typing import List, Dict
from functools import partial

import aioredis

from aioredis_watchdog import watchdog

from realtime_redis_backup.shared import *
from realtime_redis_backup.binary_format import pack_data


async def worker(s3_session,
                 queue: asyncio.Queue,
                 config: RunningConfig):

    #
    # Open s3 session in the worker instead of a separate coroutine to
    # reuse s3 session connection
    #
    async with get_s3_client(s3_session, config) as client:

        while True:
            # Get 'topic' where was stored new data
            hash_key, modified_key, modified_value = await queue.get()

            if config.debug:
                print(f"    << Storing key '{hash_key}'...")

            #
            # Store in s3
            #
            base_path = config.path or ""
            if base_path:
                if not base_path.endswith("/"):
                    base_path = f"{base_path}/"
                if base_path.startswith("/"):
                    base_path = base_path[1:]

            if config.versioning:
                timestamp = int(time.time())
                filename = f"{timestamp}.{hash_key}"
            else:
                filename = hash_key

            filename_path = f"{base_path}{filename}.backup"

            # Store Redis key
            resp = await client.put_object(
                Bucket=config.s3_bucket,
                Key=filename_path,
                Body=pack_data(modified_key, modified_value))

            queue.task_done()


async def received_new_key_callback(topics: Dict[str, asyncio.Queue],
                                    config: RunningConfig,
                                    modified_key: str,
                                    modified_value: str):
    encoded_key = decode_util(modified_key)
    encoded_value = decode_util(modified_value)
    hey_hash = hashlib.sha256(encoded_key).hexdigest()

    # Distribute job
    topics[f"worker-{hash(hey_hash) % config.concurrency}"].put_nowait(
        (hey_hash, encoded_key, encoded_value)
    )

    if config.debug:
        print(f"    >> Received New change in key '{modified_key}'")


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

    workers = {
        f"worker-{x}": asyncio.Queue() for x in range(config.concurrency)
    }

    partial_store_in_s3 = partial(received_new_key_callback, workers, config)

    if not config.quiet:
        print(f"[*] Using Redis pattern: '{config.redis_pattern}'")

    if not config.quiet and config.path:
        print(f"[*] Using S3 base path: '{config.path}'")

    if not config.quiet and config.versioning:
        print("[*] RDD Versioning enabled")

    if not config.quiet:
        print("[*] Starting workers")

    for worker_id in range(config.concurrency):

        if not config.quiet:
            print(f"    > [Worker-{worker_id}] starting...", end="")

        try:
            s3_session = await create_s3_session(config)
            asyncio.create_task(worker(
                s3_session,
                workers[f"worker-{worker_id}"],
                config
            ))
        except S3TimeoutException as e:
            print("    Can't connect to S3 server. Timeout raised!!!")
            exit(1)
        except AuthException as e:
            print("    Can't connect to S3 server. Auth error raised!!!")
            exit(1)

        if not config.quiet:
            print("OK!")

    if not config.quiet:
        print("[*] Starting Realtime Redis Backup service... OK!")

    await watchdog(config.redis_pattern, [partial_store_in_s3], redis)


def main():
    parser = argparse.ArgumentParser(
        description='Realtime Redis Backup'
    )
    parser.add_argument("REDIS_CONNECTION_STRING",
                        nargs="*",
                        help="redis connection string")
    parser.add_argument("-r", "--redis-pattern",
                        default="*",
                        help="redis pattern")
    parser.add_argument("-P", "--path",
                        default="",
                        help="base path to store data")
    parser.add_argument("--versioning",
                        action="store_true",
                        help="enable s3 versioning")
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
