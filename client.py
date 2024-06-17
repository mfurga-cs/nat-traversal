#!/usr/bin/env python3

from threading import Thread
from requests import get
import socket
import struct

from utils import ByteWriter, ByteReader


MY_ID = 1
FRIEND_ID = 2

HOST = "0.0.0.0"

SERVER_IP = "83.29.144.133"
SERVER_PORT = 31337


def listen_for_messages(sock):
  while True:
    msg = ""

    while len(msg) == 0:
      try:
        msg = sock.recv(1024)

        print(f"Received message: {msg.decode()}")
      except ConnectionRefusedError:
        return
      except OSError:
        return


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

  # Create a UDP hole (from client with lower ID)
  if MY_ID < FRIEND_ID:
    print("Creating a UDP hole...")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, port_addr))
    sock.connect((friend_ip, friend_port))

    sock.send("Hello".encode())

    sock.close()

  # Create a connection to the friend
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

  sock.bind((HOST, port_addr))
  sock.connect((friend_ip, friend_port))

  listen_thread = Thread(target=listen_for_messages, args=(sock,))
  listen_thread.start()

  # Main loop for chat clients
  print("Use /send to send a message:")

  while True:
    msg = input()

    if msg.startswith("/send "):
      sock.send(msg[6:].encode())

  # Close the connection to the friend
  sock.close()

  # End the listening thread
  listen_thread.join()  


if __name__ == "__main__":
  main()

