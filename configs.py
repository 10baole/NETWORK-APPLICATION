import json

CFG = {
    "directory": {
        "logs_dir": "logs/",
        "node_files_dir": "node_files/",
        "tracker_db_dir": "tracker_db/",
    },
    "constants":
    {
        "AVAILABLE_PORTS_RANGE": (1024, 65535),
        "TRACKER_ADDR": ("192.168.1.50", 6081),
        "MAX_UDP_SEGMENT_DATA_SIZE": 65536,
        "BUFFER_SIZE": 10000,
        "CHUNK_PIECES_SIZE": 4096,
        "MAX_SPLITTNES_RATE": 3,
    },
    "tracker_requests_mode": {
        "REGISTER": 0,
        "OWN": 1,
        "NEED": 2,      
        "UPDATE": 3,
        "EXIT": 4
    }
}

class Config:
    def __init__(self, directory, constants, tracker_requests_mode):
        self.directory = directory
        self.constants = constants
        self.tracker_requests_mode = tracker_requests_mode

    @classmethod
    def from_json(cls, cfg):
        params = json.loads(json.dumps(cfg), object_hook=HelperObject)
        return cls(params.directory, params.constants, params.tracker_requests_mode)

class HelperObject(object):
    def __init__(self, dict_):
        self.__dict__.update(dict_)