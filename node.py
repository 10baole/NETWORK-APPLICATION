import argparse
import bencodepy
import os
import socket
import hashlib
from threading import Thread
import json
from utils import create_udp_socket, create_tcp_socket, generate_random_port, free_socket, get_host_default_interface_ip, log, create_socket, generate_torrent
from messages import Message, Node2Tracker, ChunkSharing
from configs import CFG, Config  
import mmap
from operator import itemgetter
from itertools import groupby
import base64
import time
config = Config.from_json(CFG)

class Node:
    def __init__(self, node_id, rcv_port, send_port):
        self.node_id = node_id
        self.node_ip = get_host_default_interface_ip() 
        self.rcv_socket = create_tcp_socket(self.node_ip, port=rcv_port, is_server=True)  
        self.send_socket = create_tcp_socket(self.node_ip, port=send_port, is_server=False)
        self.files = [] 
        self.is_in_send_mode = False  
        self.downloaded_files = {}  

        self.node_files_dir = config.directory.node_files_dir + "node" + str(self.node_id)
        if os.path.isdir(self.node_files_dir):
            _, _, self.files = next(os.walk(self.node_files_dir))
        else: 
            os.makedirs(self.node_files_dir)
        
    def check_files(self):
        if os.path.isdir(self.node_files_dir):
            _, _, self.files = next(os.walk(self.node_files_dir))
        else: 
            os.makedirs(self.node_files_dir)

    def generate_torrent_files(self, file):
        file_path = os.path.join(self.node_files_dir, file)
        generate_torrent(file_path, config.constants.TRACKER_ADDR)

    def hash_torrent_info(self, torrent_file):
        info = self.parse_torrent_file(torrent_file)
        info_str = json.dumps(info, sort_keys=True).encode('utf-8')  
        return hashlib.sha1(info_str).hexdigest()

    def parse_torrent_file(self, torrent_file):
        torrent_file_path = os.path.join(self.node_files_dir, torrent_file)
        with open(torrent_file_path, 'rb') as f:
            torrent_data = bencodepy.decode(f.read())
        
        info = torrent_data.get(b'info')
        name = info.get(b'name').decode('utf-8')
        length = info.get(b'length')
        piece_length = info.get(b'piece length')
        
        return {
            'name': name,
            'length': length,
            'piece_length': piece_length
        }

    def register_with_tracker(self):
        msg = Node2Tracker(node_id=self.node_id, node_recv_port=self.rcv_socket.getsockname()[1], mode=CFG.tracker_requests_mode.REGISTER)
        self.send_segment(sock=self.send_socket, data=Message.encode(msg), addr=tuple(config.constants.TRACKER_ADDR))

    def request_file_info(self, torrent_file):
        hash_info = self.hash_torrent_info(torrent_file)
        msg = Node2Tracker(node_id=self.node_id, node_recv_port=self.rcv_socket.getsockname()[1], mode=config.tracker_requests_mode.NEED, info_hash=hash_info)
        temp_port = generate_random_port()
        search_sock = create_udp_socket(temp_port)
        self.send_segment(sock=search_sock, data=msg.encode(), addr=tuple(config.constants.TRACKER_ADDR))
        
        while True:
            data, addr = search_sock.recvfrom(config.constants.BUFFER_SIZE)
            tracker_msg = Message.decode(data)
            return tracker_msg

    def send_segment(self, sock: socket.socket, data, addr):
        # try:
        #     sock.sendall(data)  # Send data to the given address
        # except socket.error as e:
        #     print(f"Error sending data to {addr}: {e}")
        #     # Optionally, handle the error (e.g., retry, exit, etc.)
        # except Exception as e:
        #     print(f"Unexpected error: {e}")
        #     # Optionally, handle unexpected errors
        # try:
        #     sock.sendto(data, addr)  # For UDP use sendto() instead of sendall()
        # except socket.error as e:
        # print(f"Error sending data to {addr}: {e}")
        # try:
            if sock.type == socket.SOCK_DGRAM:  # If it's a UDP socket
                sock.sendto(data, addr)  # For UDP use sendto()
            elif sock.type == socket.SOCK_STREAM:  # If it's a TCP socket
                
                sock.sendall(data)  # For TCP use sendall()
        # except socket.error as e:
        #     print(f"Error sending data to {addr}: {e}")
        # except Exception as e:
        #     print(f"Unexpected error: {e}")    

    def split_file_to_chunks(self, file_path, rng):
        with open(file_path, "r+b") as f:
            mm = mmap.mmap(f.fileno(), 0)[rng[0]: rng[1]]
            piece_size = config.constants.CHUNK_PIECES_SIZE

            return [mm[p: p + piece_size] for p in range(0, rng[1] - rng[0], piece_size)]

    def reassemble_file(self, chunks, file_path):
        with open(file_path, "bw+") as f:
            for ch in chunks:
                f.write(ch)
            f.flush()
            f.close()

    def ask_chunk_size(self, msg, ask_sock, addr):
        self.send_segment(sock=ask_sock, data=msg.encode(), addr=addr)

    def send_chunk(self, torrent_file, rng, des_node, client_socket):
        filename = self.parse_torrent_file(torrent_file).get("name")
        file_path = os.path.join(config.directory.node_files_dir, f"node{self.node_id}", filename)
        chunk_pieces = self.split_file_to_chunks(file_path, rng)
        print("Halo Im ChunkPiece", type(chunk_pieces[0]))
        for idx, p in enumerate(chunk_pieces):
            print('piece: ', idx)
            print('len chunk: ', len(p))
            msg = ChunkSharing(src_node_id=self.node_id, des_node=des_node, filename=filename, range=rng, index=idx, chunk_size=len(p))
            data = Message.encode(msg)
            self.send_segment(sock=client_socket, data=data, addr=des_node['addr'])
            # encoded_chunk = base64.b64decode(p).encode('utf-8')
            confirmation = client_socket.recv(1024).decode('utf-8')
            print(confirmation)
            if confirmation == 'READY':
                client_socket.sendall(p)

        # msg = ChunkSharing(src_node_id=self.node_id, des_node=des_node, filename=filename, range=rng)
        # self.send_segment(sock=client_socket, data=Message.encode(msg), addr=des_node['addr'])
        log_content = f"Finished sending the chunk to node {des_node['node_id']} of file {filename}!"
        log(log_content)
        client_socket.close()

        # sok
        # msg = Node2Tracker(node_id=self.node_id, node_recv_port=self.rcv_socket.getsockname()[1], mode=config.tracker_requests_mode.UPDATE)
        # self.send_segment(sock=client_socket, data=Message.encode(msg), addr=tuple(config.constants.TRACKER_ADDR))
        
    
    def receive_chunk(self, torrent_file, rng, file_owner):
        filename = self.parse_torrent_file(torrent_file).get("name")
        msg = ChunkSharing(src_node_id=self.node_id, des_node=file_owner, filename=filename, range=rng)
        temp_port = generate_random_port()
        temp_sock = create_tcp_socket(self.node_ip, temp_port, False)
        temp_sock.connect(tuple(file_owner["addr"]))
        print(file_owner['addr'])
        self.send_segment(sock=temp_sock, data=msg.encode(), addr=tuple(file_owner["addr"]))
        log_content = f"Sent request for a chunk of {filename} from node {file_owner['node_id']}"
        log(log_content)
        a = 0
        # while True:
        #     data = temp_sock.recv(4000)
        #     if not data:
        #         continue
        #     msg = Message.decode(data)
        #     if msg is None:
        #         # log("Failed to decode message")
        #         continue

        #     if "index" in msg and msg["index"] == -1:
        #         temp_sock.close()
        #         return
            
        #     self.downloaded_files[filename].append(msg)

        while True:
            # Receive metadata first
            
            metadata = temp_sock.recv(16192)
            try:
                chunk_msg = Message.decode(metadata)
                print(chunk_msg)
            except: chunk_msg = None
            if not chunk_msg or "index" not in chunk_msg:
                break
            
            temp_sock.send("READY".encode('utf-8'))
            
            chunk_size = chunk_msg["chunk_size"]

            chunk_data = temp_sock.recv(chunk_size)
            
            # chunk_data = base64.b64encode(chunk_data).decode('utf-8')
            
            # Store chunk in the buffer
            self.downloaded_files.setdefault(filename, []).append({
                "index": chunk_msg["index"],
                "range": chunk_msg["range"],
                "chunk": chunk_data
            })
            print(f"Received chunk {chunk_msg['index']} of size {chunk_size}")
    
    def sort_downloaded_chunks(self, torrent_file):
        filename = self.parse_torrent_file(torrent_file).get("name")
        sorted_chunks = sorted(self.downloaded_files[filename], key=itemgetter("range"))
        group_by_range = groupby(sorted_chunks, key=lambda i: i["range"])
        sorted_downloaded_chunks = []

        for key, value in group_by_range:
            sorted_chunks_by_index = sorted(list(value), key=itemgetter("index"))
            sorted_downloaded_chunks.append(sorted_chunks_by_index)
        return sorted_downloaded_chunks

    def split_file_owners(self, torrent_file, file_owners):
        filename = self.parse_torrent_file(torrent_file).get("name")
        owners = [owner for owner in file_owners if owner["node_id"] != self.node_id]
        if len(owners) == 0:
            log(f"No one has {filename}")
            return

        to_be_used_owners = owners[:config.constants.MAX_SPLITTNES_RATE]
        log_content = f"Downloading {filename} from nodes {[owner['node_id'] for owner in to_be_used_owners]}"
        log(log_content)

        file_size = self.parse_torrent_file(torrent_file=torrent_file).get('length')
        log(f"The file {filename} has size {file_size} bytes.")

        step = file_size / len(to_be_used_owners)
        chunks_ranges = [(round(step*i), round(step*(i+1))) for i in range(len(to_be_used_owners))]

        self.downloaded_files[filename] = []
        neighboring_peers_threads = []
        print(print(len(to_be_used_owners)))
        for idx, owner in enumerate(to_be_used_owners):
            t = Thread(target=self.receive_chunk, args=(torrent_file, chunks_ranges[idx], owner))
            t.daemon=True
            t.start()
            neighboring_peers_threads.append(t)
        for t in neighboring_peers_threads:
            t.join()

        log_content = "All the chunks of {} has downloaded from neighboring peers. But they must be reassembled!".format(filename)
        log(log_content)

        sorted_chunks = self.sort_downloaded_chunks(torrent_file=torrent_file)
        log_content = f"All the pieces of the {filename} is now sorted and ready to be reassembled."
        log(log_content)

        total_file = []
        file_path = f"{config.directory.node_files_dir}node{self.node_id}/{filename}"
        for chunk in sorted_chunks:
            for piece in chunk:
                total_file.append(piece["chunk"])
        self.reassemble_file(chunks=total_file, file_path=file_path)
        log_content = f"{filename} has successfully downloaded and saved in my files directory."
        log(log_content)
        self.files.append(filename)
        self.seeding(torrent_file)

    def handle_requests(self, msg, addr, client_socket):
        if "range" in msg.keys():
            print("A node has connected to me")
            self.send_chunk(torrent_file=msg['filename']+'.torrent',rng=msg["range"],
                             des_node={'node_id': msg['src_node_id'], 
                                                          'addr': addr}, client_socket=client_socket)
        return

    def listen(self):
        while True:
            try:
                client_socket, client_addr = self.rcv_socket.accept() # Using TCP for receiving requests
                data = client_socket.recv(config.constants.BUFFER_SIZE)
                msg = Message.decode(data)  
                t = Thread(target=self.handle_requests, args=(msg, client_addr, client_socket))
                t.daemon = True
                t.start()
            except socket.error as e:
                print(f"Error while receiving data: {e}")
            except Exception as e:
                print(f"Unexpected error: {e}")

    def enter_torrent(self):
        msg = Node2Tracker(node_id=self.node_id, node_recv_port=self.rcv_socket.getsockname()[1], mode=config.tracker_requests_mode.REGISTER)
        temp_port = generate_random_port()
        temp_sock = create_udp_socket(temp_port)
        self.send_segment(sock=temp_sock, data=Message.encode(msg), addr=tuple(config.constants.TRACKER_ADDR))
        log_content = f"Successfully entered torrent."
        log(log_content)

    def download(self, torrent_file):
        filename = self.parse_torrent_file(torrent_file).get("name")
        file_path = f"{config.directory.node_files_dir}node{self.node_id}/{filename}"
        if os.path.isfile(file_path):
            log_content = f"You already have this file!"
            log(log_content)
            return
        else:
            log_content = f"You just started to download {filename}. Let's search it in torrent!"
            log(log_content)
            tracker_response = self.request_file_info(torrent_file)
            file_owners = tracker_response["search_result"]
            self.split_file_owners(torrent_file=torrent_file, file_owners=file_owners)

    def seeding(self, torrent_file):
        self.check_files()
        if torrent_file not in self.files:
            log(f"You don't have {torrent_file}")
            return
        hash_info = self.hash_torrent_info(torrent_file)

        message = Node2Tracker(node_id=self.node_id, node_recv_port=self.rcv_socket.getsockname()[1], mode=config.tracker_requests_mode.OWN, info_hash=hash_info)
        seeding_sock = create_socket(generate_random_port())
        self.send_segment(sock=seeding_sock, data=message.encode(), addr=tuple(config.constants.TRACKER_ADDR))
        
        free_socket(seeding_sock)
        # print(message.info_hash, message.node_id, message.mode)
        if self.is_in_send_mode:
            log_content = f"Some other node also requested a file from you! But you are already in SEND(upload) mode!"
            log(log_content)
            return
        else:
            self.is_in_send_mode = True
            log(f"Waiting for other nodes' requests!")
            t = Thread(target=self.listen, args=())
            t.daemon = True
            t.start()
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-node_id', type=int, help='ID of the node to create')
    parser.add_argument('-torrent_file', type=str, help='Path to the .torrent file')
    args = parser.parse_args()

    node = Node(node_id=args.node_id,
                rcv_port=generate_random_port(),
                send_port=generate_random_port())
    log_content = f"***************** Node program started! *****************"
    log(log_content)
    node.enter_torrent()

    print("ENTER YOUR COMMAND!")
    while True:
        command = input()
        parts = command.split(" ")
        if len(parts) == 2:
            mode = parts[0]
            filename = parts[1]
            # filename = 'Q74b.pdf.torrent'
            if mode == "SEEDING":
                node.seeding(filename)
            elif mode == "DOWNLOAD":
                t = Thread(target=node.download, args=(filename,))
                t.daemon = True
                t.start()
            elif mode == "MAKETORRENT":
                node.generate_torrent_files(filename)
        else:
            log_content = f"INVALID COMMAND. TRY AGAIN!"
            log(log_content)