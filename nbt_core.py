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

    def __init__(self, value: int = 0):
        self.value = int(value)
        if self.value > 2147483647 or self.value < -2147483648:
            self.value = struct.unpack(">i", struct.pack(">i", self.value & 0xFFFFFFFF))[0]

    def to_py(self) -> int:
        return self.value

    def __int__(self) -> int:
        return self.value

    def __float__(self) -> float:
        return float(self.value)

    def __bool__(self) -> bool:
        return bool(self.value)

    def __repr__(self) -> str:
        return f"TAG_Int({self.value})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, TAG_Int):
            return self.value == other.value
        if isinstance(other, int):
            return self.value == other
        return False


class TAG_Long(NBTTag):
    tag_type = TAG_LONG

    def __init__(self, value: int = 0):
        self.value = int(value)
        if self.value > 9223372036854775807 or self.value < -9223372036854775808:
            self.value = struct.unpack(">q", struct.pack(">q", self.value & 0xFFFFFFFFFFFFFFFF))[0]

    def to_py(self) -> int:
        return self.value

    def __int__(self) -> int:
        return self.value

    def __float__(self) -> float:
        return float(self.value)

    def __bool__(self) -> bool:
        return bool(self.value)

    def __repr__(self) -> str:
        return f"TAG_Long({self.value}L)"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, TAG_Long):
            return self.value == other.value
        if isinstance(other, int):
            return self.value == other
        return False


class TAG_Float(NBTTag):
    tag_type = TAG_FLOAT

    def __init__(self, value: float = 0.0):
        self.value = float(value)

    def to_py(self) -> float:
        return self.value

    def __float__(self) -> float:
        return self.value

    def __int__(self) -> int:
        return int(self.value)

    def __repr__(self) -> str:
        return f"TAG_Float({self.value}f)"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, TAG_Float):
            return abs(self.value - other.value) < 1e-6
        if isinstance(other, (int, float)):
            return abs(self.value - float(other)) < 1e-6
        return False


class TAG_Double(NBTTag):
    tag_type = TAG_DOUBLE

    def __init__(self, value: float = 0.0):
        self.value = float(value)

    def to_py(self) -> float:
        return self.value

    def __float__(self) -> float:
        return self.value

    def __int__(self) -> int:
        return int(self.value)

    def __repr__(self) -> str:
        return f"TAG_Double({self.value}d)"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, TAG_Double):
            return self.value == other.value
        if isinstance(other, (int, float)):
            return self.value == float(other)
        return False


class TAG_Byte_Array(NBTTag):
    tag_type = TAG_BYTE_ARRAY

    def __init__(self, value: Union[bytes, bytearray, List[int]] = b""):
        if isinstance(value, (bytes, bytearray)):
            self.value = bytearray(value)
        else:
            self.value = bytearray(v & 0xFF for v in value)

    def to_py(self) -> bytearray:
        return self.value

    def __len__(self) -> int:
        return len(self.value)

    def __repr__(self) -> str:
        return f"TAG_Byte_Array({len(self.value)} bytes)"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, TAG_Byte_Array):
            return self.value == other.value
        if isinstance(other, (bytes, bytearray)):
            return self.value == other
        return False


class TAG_String(NBTTag):
    tag_type = TAG_STRING

    def __init__(self, value: str = ""):
        self.value = str(value)

    def to_py(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"TAG_String({repr(self.value)})"

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, TAG_String):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return False


class TAG_List(NBTTag):
    tag_type = TAG_LIST

    def __init__(self, subtag_type: int = TAG_END, value: Optional[List[NBTTag]] = None):
        self.subtag_type = subtag_type
        self.value: List[NBTTag] = list(value) if value is not None else []
        if self.value and self.subtag_type == TAG_END:
            self.subtag_type = self.value[0].tag_type

    def append(self, tag: NBTTag) -> None:
        if not self.value and self.subtag_type == TAG_END:
            self.subtag_type = tag.tag_type
        elif self.subtag_type != tag.tag_type:
            raise TypeError(f"Cannot append {tag.name} to TAG_List of {TAG_NAMES.get(self.subtag_type)}")
        self.value.append(tag)

    def __len__(self) -> int:
        return len(self.value)

    def __getitem__(self, index: int) -> NBTTag:
        return self.value[index]

    def __setitem__(self, index: int, tag: NBTTag) -> None:
        if self.subtag_type == TAG_END:
            self.subtag_type = tag.tag_type
        elif self.subtag_type != tag.tag_type:
            raise TypeError(f"Cannot set {tag.name} in TAG_List of {TAG_NAMES.get(self.subtag_type)}")
        self.value[index] = tag

    def __iter__(self) -> Iterator[NBTTag]:
        return iter(self.value)

    def to_py(self) -> List[Any]:
        return [tag.to_py() for tag in self.value]

    def __repr__(self) -> str:
        sub_name = TAG_NAMES.get(self.subtag_type, "Empty")
        return f"TAG_List[{sub_name}]({len(self.value)} entries)"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, TAG_List):
            if len(self.value) == 0 and len(other.value) == 0:
                return True
            return self.subtag_type == other.subtag_type and self.value == other.value
        if isinstance(other, list):
            return self.to_py() == other
        return False


class TAG_Compound(NBTTag):
    tag_type = TAG_COMPOUND

    def __init__(self, value: Optional[Dict[str, NBTTag]] = None):
        self.value: Dict[str, NBTTag] = dict(value) if value is not None else {}

    def __len__(self) -> int:
        return len(self.value)

    def __getitem__(self, key: str) -> NBTTag:
        return self.value[key]

    def __setitem__(self, key: str, tag: NBTTag) -> None:
        if not isinstance(tag, NBTTag):
            raise TypeError(f"Value for compound key '{key}' must be an NBTTag instance, got {type(tag)}")
        self.value[key] = tag

    def __delitem__(self, key: str) -> None:
        del self.value[key]

    def __contains__(self, key: str) -> bool:
        return key in self.value

    def keys(self):
        return self.value.keys()

    def values(self):
        return self.value.values()

    def items(self):
        return self.value.items()

    def get(self, key: str, default: Any = None) -> Any:
        return self.value.get(key, default)

    def get_val(self, path: str, default: Any = None) -> Any:
        """
        Navigate nested keys with forward-slash syntax, e.g. 'abilities/mayfly'
        Returns standard python unwrapped primitive value.
        """
        parts = path.split("/")
        curr = self
        for part in parts[:-1]:
            if not isinstance(curr, TAG_Compound) or part not in curr:
                return default
            curr = curr[part]
        if not isinstance(curr, TAG_Compound) or parts[-1] not in curr:
            return default
        tag = curr[parts[-1]]
        return tag.to_py() if isinstance(tag, NBTTag) else tag

    def set_path(self, path: str, tag: NBTTag) -> None:
        """
        Set a tag along a slash-separated path, creating missing TAG_Compounds along the way.
        Example: root.set_path("Data/allowCommands", TAG_Byte(1))
        """
        parts = path.split("/")
        curr = self
        for part in parts[:-1]:
            if part not in curr or not isinstance(curr[part], TAG_Compound):
                new_compound = TAG_Compound()
                curr[part] = new_compound
                curr = new_compound
            else:
                curr = curr[part]
        curr[parts[-1]] = tag

    def to_py(self) -> Dict[str, Any]:
        return {k: v.to_py() for k, v in self.value.items()}

    def __repr__(self) -> str:
        return f"TAG_Compound({len(self.value)} entries: {list(self.value.keys())[:5]}...)"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, TAG_Compound):
            return self.value == other.value
        if isinstance(other, dict):
            return self.to_py() == other
        return False


class TAG_Int_Array(NBTTag):
    tag_type = TAG_INT_ARRAY

    def __init__(self, value: Optional[List[int]] = None):
        if value is None:
            self.value: List[int] = []
        else:
            self.value = [
                struct.unpack(">i", struct.pack(">i", int(v) & 0xFFFFFFFF))[0]
                if (int(v) > 2147483647 or int(v) < -2147483648)
                else int(v)
                for v in value
            ]

    def to_py(self) -> List[int]:
        return self.value

    def __len__(self) -> int:
        return len(self.value)

    def __repr__(self) -> str:
        return f"TAG_Int_Array({len(self.value)} ints)"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, TAG_Int_Array):
            return self.value == other.value
        if isinstance(other, list):
            return self.value == other
        return False


class TAG_Long_Array(NBTTag):
    tag_type = TAG_LONG_ARRAY

    def __init__(self, value: Optional[List[int]] = None):
        if value is None:
            self.value: List[int] = []
        else:
            self.value = [
                struct.unpack(">q", struct.pack(">q", int(v) & 0xFFFFFFFFFFFFFFFF))[0]
                if (int(v) > 9223372036854775807 or int(v) < -9223372036854775808)
                else int(v)
                for v in value
            ]

    def to_py(self) -> List[int]:
        return self.value

    def __len__(self) -> int:
        return len(self.value)

    def __repr__(self) -> str:
        return f"TAG_Long_Array({len(self.value)} longs)"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, TAG_Long_Array):
            return self.value == other.value
        if isinstance(other, list):
            return self.value == other
        return False


# Tag mapping by ID
TAG_CLASSES = {
    TAG_END: TAG_End,
    TAG_BYTE: TAG_Byte,
    TAG_SHORT: TAG_Short,
    TAG_INT: TAG_Int,
    TAG_LONG: TAG_Long,
    TAG_FLOAT: TAG_Float,
    TAG_DOUBLE: TAG_Double,
    TAG_BYTE_ARRAY: TAG_Byte_Array,
    TAG_STRING: TAG_String,
    TAG_LIST: TAG_List,
    TAG_COMPOUND: TAG_Compound,
    TAG_INT_ARRAY: TAG_Int_Array,
    TAG_LONG_ARRAY: TAG_Long_Array,
}


class NBTStreamReader:
    """Big-Endian binary stream reader for NBT."""

    def __init__(self, stream: io.BytesIO):
        self.stream = stream

    def read_byte(self) -> int:
        data = self.stream.read(1)
        if not data:
            raise EOFError("Unexpected end of NBT stream reading byte")
        return struct.unpack(">b", data)[0]

    def read_ubyte(self) -> int:
        data = self.stream.read(1)
        if not data:
            raise EOFError("Unexpected end of NBT stream reading unsigned byte")
        return data[0]

    def read_short(self) -> int:
        data = self.stream.read(2)
        if len(data) < 2:
            raise EOFError("Unexpected end of NBT stream reading short")
        return struct.unpack(">h", data)[0]

    def read_ushort(self) -> int:
        data = self.stream.read(2)
        if len(data) < 2:
            raise EOFError("Unexpected end of NBT stream reading unsigned short")
        return struct.unpack(">H", data)[0]

    def read_int(self) -> int:
        data = self.stream.read(4)
        if len(data) < 4:
            raise EOFError("Unexpected end of NBT stream reading int")
        return struct.unpack(">i", data)[0]

    def read_long(self) -> int:
        data = self.stream.read(8)
        if len(data) < 8:
            raise EOFError("Unexpected end of NBT stream reading long")
        return struct.unpack(">q", data)[0]

    def read_float(self) -> float:
        data = self.stream.read(4)
        if len(data) < 4:
            raise EOFError("Unexpected end of NBT stream reading float")
        return struct.unpack(">f", data)[0]

    def read_double(self) -> float:
        data = self.stream.read(8)
        if len(data) < 8:
            raise EOFError("Unexpected end of NBT stream reading double")
        return struct.unpack(">d", data)[0]

    def read_string(self) -> str:
        length = self.read_ushort()
        if length == 0:
            return ""
        data = self.stream.read(length)
        if len(data) < length:
            raise EOFError(f"Unexpected end of NBT stream reading string of length {length}")
        return data.decode("utf-8", errors="replace")

    def read_payload(self, tag_type: int) -> NBTTag:
        if tag_type == TAG_BYTE:
            return TAG_Byte(self.read_byte())
        elif tag_type == TAG_SHORT:
            return TAG_Short(self.read_short())
        elif tag_type == TAG_INT:
            return TAG_Int(self.read_int())
        elif tag_type == TAG_LONG:
            return TAG_Long(self.read_long())
        elif tag_type == TAG_FLOAT:
            return TAG_Float(self.read_float())
        elif tag_type == TAG_DOUBLE:
            return TAG_Double(self.read_double())
        elif tag_type == TAG_BYTE_ARRAY:
            length = self.read_int()
            data = self.stream.read(length)
            if len(data) < length:
                raise EOFError("Unexpected end of NBT stream reading byte array")
            return TAG_Byte_Array(data)
        elif tag_type == TAG_STRING:
            return TAG_String(self.read_string())
        elif tag_type == TAG_LIST:
            subtag_type = self.read_ubyte()
            length = self.read_int()
            items: List[NBTTag] = []
            if length > 0:
                for _ in range(length):
                    items.append(self.read_payload(subtag_type))
            return TAG_List(subtag_type, items)
        elif tag_type == TAG_COMPOUND:
            compound = TAG_Compound()
            while True:
                item_type = self.read_ubyte()
                if item_type == TAG_END:
                    break
                name = self.read_string()
                compound[name] = self.read_payload(item_type)
            return compound
        elif tag_type == TAG_INT_ARRAY:
            length = self.read_int()
            if length <= 0:
                return TAG_Int_Array([])
            data = self.stream.read(length * 4)
            if len(data) < length * 4:
                raise EOFError("Unexpected end of NBT stream reading int array")
            ints = list(struct.unpack(f">{length}i", data))
            return TAG_Int_Array(ints)
        elif tag_type == TAG_LONG_ARRAY:
            length = self.read_int()
            if length <= 0:
                return TAG_Long_Array([])
            data = self.stream.read(length * 8)
            if len(data) < length * 8:
                raise EOFError("Unexpected end of NBT stream reading long array")
            longs = list(struct.unpack(f">{length}q", data))
            return TAG_Long_Array(longs)
        else:
            raise ValueError(f"Unknown NBT tag type: {tag_type}")


class NBTStreamWriter:
    """Big-Endian binary stream writer for NBT."""

    def __init__(self, stream: io.BytesIO):
        self.stream = stream

    def write_byte(self, val: int) -> None:
        self.stream.write(struct.pack(">b", val))

    def write_ubyte(self, val: int) -> None:
        self.stream.write(struct.pack(">B", val))

    def write_short(self, val: int) -> None:
        self.stream.write(struct.pack(">h", val))

    def write_ushort(self, val: int) -> None:
        self.stream.write(struct.pack(">H", val))

    def write_int(self, val: int) -> None:
        self.stream.write(struct.pack(">i", val))

    def write_long(self, val: int) -> None:
        self.stream.write(struct.pack(">q", val))

    def write_float(self, val: float) -> None:
        self.stream.write(struct.pack(">f", val))

    def write_double(self, val: float) -> None:
        self.stream.write(struct.pack(">d", val))

    def write_string(self, val: str) -> None:
        raw = val.encode("utf-8")
        self.write_ushort(len(raw))
        self.stream.write(raw)

    def write_payload(self, tag: NBTTag) -> None:
        t = tag.tag_type
        if t == TAG_BYTE:
            self.write_byte(tag.value)  # type: ignore
        elif t == TAG_SHORT:
            self.write_short(tag.value)  # type: ignore
        elif t == TAG_INT:
            self.write_int(tag.value)  # type: ignore
        elif t == TAG_LONG:
            self.write_long(tag.value)  # type: ignore
        elif t == TAG_FLOAT:
            self.write_float(tag.value)  # type: ignore
        elif t == TAG_DOUBLE:
            self.write_double(tag.value)  # type: ignore
        elif t == TAG_BYTE_ARRAY:
            raw = tag.value  # type: ignore
            self.write_int(len(raw))
            self.stream.write(raw)
        elif t == TAG_STRING:
            self.write_string(tag.value)  # type: ignore
        elif t == TAG_LIST:
            subtag_type = tag.subtag_type  # type: ignore
            items = tag.value  # type: ignore
            self.write_ubyte(subtag_type)
            self.write_int(len(items))
            for item in items:
                self.write_payload(item)
        elif t == TAG_COMPOUND:
            for name, subtag in tag.value.items():  # type: ignore
                self.write_ubyte(subtag.tag_type)
                self.write_string(name)
                self.write_payload(subtag)
            self.write_ubyte(TAG_END)
        elif t == TAG_INT_ARRAY:
            ints = tag.value  # type: ignore
            self.write_int(len(ints))
            if ints:
                self.stream.write(struct.pack(f">{len(ints)}i", *ints))
        elif t == TAG_LONG_ARRAY:
            longs = tag.value  # type: ignore
            self.write_int(len(longs))
            if longs:
                self.stream.write(struct.pack(f">{len(longs)}q", *longs))
        else:
            raise ValueError(f"Cannot serialize unknown tag type: {t}")


class NBTFile:
    """High-level NBT document representation."""

    def __init__(self, root: Optional[TAG_Compound] = None, name: str = "", compressed: bool = True):
        self.root: TAG_Compound = root if root is not None else TAG_Compound()
        self.name: str = name
        self.compressed: bool = compressed

    @classmethod
    def load(cls, filepath_or_stream: Union[str, io.BytesIO, bytes]) -> NBTFile:
        raw_bytes: bytes
        if isinstance(filepath_or_stream, str):
            with open(filepath_or_stream, "rb") as f:
                raw_bytes = f.read()
        elif isinstance(filepath_or_stream, io.BytesIO):
            raw_bytes = filepath_or_stream.getvalue()
        elif isinstance(filepath_or_stream, (bytes, bytearray)):
            raw_bytes = bytes(filepath_or_stream)
        else:
            raise TypeError("Unsupported input type for NBT loading")

        compressed = False
        decompressed_bytes = raw_bytes

        # Check for Gzip compression (magic bytes 0x1f, 0x8b)
        if len(raw_bytes) >= 2 and raw_bytes[:2] == b"\x1f\x8b":
            compressed = True
            decompressed_bytes = gzip.decompress(raw_bytes)
        # Check for zlib (0x78)
        elif len(raw_bytes) >= 2 and raw_bytes[0] == 0x78 and raw_bytes[1] in (0x01, 0x5E, 0x9C, 0xDA):
            try:
                decompressed_bytes = zlib.decompress(raw_bytes)
                compressed = True
            except Exception:
                decompressed_bytes = raw_bytes

        stream = io.BytesIO(decompressed_bytes)
        reader = NBTStreamReader(stream)

        root_type = reader.read_ubyte()
        if root_type == TAG_END:
            return cls(TAG_Compound(), "", compressed=compressed)

        if root_type != TAG_COMPOUND:
            raise ValueError(f"NBT root tag must be TAG_Compound, found type {root_type}")

        root_name = reader.read_string()
        root_payload = reader.read_payload(TAG_COMPOUND)

        return cls(root=root_payload, name=root_name, compressed=compressed)  # type: ignore

    def save(self, filepath_or_stream: Union[str, io.BytesIO], compress: Optional[bool] = None) -> None:
        should_compress = self.compressed if compress is None else compress

        bio = io.BytesIO()
        writer = NBTStreamWriter(bio)

        # Write root tag header
        writer.write_ubyte(TAG_COMPOUND)
        writer.write_string(self.name)
        writer.write_payload(self.root)

        raw = bio.getvalue()
        if should_compress:
            final_bytes = gzip.compress(raw, compresslevel=6)
        else:
            final_bytes = raw

        if isinstance(filepath_or_stream, str):
            with open(filepath_or_stream, "wb") as f:
                f.write(final_bytes)
        elif isinstance(filepath_or_stream, io.BytesIO):
            filepath_or_stream.write(final_bytes)
        else:
            raise TypeError("Unsupported target type for NBT save")

    def to_bytes(self, compress: Optional[bool] = None) -> bytes:
        bio = io.BytesIO()
        self.save(bio, compress=compress)
        return bio.getvalue()

    def __getitem__(self, key: str) -> NBTTag:
        return self.root[key]

    def __setitem__(self, key: str, tag: NBTTag) -> None:
        self.root[key] = tag

    def __contains__(self, key: str) -> bool:
        return key in self.root

    def get(self, key: str, default: Any = None) -> Any:
        return self.root.get(key, default)

    def get_val(self, path: str, default: Any = None) -> Any:
        return self.root.get_val(path, default)

    def set_path(self, path: str, tag: NBTTag) -> None:
        self.root.set_path(path, tag)
