import socket
import random
from datetime import datetime
from configs import CFG, Config
import os
import hashlib
import bencodepy
import json

config = Config.from_json(CFG)
used_ports = []

def get_host_default_interface_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def create_socket(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", port))
    used_ports.append(port)
    return sock

def free_socket(sock: socket.socket):
    used_ports.remove(sock.getsockname()[1])
    sock.close()

def generate_random_port() -> int: 
    available_ports = config.constants.AVAILABLE_PORTS_RANGE
    rand_port = random.randint(available_ports[0], available_ports[1])
    while rand_port in used_ports:
        rand_port = random.randint(available_ports[0], available_ports[1])
    return rand_port

def generate_torrent(file_path, tracker_address):
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    piece_length = config.constants.CHUNK_PIECES_SIZE
    pieces = []
    with open(file_path, "rb") as f:
        while chunk := f.read(piece_length):
            pieces.append(hashlib.sha1(chunk).digest())

    torrent = {
        "tracker address": tracker_address,
        "info": {
            "name": file_name,
            "length": file_size,
            "pieces count": len(pieces),
            "pieces": b"".join(pieces),  
        }
    }
    torrent_data = bencodepy.encode(torrent)
    torrent_filename = f"{file_path}.torrent"
    with open(torrent_filename, "wb") as f:
        f.write(torrent_data)

    print(f".torrent file generated: {torrent_filename}")

import socket

def create_tcp_socket(host='0.0.0.0', port=0, is_server=False):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    if is_server:
        # Server-side: bind the socket to the specified host and port, then listen for connections
        sock.bind((host, port))
        sock.listen(5)  # Allow up to 5 pending connections
        print(f"Server listening on {host}:{port}")
    else:
        sock.bind((host, port))

    if port == 0:
        port = sock.getsockname()[1]
        print(f"Socket bound to port {port}")

    # Return the socket object
    return sock

def create_udp_socket(port=0):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', port))  
    if port == 0:
        port = sock.getsockname()[1]
    return sock

def accept_connection(server_socket):
    client_socket, client_address = server_socket.accept()  # Accept a new connection
    print(f"Connection established with {client_address}")
    return client_socket, client_address

def log(content) -> None:
    current_time = datetime.now().strftime("%H:%M:%S")
    content = f"[{current_time}]  {content}\n"
    print(content)

def hash_torrent_info(torrent_file):
    info = parse_torrent_file(torrent_file)

    info_str = json.dumps(info, sort_keys=True).encode('utf-8')  # Ensure consistent ordering
    return hashlib.sha1(info_str).hexdigest()

def parse_torrent_file(torrent_file):
    with open(torrent_file, 'rb') as f:
        torrent_data = bencodepy.decode(f.read())
    
    info = torrent_data.get(b'info')
    name = info.get(b'name').decode('utf-8')
    length = info.get(b'length')
    piece_count = info.get(b'pieces count')
    
    # Generate a list of piece hashes (20-byte)
    
    return {
        'name': name,
        'length': length,
        'piece_count': piece_count
    }


if __name__ == "__main__":
    file = "Q74b.pdf"
    generate_torrent(file, "172.31.242.140")
