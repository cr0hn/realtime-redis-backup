from typing import Tuple

from realtime_redis_backup.shared import decode_util


def pack_data(key: str, content: str) -> bytes:
    c = bytearray()

    binary_key = decode_util(key)
    binary_value = decode_util(content)

    c.extend(str(len(binary_key)).encode("UTF-8"))
    c.extend(b"#")
    c.extend(str(len(binary_value)).encode("UTF-8"))
    c.extend(b"#")
    c.extend(binary_key)
    c.extend(binary_value)

    return bytes(c)


def unpack_data(content: bytes) -> Tuple[bytes, bytes]:
    key_pos_end = content.find(b"#")

    key_len = int(content[:key_pos_end])
    data_pos_end = content[key_pos_end + 1:].find(b"#") + 1
    data_len = int(content[key_pos_end + 1:data_pos_end + 1])

    key = content[-(data_len + key_len):-data_len]
    value = content[-data_len:]

    return key, value


if __name__ == '__main__':
    c = pack_data("holahola", "mundomundo")
    print(c)
    u = unpack_data(c)
    print(u)
