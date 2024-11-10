from threading import Thread
from collections import defaultdict 
import json
from utils import *
from segment import UDPSegment
import os
from messages import *

class Tracker: 
    def __init__(self):
        self.tracker_socket = set_socket(config.constants.TRACKER_ADDR[1])
        self.file_owners_list = defaultdict(list)
        self.send_freq_list = defaultdict(int)
        self.has_informed_tracker = defaultdict(bool)

    def send_segment(self, sock: socket.socket, data, addr):
        ip, des_port = addr
        segment = UDPSegment(src_port=sock.getsockname()[1], des_port=des_port, data=data)
        sock.sendto(segment.data, addr)

    def save_db_as_json(self):
        if not os.path.exists(config.directory.tracker_db_dir):
            os.makedirs(config.directory.tracker_db_dir)

        nodes_info_path = config.directory.tracker_db_dir + "nodes.json"
        files_info_path = config.directory.tracker_db_dir + "files.json"

        temp_dict = {}
        for key, value in self.send_freq_list.items():
            temp_dict["node"+str(key)] = value
        nodes_json = open(nodes_info_path, "w")
        json.dump(temp_dict, nodes_json, indent=4, sort_keys=True)

        files_json = open(files_info_path, "w")
        json.dump(self.file_owners_list, files_json, indent=4, sort_keys=True)
        
    def add_file_owner(self, msg, addr):
        entry = {"node_id": msg["node_id"], "addr": addr}
        log_content = f"Node {msg["node_id"]} owns {msg["filename"]} and is ready to send."
        log(log_content)

        self.file_owners_list[msg["filename"]].append(json.dumps(entry))
        self.file_owners_list[msg["filename"]] = list(set(self.file_owners_list[msg["filename"]]))
        self.save_db_as_json()

    def search_file(self, msg, addr):
        log_content = f"Node{msg["node_id"]} is searching for {msg["filename"]}"
        log(log_content)

        matched_entries = []
        for json_entry in self.file_owners_list[msg["filename"]]:
            entry = json.loads(json_entry)
            matched_entries.append((entry, self.send_freq_list[entry["node_id"]]))

        tracker_response = Tracker2Node(des_node_id=msg["node_id"], search_result=matched_entries, filename=msg["filename"])
        self.send_segment(sock=self.tracker_socket, data=tracker_response.encode(), addr=addr)
    
    def update_db(self, msg):
        self.send_freq_list[msg["node_id"]] += 1
        self.save_db_as_json()
    
    def handle_node_request(self, data, addr):
        msg = Message.decode(data)
        mode = msg["mode"]
    
        if mode == config.tracker_requests_mode.REGISTER:
            log_content = f"Node {msg["node_id"]} have just entered the torrent."
            log(log_content)
        elif mode == config.tracker_requests_mode.OWN:
            self.add_file_owner(msg, addr)
        elif mode == config.tracker_requests_mode.NEED:
            self.search_file(msg, addr)
        elif mode == config.tracker_requests_mode.UPDATE:
            self.update_db(msg)

    def listen(self):
        while True:
            data, addr = self.tracker_socket.recvfrom(config.constants.BUFFER_SIZE)
            Thread(target=self.handle_node_request, args=(data, addr)).start()

    def run(self):
        log_content = f"***************** Tracker program started just right now! *****************"
        log(log_content)
        t = Thread(target=self.listen())
        t.setDaemon(True)
        t.start()
        t.join()

if __name__ == "__main__":
    Tracker().run()