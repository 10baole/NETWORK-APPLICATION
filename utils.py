import socket
import random
from datetime import datetime
from configs import CFG, Config
config = Config.from_json(CFG)

used_ports = []

def set_socket(port: int) -> socket.socket:
    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("localhost", port))
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

def log(content) -> None:
    current_time = datetime.now().strftime("%H:%M:%S")
    content = f"[{current_time}]  {content}\n"
    print(content)