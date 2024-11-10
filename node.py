from utils import *
import argparse
from operator import itemgetter
import mmap
from itertools import groupby
import os
import warnings
warnings.filterwarnings("ignore")
from threading import Thread
from messages import *
from segment import UDPSegment
from configs import CFG, Config
config = Config.from_json(CFG)

class Node:
    def __init__(self, node_id, rcv_port, send_port):
        self.node_id = node_id
        self.rcv_socet = set_socket(rcv_port)
        self.send_socket = set_socket(send_port)
        self.files = self.fetch_owned_files()
        self.is_in_send_mode = False
        self.dowloaded_files = {}

    def fetch_owned_files(self) -> list:
        files = []
        node_files_dir = config.directory.node_files_dir + "node" + str(self.node_id)
        if os.path.isdir(node_files_dir):
            _, _, files = next(os.walk(node_files_dir))
        else: 
            os.makedirs(node_files_dir)
        return files 

    def send_segment(self, sock: socket.socket, data, addr):
        ip, des_port = addr
        segment = UDPSegment(src_port=sock.getsockname()[1], des_port=des_port, data=data)
        sock.sendto(segment.data, addr)

    def ask_file_size(self, filename, file_owner) -> int:
        temp_port = generate_random_port()
        temp_sock = set_socket(temp_port)
        des_node = file_owner[0]

        msg = Node2Node(src_node_id=self.node_id, des_node_id=des_node["node_id"], filename=filename)
        self.send_segment(sock=temp_sock, data=msg.encode(), addr=tuple(des_node["addr"]))

        while True:
            data, addr = temp_sock.recvfrom(config.constants.BUFFER_SIZE)
            des_node_response = Message.decode(data)
            size = des_node_response["size"]
            free_socket(temp_sock)

            # ????????????????????????????
            return size

    def tell_file_size(self, msg, addr):
        filename = msg["filename"]
        file_path = f"{config.directory.node_files_dir}node{self.node_id}/{filename}"
        file_size = os.stat(file_path).st_size
        response_msg = Node2Node(src_node_id=self.node_id, des_node_id=msg["src_node_id"], filename=filename, size=file_size)
        
        temp_port = generate_random_port()
        temp_sock = set_socket(temp_port)
        self.send_segment(sock=temp_sock, data=response_msg.encode(), addr=addr)
        free_socket(temp_sock)

    def split_file_to_chunks(self, file_path, rng):
        with open(file_path, "r+b") as f:
            mm = mmap.mmap(f.fileno(), 0)[rng[0]: rng[1]]
            piece_size = config.constants.CHUNK_PIECES_SIZE
            return [mm[p : p+piece_size] for p in range(0, rng[1] - rng[0], piece_size)]
        
    def reassemble_file(self, chunks, file_path):
        with open(file_path, "bw+") as f:
            for ch in chunks:
                f.write(ch)
            f.flush()
            f.close()
        
    def send_chunk(self, filename, range, des_node_id, des_port):
        file_path = f"{config.directory.node_files_dir}node{self.node_id}/{filename}"
        chunk_pieces = self.split_file_to_chunks(file_path, range)
        temp_port = generate_random_port()
        temp_sock = set_socket(temp_port)
        
        for idx, p in enumerate(chunk_pieces):
            msg = ChunkSharing(src_node_id=self.node_id, 
                               des_node_id=des_node_id, 
                               filename=filename, 
                               range=range, 
                               index=idx, 
                               chunk=p)
            log_content = f"The {idx}/{len(chunk_pieces)} has been sent!"
            log(log_content)
            self.send_segment(sock=temp_sock, data=Message.encode(msg), addr=("localhost", des_port))
        
        msg = ChunkSharing(src_node_id=self.node_id,
                           des_node_id=des_node_id,
                           filename=filename,
                           range=range)
        self.send_segment(sock=temp_sock, data=Message.encode(msg), addr=("localhost", des_port))
        log_content = "The process of sending a chunk to node{} of file {} has finished!".format(des_node_id, filename)
        log(log_content)
    
        msg = Node2Tracker(node_id=self.node_id, mode=config.tracker_requests_mode.UPDATE, filename=filename)
        self.send_segment(sock=temp_sock, data=Message.encode(msg), addr=tuple(config.constants.TRACKER_ADDR))
        free_socket(temp_sock)

    def receive_chunk(self, filename, range, file_owner):
        des_node = file_owner[0]
        msg = ChunkSharing(src_node_id=self.node_id, des_node_id=des_node["node_id"], filename=filename, range=range)
        temp_port = generate_random_port()
        temp_sock = set_socket(temp_port)
        self.send_segment(sock=temp_sock, data=msg.encode(), addr=tuple(des_node["addr"]))
        log_content = "I sent a request for a chunk of {0} for node{1}".format(filename, des_node["node_id"])
        log(log_content)

        while True:
            data, addr = temp_sock.recvfrom(config.constants.BUFFER_SIZE)
            msg = Message.decode(data)
            if msg["index"] == -1:
                free_socket(temp_sock)
                return
            self.dowloaded_files[filename].append(msg)

    def sort_downloaded_chunks(self, filename) -> list:
        sort_result_by_range = sorted(self.dowloaded_files[filename], key=itemgetter("range"))
        group_by_range = groupby(sort_result_by_range, key=lambda i: i["range"])
        sorted_downloaded_chunks = []
        for key, value in group_by_range:
            value_sorted_by_index = sorted(list(value), key=itemgetter("index"))
            sorted_downloaded_chunks.append(value_sorted_by_index)

        return sorted_downloaded_chunks
    
    def split_file_owners(self, file_owners, filename):
        owners = []
        for owner in file_owners:
            if owner[0]["node_id"] != self.node_id:
                owners.append(owner)
        
        if len(owners) == 0:
            log_content = f"No one has {filename}"
            log(log_content)
            return

        owners = sorted(owners, key=lambda x:x[1], reverse=True)
        to_be_used_owners = owners[:config.constants.MAX_SPLITTNES_RATE]
        log_content = f"You are going to download {filename} from Node(s) {[owner[0]['node_id'] for owner in to_be_used_owners]}"
        log(log_content)
        file_size = self.ask_file_size(filename=filename, file_owner=to_be_used_owners[0])
        log_content = f"The file {filename} which you are about to download, has size of {file_size} bytes"
        log(log_content)

        step = file_size/len(to_be_used_owners)
        chunks_ranges = [(round(step*i), round(step*(i+1))) for i in range(len(to_be_used_owners))]

        self.dowloaded_files[filename] = []
        neighboring_peers_threads = []
        for idx, obj in enumerate(to_be_used_owners):
            t = Thread(target=self.receive_chunk, args=(filename, chunks_ranges[idx], obj))
            t.setDaemon(True)
            t.start()
            neighboring_peers_threads.append(t)
        for t in neighboring_peers_threads:
            t.join()
        log_content = "All the chunks of {} has downloaded from neighboring peers. But they must be reassembled!".format(filename)
        log(log_content)

        sorted_chunks = self.sort_downloaded_chunks(filename)
        log_content = f"All the pieces of the {filename} is now sorted and ready to be reassembled."
        log(log_content)

        total_files = []
        file_path = f"{config.directory.node_files_dir}node{self.node_id}/{filename}"
        for chunk in sorted_chunks:
            for piece in chunk:
                total_files.append(piece["chunk"])
        self.reassemble_file(total_files, file_path)
        log_content = f"{filename} has successfully downloaded and saved in my files directory."
        log(log_content)
        self.files.append(filename)

    def handle_requests(self, msg, addr):
        if "size" in msg.keys() and msg["size"]==-1:
            self.tell_file_size(msg, addr)
        elif "range" in msg.keys() and msg["chunk"] is None:
            self.send_chunk(filename=msg["filename"], range=msg["range"], des_node_id=msg["src_node_id"], des_port=addr[1])

    def listen(self):
        while True:
            data, addr = self.send_socket.recvfrom(config.constants.BUFFER_SIZE)
            msg = Message.decode(data)
            self.handle_requests(msg, addr)
    
    def search_torrent(self, filename) -> dict:
        msg = Node2Tracker(node_id=self.node_id, mode=config.tracker_requests_mode.NEED, filename=filename)
        temp_port = generate_random_port()
        search_sock = set_socket(temp_port)
        self.send_segment(sock=search_sock, data=msg.encode(), addr=tuple(config.constants.TRACKER_ADDR))
    
        while True:
            data, addr = search_sock.recvfrom(config.constants.BUFFER_SIZE)
            tracker_msg = Message.decode(data)
            return tracker_msg

    def set_download_mode(self, filename):
        file_path = f"{config.directory.node_files_dir}node{self.node_id}/{filename}"
        if os.path.isfile(file_path):
            log_content = f"You already have this file!"
            log(log_content)
            return
        else:
            log_content = f"You just started to download {filename}. Let's search it in torrent!"
            log(log_content)
            tracker_response = self.search_torrent(filename)
            file_owners = tracker_response["search_result"]
            self.split_file_owners(file_owners, filename)

    def set_send_mode(self, filename):
        if filename not in self.files:
            log_content = f"You don't have {filename}"
            log(log_content)
            return

        message = Node2Tracker(node_id=self.node_id, mode=config.tracker_requests_mode.OWN, filename=filename)
        self.send_segment(sock=self.send_socket, data=message.encode(), addr=tuple(config.constants.TRACKER_ADDR))

        if self.is_in_send_mode:
            log_content = f"Some other node also requested a file from you! But you are already in SEND(upload) mode!"
            log(log_content)
            return
        else:
            self.is_in_send_mode = True
            log_content = f"You are free now! You are waiting for other nodes' requests!"
            log(log_content)
            t = Thread(target=self.listen, args=())
            t.setDaemon(True)
            t.start()

    def enter_torrent(self):
        msg = Node2Tracker(node_id=self.node_id, mode=config.tracker_requests_mode.REGISTER)
        self.send_segment(sock=self.send_socket, data=Message.encode(msg), addr=tuple(config.constants.TRACKER_ADDR))
        log_content = f"You entered Torrent."
        log(log_content)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-node_id', type=int,  help='id of the node you want to create')
    args = parser.parse_args()

    node = Node(node_id=args.node_id, 
                rcv_port=generate_random_port(),
                send_port=generate_random_port())
    log_content = f"***************** Node program started just right now! *****************"
    log(log_content)
    node.enter_torrent()

    print("ENTER YOUR COMMAND!")
    while True:
        command = ""
        while command == "":
            command = input()

        parts = command.split(" ")
        if len(parts) == 2:
            mode = parts[0]
            filename = parts[1]
            if mode == "send":
                node.set_send_mode(filename)
            elif mode == "download": 
                t = Thread(target=node.set_download_mode, args=(filename,))
                t.setDaemon(True)
                t.start()
        # elif mode == "upload":
        else:
            log_content = f"INVALID COMMAND ENTERED. TRY ANOTHER!"
            log(log_content)