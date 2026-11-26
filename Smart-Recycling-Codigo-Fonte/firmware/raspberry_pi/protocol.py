"""Bounded serial framing shared by the Pi worker and integration tests."""
import json
import zlib
class LineFramer:
    def __init__(self,limit=2048):self.limit=limit;self.buffer=bytearray();self.discard=False
    def feed(self,chunk):
        lines=[]
        for byte in chunk:
            if byte==10:
                if not self.discard and self.buffer:lines.append(bytes(self.buffer).rstrip(b'\r'))
                self.buffer.clear();self.discard=False
            elif not self.discard:
                if len(self.buffer)>=self.limit:self.buffer.clear();self.discard=True
                else:self.buffer.append(byte)
        return lines

def encode_bridge(data):
    body=json.dumps(data,separators=(',',':'),allow_nan=False).encode()
    return body+b'\t'+f'{zlib.crc32(body):08x}'.encode()+b'\n'

def decode_bridge(line):
    body,checksum=line.rstrip(b'\r\n').rsplit(b'\t',1)
    if len(checksum)!=8 or int(checksum,16)!=zlib.crc32(body):raise ValueError('CRC mismatch')
    return json.loads(body)
