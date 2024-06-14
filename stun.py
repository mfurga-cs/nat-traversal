#!/usr/bin/env python3
# https://datatracker.ietf.org/doc/html/rfc5389

from typing import List
from enum import IntEnum
import socket
import struct
import random

from utils import ByteWriter, ByteReader

STUN_SERVER_HOST = "stunserver.stunprotocol.org"
STUN_SERVER_PORT = 3478
STUN_MAGIC_COOKIE = 0x2112a442


class AttributeType(IntEnum):
  MAPPED_ADDRESS = 0x0001
  CHANGE_REQUEST = 0x0003
  XOR_MAPPED_ADDRESS = 0x0020
  RESPONSE_ORIGIN = 0x802b
  OTHER_ADDRESS = 0x802c


class Attribute:
  def __init__(self, type: AttributeType, value: object):
    self.type = type
    self.value = value

  @classmethod
  def from_bytes(cls, data: bytes):
    reader = ByteReader(data)

    type = AttributeType(reader.read_u16())
    length = reader.read_u16()
    value = reader.read_bytes(length)

    attrs = {
      AttributeType.XOR_MAPPED_ADDRESS: XorMappedAddressAttribute,
      AttributeType.CHANGE_REQUEST: ChangeRequestAttribute
    }

    if type not in attrs:
      value = UnknownAttribute(value)
    else:
      value = attrs[type].from_bytes(value)

    return cls(type, value)

  @property
  def length(self) -> int:
    return len(self.value)

  def __len__(self) -> int:
    return len(self.to_bytes())

  def __str__(self) -> str:
    s = []
    s.append(f"Type: {self.type.name:<25}")
    s.append(f"Length: {self.length:<8}")
    s.append(f"Value: {str(self.value)}")
    return "".join(s)

  def to_bytes(self) -> bytes:
    writer = ByteWriter()

    writer.write_u16(self.type.value)
    writer.write_u16(self.length)
    data = writer.write_bytes(self.value.to_bytes())

    return data


class UnknownAttribute:
  def __init__(self, data: bytes):
    self.data = data

  @classmethod
  def from_bytes(cls, data: bytes):
    return cls(data)

  def to_bytes(self) -> bytes:
    return self.data

  def __len__(self) -> int:
    return len(self.to_bytes())

  def __str__(self) -> str:
    return f"?? 0x{self.data.hex()}"


class ChangeRequestAttribute:
  def __init__(self, change_ip: bool, change_port: bool):
    self.change_ip = change_ip
    self.change_port = change_port

  def __len__(self) -> int:
    return 4

  def to_bytes(self) -> bytes:
    writer = ByteWriter()
    v = [0, 1 << 2][self.change_ip] | [0, 1 << 1][self.change_port]
    data = writer.write_u32(v)
    return data


class XorMappedAddressAttribute:
  def __init__(self,
               family: int,
               port: int,
               ip: int):
    assert family == 0x0001   # IPv4
    self.family = family
    self.port = port
    self.ip = ip

  @classmethod
  def from_bytes(cls, data: bytes):
    reader = ByteReader(data)

    reader.read_u8()  # reserved
    family = reader.read_u8()
    assert family == 0x0001   # IPv4
    port = reader.read_u16() ^ (STUN_MAGIC_COOKIE >> 16)
    ip = reader.read_u32() ^ STUN_MAGIC_COOKIE

    return cls(family, port, ip)

  def to_bytes(self) -> bytes:
    writer = ByteWriter()

    writer.write_u8(0x00)  # reserved
    writer.write_u8(self.family)
    writer.write_u16(self.port ^ (STUN_MAGIC_COOKIE >> 16))
    data = writer.write_u32(self.ip ^ STUN_MAGIC_COOKIE)

    return data

  def __len__(self) -> int:
    return len(self.to_bytes())

  def __str__(self) -> str:
    ip = "{}.{}.{}.{}".format(self.ip >> 24,
                              (self.ip >> 16) & 0xff,
                              (self.ip >> 8) & 0xff,
                              (self.ip) & 0xff)
    return f"{ip}:{self.port}"


class MessageType(IntEnum):
  BINDING_REQUEST = 0x0001
  BINDING_SUCCESS_RESPONSE = 0x0101


class Message:
  def __init__(self,
               type: MessageType,
               transaction_id: bytes,
               attributes: List[Attribute]):
    self.type = type
    self.transaction_id = transaction_id
    assert len(transaction_id) == 12
    self.attributes = attributes

  @classmethod
  def from_bytes(cls, data: bytes):
    reader = ByteReader(data)

    type = MessageType(reader.read_u16())
    length = reader.read_u16()
    cookie = reader.read_u32()
    assert cookie == STUN_MAGIC_COOKIE
    transaction_id = reader.read_bytes(12)
    data = reader.read_bytes(length)

    attributes = []
    while len(data) > 0:
      attribute = Attribute.from_bytes(data)
      attributes.append(attribute)
      data = data[len(attribute):]

    return cls(type, transaction_id, attributes)

  @property
  def length(self) -> int:
    return sum(len(attr) for attr in self.attributes)

  def to_bytes(self) -> bytes:
    writer = ByteWriter()

    attributes = b"".join(attr.to_bytes() for attr in self.attributes)

    writer.write_u16(self.type.value)
    writer.write_u16(self.length)
    writer.write_u32(STUN_MAGIC_COOKIE)
    writer.write_bytes(self.transaction_id)
    data = writer.write_bytes(attributes)

    return data

  def __str__(self) -> str:
    s = []
    s.append("== STUN Message ==")
    s.append(f"  Type           : {self.type.name}")
    s.append(f"  Length         : {self.length}")
    s.append(f"  Transaction ID : 0x{self.transaction_id.hex()}")
    s.append(f"  Attributes     :")

    for attr in self.attributes:
      s.append(" " * 4 + str(attr))

    return "\n".join(s)


def stun_nat_type() -> Message:
  source_ip = "0.0.0.0"
  source_port = 4000

  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

  print(f"Binding on {source_ip}:{source_port} ...")
  sock.bind((source_ip, source_port))

  transaction_id = random.randbytes(12)
  request = Message(
    type=MessageType.BINDING_REQUEST,
    transaction_id=transaction_id,
    attributes=[
      Attribute(
        type=AttributeType.CHANGE_REQUEST,
        value=ChangeRequestAttribute(change_ip=False, change_port=False)
      )
    ]
  )
  sock.sendto(request.to_bytes(), (STUN_SERVER_HOST, STUN_SERVER_PORT))

  response, addr = sock.recvfrom(1024)
  message = Message.from_bytes(response)
  assert transaction_id == message.transaction_id

  print(f"Response from {addr[0]}:{addr[1]}")
  print(message)

  return message


if __name__ == "__main__":
  message = stun_nat_type()

