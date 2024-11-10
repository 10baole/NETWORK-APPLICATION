from configs import CFG, Config
config = Config.from_json(CFG)

class UDPSegment:
    def __init__(self, src_port, des_port, data):
        assert len(data) <= config.constants.MAX_UDP_SEGMENT_DATA_SIZE, f"MAXIMUM DATA SIZE OF A UDP SEGMENT IS {config.constants.MAX_UDP_SEGMENT_DATA_SIZE}"
        self.src_port = src_port
        self.des_port = des_port
        self.data =  data
        self.length = len(data)