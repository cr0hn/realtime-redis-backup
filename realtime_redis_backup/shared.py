import asyncio

from functools import lru_cache
from dataclasses import dataclass

import aiobotocore
import botocore.exceptions

from async_timeout import timeout


@dataclass
class RunningConfig:
    redis_server: str

    s3_access_key: str
    s3_secret_key: str
    s3_server: str
    s3_bucket: str = "redis-backup"

    quiet: bool = False
    debug: bool = False
    path: str = ""
    concurrency: int = 1
    redis_pattern: str = "*"
    versioning: bool = False


class AuthException(Exception):
    pass


class S3TimeoutException(Exception):
    pass


async def create_s3_session(config: RunningConfig) -> \
        None or AuthException or S3TimeoutException:
    session = aiobotocore.get_session()
    client = get_s3_client(session, config)

    # Check connectivity
    try:
        async with timeout(4) as cm:
            async with client as c:
                await c.get_bucket_acl(Bucket=config.s3_bucket)

    except botocore.exceptions.ClientError as e:
        raise AuthException(str(e))
    except asyncio.exceptions.TimeoutError as e:
        raise S3TimeoutException("Timeout while try to connect with S3 server")

    return session


def get_s3_client(session, config: RunningConfig):
    client = session.create_client(
        's3',
        # region_name='us-west-2',
        endpoint_url=config.s3_server,
        aws_access_key_id=config.s3_access_key,
        aws_secret_access_key=config.s3_secret_key)
    return client


@lru_cache(200)
def decode_util(text: str or bytes) -> bytes:
    try:
        _text = text.encode("UTF-8")
    except AttributeError:
        _text = text

    return _text


__all__ = ("decode_util", "get_s3_client", "create_s3_session",
           "S3TimeoutException", "AuthException", "RunningConfig")
