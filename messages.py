import pickle

class Message:
    def __init__(self):
        pass

    def encode(self) -> bytes:
        return pickle.dumps(self.__dict__)
    
    @staticmethod
    def decode(data: bytes) -> dict:
        return pickle.loads(data)
    
class Tracker2Node(Message):
    def __init__(self, des_node_id, search_result, filename):
        super().__init__()
        self.des_node_id = des_node_id
        self.search_result = search_result
        self.filename = filename
    
class Node2Node(Message):
    def __init__(self, src_node_id, des_node_id, filename, size=-1):
        super().__init__()
        self.src_node_id = src_node_id
        self.des_node_id = des_node_id
        self.filename = filename
        self.size = size

class Node2Tracker(Message):
    def __init__(self, node_id, mode, filename=""):
        super().__init__()
        self.node_id = node_id
        self.filename = filename
        self.mode = mode

class ChunkSharing(Message):
    def __init__(self, src_node_id, des_node_id, filename, range, index=-1, chunk=None):
        super().__init__()
        self.src_node_id = src_node_id
        self.des_node_id = des_node_id
        self.filename = filename
        self.range = range
        self.index = index
        self.chunk = chunk