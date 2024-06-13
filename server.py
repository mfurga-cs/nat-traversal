#!/usr/bin/env python3

import socket
import struct
import threading

from utils import ByteWriter, ByteReader

HOST = "0.0.0.0"
PORT = 31337

CONNECTIONS = {
  #0x0000: (0xaabbccdd, 0x1234)   # ID, IP address, port
}
CONNECTIONS_CV = threading.Condition()

def handle_connection(clientsock, addr) -> None:
  data = clientsock.recv(1024)
  reader = ByteReader(data)

  client_id = reader.read_u16()
  other_id = reader.read_u16()
  client_ip = reader.read_u32()
  client_port = reader.read_u16()

  with CONNECTIONS_CV:
    CONNECTIONS[client_id] = (client_ip, client_port)
    CONNECTIONS_CV.notify_all()

  ip = socket.inet_ntoa(struct.pack('!L', client_ip))
  print(f"[+] [{client_id:04x}] Added new connection to 0x{client_id:04x} ({ip}, {client_port})")
  print(f"[*] [{client_id:04x}] Waiting to connection from 0x{other_id:04x} ...")

  with CONNECTIONS_CV:
    CONNECTIONS_CV.wait_for(lambda: other_id in CONNECTIONS)
    other_ip, other_port = CONNECTIONS[other_id]

  writer = ByteWriter()
  writer.write_u32(other_ip)
  writer.write_u16(other_port)
  data = writer.data

  ip = socket.inet_ntoa(struct.pack('!L', other_ip))
  print(f"[+] [{client_id:04x}] Connection sent ({ip}, {other_port})")

  clientsock.send(data)
  clientsock.close()

def main() -> None:
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

  sock.bind((HOST, PORT))
  sock.listen(5)

  print(f"[*] Start listening on {HOST}:{PORT}")

  while True:
    (clientsock, addr) = sock.accept()
    t = threading.Thread(target=handle_connection, args=(clientsock, addr))
    t.start()

if __name__ == "__main__":
  main()

