import json
import os
from threading import Thread
from utils import create_socket, get_host_default_interface_ip, log
from collections import defaultdict
from messages import Message, Node2Tracker, ChunkSharing, Tracker2Node
from configs import CFG, Config
import shutil

config = Config.from_json(CFG)

class Tracker:
    def __init__(self, port):
        self.port = port
        self.db_dir = config.directory.tracker_db_dir
        self.node_data = defaultdict(list)
        self.node_requests = defaultdict(list)
        self.socket = create_socket(port)
        self.ip = get_host_default_interface_ip()

        if not os.path.exists(self.db_dir):
            os.makedirs(self.db_dir)
    
    def send_segment(self, data, addr):
        self.socket.sendto(data.encode(), addr)
        log(f"Sent response to {addr}")

    def save_db(self):
        nodes_json_path = os.path.join(self.db_dir, "nodes.json")
        with open(nodes_json_path, 'w') as nodes_file:
            json.dump(self.node_requests, nodes_file, indent=4)

        files_json_path = os.path.join(self.db_dir, "files.json")
        with open(files_json_path, 'w') as files_file:
            json.dump(self.node_data, files_file, indent=4)

    def load_db(self):
        nodes_json_path = os.path.join(self.db_dir, "nodes.json")
        if os.path.exists(nodes_json_path):
            with open(nodes_json_path, 'r') as nodes_file:
                self.node_requests = json.load(nodes_file)

        files_json_path = os.path.join(self.db_dir, "files.json")
        if os.path.exists(files_json_path):
            with open(files_json_path, 'r') as files_file:
                self.node_data = json.load(files_file)

    def register_node(self, node_id, addr):
        if node_id not in self.node_requests:
            self.node_requests[node_id] = 0

        log(f"Node {node_id} registered with address {addr}")
        self.save_db()
    
    def add_file_owner(self, msg, addr):
        file_entry = {'node_id': msg['node_id'], 'addr': addr}
        self.node_data[msg['info_hash']].append(json.dumps(file_entry))
        # self.node_data[msg['info_hash']] = list({json.dumps(entry) for entry in self.node_data[info_hash]})  # Remove duplicates
        log(f"Node {msg['node_id']} now owns file with info_hash {msg['info_hash']}")
        self.save_db()

    def search_file(self, node_id, info_hash, addr):
        if info_hash not in self.node_data:
            log(f"File with info_hash {info_hash} not found in tracker!")
            response = Tracker2Node(node_id, f"No node found for searching file!")
            self.send_segment(response, addr)
            return
        
        matched_entries = []
        for json_entry in self.node_data[info_hash]:
            entry = json.loads(json_entry)
            matched_entries.append(entry)

        log(matched_entries)
        response = Tracker2Node(node_id, matched_entries)
        self.send_segment(response, addr)

    def update_node_request_count(self, node_id):
        self.node_requests[node_id] += 1
        self.save_db()

    def handle_request(self, data, addr):
        try:
            msg = Message.decode(data)
            mode = msg["mode"]
            log(f"Received request from {addr} with mode: {mode}")

            if mode == config.tracker_requests_mode.REGISTER:
                self.register_node(msg['node_id'], addr)
            elif mode == config.tracker_requests_mode.OWN:
                log(msg)
                self.add_file_owner(msg, (addr[0], msg['node_recv_port']))
            elif mode == config.tracker_requests_mode.NEED:
                self.search_file(msg['node_id'], msg['info_hash'], addr)
            elif mode == config.tracker_requests_mode.UPDATE:
                self.update_node_request_count(msg['node_id'])
            else:
                log(f"Unknown mode: {mode}")
        except Exception as e:
            log(f"Error processing request: {e}")
        
    def listen(self):
        while True:
            data, addr = self.socket.recvfrom(1024)
            Thread(target=self.handle_request, args=(data, addr)).start()

    def run(self):
        log_content = f"***************** Tracker program started on address {self.ip} at port {self.port} *****************"
        log(log_content)
        self.load_db()
        t = Thread(target=self.listen)
        t.daemon = True
        t.start()
        t.join()

if __name__ == "__main__":
    if os.path.exists("tracker_db"):
        shutil.rmtree('tracker_db')
    tracker = Tracker(port=6081)
    tracker.run()