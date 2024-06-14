#!/usr/bin/env python3

import socket
import struct
from utils import ByteWriter, ByteReader
from stun import AttributeType, XorMappedAddressAttribute, stun_nat_type

SERVER_HOST = "localhost"
SERVER_PORT = 31337


def get_public_mapping() -> XorMappedAddressAttribute:
  message = stun_nat_type()

  for attr in message.attributes:
    if attr.type == AttributeType.XOR_MAPPED_ADDRESS:
      attr: XorMappedAddressAttribute = attr.value

      return attr
    
  raise Exception("No XOR-MAPPED-ADDRESS attribute found")


def request_server(client_id: int, other_id: int, client_ip: str, client_port: int) -> None:
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  sock.connect((SERVER_HOST, SERVER_PORT))

  writer = ByteWriter()
  writer.write_u16(client_id)
  writer.write_u16(other_id)
  writer.write_u32(client_ip)
  writer.write_u16(client_port)

  sock.send(writer.data)

  response = sock.recv(1024)
  reader = ByteReader(response)

  other_ip = socket.inet_ntoa(struct.pack("!L", reader.read_u32()))
  other_port = reader.read_u16()

  print(f"Received other client IP: {other_ip}, Port: {other_port}")

  sock.close()


def main() -> None:
  client_id = 0
  other_id = 1

  client_id = int(input("Enter your client ID: "), 16)
  other_id = int(input("Enter the other client ID to connect to: "), 16)

  mapping = get_public_mapping()
  print(mapping)

  request_server(client_id, other_id, mapping.ip, mapping.port)


if __name__ == "__main__":
  main()
