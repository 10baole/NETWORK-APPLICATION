import json
import base64

class Message:
    def __init__(self):
        pass

    def encode(self) -> bytes:
        """Encode the message object to a JSON string, converting any bytes to base64."""
        # Serialize the object to a dictionary
        dict_data = self.__dict__.copy()

        # Handle any attributes that are of type bytes
        # for key, value in dict_data.items():
        #     if isinstance(value, bytes):  # Check if the value is a bytes object
        #         dict_data[key] = base64.b64encode(value).decode('utf-8')  # Convert to base64 string

        # Convert the dictionary to a JSON string and then encode it to bytes
        json_string = json.dumps(dict_data)
        return json_string.encode('utf-8')  # Convert to bytes

    @staticmethod
    def decode(data: bytes) -> dict:
        """Decode a byte-like object to a JSON string, then parse it into a dictionary."""
        try:
            json_string = data.decode('utf-8')  # Decode bytes to a JSON string
            dict_data = json.loads(json_string)  # Convert the JSON string into a Python dictionary

            # Convert any base64 strings back to bytes
            # for key, value in dict_data.items():
            #     if isinstance(value, str) and key.endswith('chunk'):  # For chunk, or other fields with bytes
            #         dict_data[key] = base64.b64decode(value.encode('utf-8'))  # Decode from base64 back to bytes

            return dict_data
        except json.JSONDecodeError as e:
            #print(f"Error decoding JSON: {e}")
            return None


class Tracker2Node(Message):
    def __init__(self, des_node_id, search_result):
        super().__init__()
        self.des_node_id = des_node_id
        self.search_result = search_result


class Node2Tracker(Message):
    def __init__(self, node_id, node_recv_port, mode, info_hash=""):
        super().__init__()
        self.node_id = node_id
        self.node_recv_port = node_recv_port
        self.info_hash = info_hash
        self.mode = mode


class ChunkSharing(Message):
    def __init__(self, src_node_id, des_node, filename, range, index=-1, chunk_size=0, chunk=None):
        super().__init__()
        self.src_node_id = src_node_id
        self.des_node = des_node  # Dict {'node_id': , 'addr': }
        self.filename = filename
        self.range = range
        self.index = index
        self.chunk_size = chunk_size
        # self.chunk = chunk
