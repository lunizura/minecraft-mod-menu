"""
nbt_core.py - Pure-Python Lossless Big-Endian NBT Parser & Serializer
Zero external dependencies. Fully compliant with Minecraft Java Edition NBT specifications.
Supports all 13 official tag types (TAG_End 0 through TAG_Long_Array 12).
Handles Gzip-compressed, Zlib-compressed, and uncompressed NBT streams.
"""

from __future__ import annotations
import io
import gzip
import zlib
import struct
from typing import Any, Dict, List, Optional, Union, Iterator

# Tag Type Constants
TAG_END = 0
TAG_BYTE = 1
TAG_SHORT = 2
TAG_INT = 3
TAG_LONG = 4
TAG_FLOAT = 5
TAG_DOUBLE = 6
TAG_BYTE_ARRAY = 7
TAG_STRING = 8
TAG_LIST = 9
TAG_COMPOUND = 10
TAG_INT_ARRAY = 11
TAG_LONG_ARRAY = 12

TAG_NAMES = {
    TAG_END: "TAG_End",
    TAG_BYTE: "TAG_Byte",
    TAG_SHORT: "TAG_Short",
    TAG_INT: "TAG_Int",
    TAG_LONG: "TAG_Long",
    TAG_FLOAT: "TAG_Float",
    TAG_DOUBLE: "TAG_Double",
    TAG_BYTE_ARRAY: "TAG_Byte_Array",
    TAG_STRING: "TAG_String",
    TAG_LIST: "TAG_List",
    TAG_COMPOUND: "TAG_Compound",
    TAG_INT_ARRAY: "TAG_Int_Array",
    TAG_LONG_ARRAY: "TAG_Long_Array",
}


class NBTTag:
    """Base class for all NBT tags."""
    tag_type: int = TAG_END

    @property
    def name(self) -> str:
        return TAG_NAMES.get(self.tag_type, f"TAG_Unknown({self.tag_type})")

    def to_py(self) -> Any:
        """Convert to standard Python primitives."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.name}>"


class TAG_End(NBTTag):
    tag_type = TAG_END

    def to_py(self) -> None:
        return None

    def __repr__(self) -> str:
        return "<TAG_End>"


class TAG_Byte(NBTTag):
    tag_type = TAG_BYTE

    def __init__(self, value: int = 0):
        # normalize to signed 8-bit int (-128 to 127)
        self.value = int(value)
        if self.value > 127:
            self.value = ((self.value + 128) % 256) - 128
        elif self.value < -128:
            self.value = ((self.value + 128) % 256) - 128

    def to_py(self) -> int:
        return self.value

    def __int__(self) -> int:
        return self.value

    def __float__(self) -> float:
        return float(self.value)

    def __bool__(self) -> bool:
        return bool(self.value)

    def __repr__(self) -> str:
        return f"TAG_Byte({self.value}b)"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, TAG_Byte):
            return self.value == other.value
        if isinstance(other, int):
            return self.value == other
        return False


class TAG_Short(NBTTag):
    tag_type = TAG_SHORT

    def __init__(self, value: int = 0):
        self.value = int(value)
        if self.value > 32767 or self.value < -32768:
            self.value = struct.unpack(">h", struct.pack(">h", self.value & 0xFFFF))[0]

    def to_py(self) -> int:
        return self.value

    def __int__(self) -> int:
        return self.value

    def __float__(self) -> float:
        return float(self.value)

    def __bool__(self) -> bool:
        return bool(self.value)

    def __repr__(self) -> str:
        return f"TAG_Short({self.value}s)"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, TAG_Short):
            return self.value == other.value
        if isinstance(other, int):
            return self.value == other
        return False


class TAG_Int(NBTTag):
    tag_type = TAG_INT
