#!/usr/bin/env python3

from requests import get
from time import sleep
import socket
import struct

from utils import ByteWriter, ByteReader


MY_ID = 1
FRIEND_ID = 2

HOST = "0.0.0.0"

SERVER_IP = "1.2.3.4"
SERVER_PORT = 31337


def main() -> None:
  print(f"Running client with ID {MY_ID}")

  # Get my public IP address
  public_ip = get("https://api.ipify.org").content.decode("utf8")
  public_ip_num = struct.unpack("!L", socket.inet_aton(public_ip))[0]

  # Start a TCP connection to the server
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  sock.connect((SERVER_IP, SERVER_PORT))

  port_addr = sock.getsockname()[1]

  # Send a request to the server
  writer = ByteWriter()

  writer.write_u16(MY_ID)
  writer.write_u16(FRIEND_ID)
  writer.write_u32(public_ip_num)
  writer.write_u16(port_addr)

  sock.send(writer.data)

  # Wait for IP address and port of a friend
  friend_data = sock.recv(1024)

  reader = ByteReader(friend_data)

  friend_ip_num = reader.read_u32()
  friend_port = reader.read_u16()

  friend_ip = socket.inet_ntoa(struct.pack('!L', friend_ip_num))

  print(f"Friend's IP address and port is {friend_ip}:{friend_port}")

  # Close the connection to the server
  sock.close()

  if MY_ID == 1:
    # Create a UDP hole
    print("Creating a UDP hole...")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, port_addr))
    sock.connect((friend_ip, friend_port))

    sock.send("Hello".encode())

    sock.close()

    # Wait for a message from the friend
    print("Waiting for a message from the friend")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    sock.bind((HOST, port_addr))

    msg_data = ""
    while len(msg_data) == 0:
      msg_data = sock.recv(1024)

    print(f"Received message from the friend: {msg_data}")
  else:
    # Wait a few seconds
    sleep(5)

    # Use the created UDP hole
    print("Use the created UDP hole...")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, port_addr))
    sock.connect((friend_ip, friend_port))

    sock.send("Hello my friend!".encode())

  # Close the connection to the friend
  sock.close()


if __name__ == "__main__":
  main()

