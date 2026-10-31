import struct

def send_msg(sock, data: bytes):
    sock.sendall(struct.pack(">I", len(data)) + data)

def recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("socket closed early")
        buf += chunk
    return buf

def recv_msg(sock) -> bytes:
    length = struct.unpack(">I", recv_exact(sock, 4))[0]
    return recv_exact(sock, length)