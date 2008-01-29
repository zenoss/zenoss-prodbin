import os
import socket

import Globals
from Products.ZenUtils.Utils import zenPath

def main():
    dumpfile = zenPath('Products/ZenEvents/tests/trapdump.pcap')
    packets = []
    packet = []
    for line in os.popen('tcpdump -x -r %s' % dumpfile):
        if line[0] == '\t':
            hex = line.split(':', 1)[1].replace(' ','').strip()
            bytes = [hex[i:i+2] for i in range(0, len(hex), 2)]
            data = ''.join([chr(int(byte, 16)) for byte in bytes])
            packet.append(data)
        else:
            if packet:
                packets.append(''.join(packet))
    if packet:
        packets.append(''.join(packet))
    assert len(packets) == 2
    for p in packets:
        assert p[0] == chr(0x45)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for p in packets:
        dataoffset = 28
        p = p[28:]
        # p = p.replace('\xC0\xA8\x01\x40', '\x7f\x00\x00\x01')
        print `p`
        s.sendto( p, ('127.0.0.1', 1162))

main()
