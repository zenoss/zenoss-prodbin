import math, sys, time, random, threading

make_hexip = lambda ip: ''.join(["%02x" % long(i) for i in ip.split('.')]) 
  
ip = ''
lock = threading.RLock()
try:  # only need to get the IP addresss once
  ip = socket.getaddrinfo(socket.gethostname(),0)[-1][-1][0]
  hexip = make_hexip(ip)
except: 
    # if we don't have an ip, default to someting in the 10.x.x.x private range
    ip = '10'
    rand = random.Random()
    for i in range(3):
        ip += '.' + str(rand.randrange(1, 0xff))  
        # might as well use IPv6 range if we're making it up
    hexip = make_hexip(ip)


def _unique_sequencer():
    _XUnit_sequence = sys.maxint

    while 1:
        yield _XUnit_sequence
        _XUnit_sequence -= 1
        if _XUnit_sequence <= 0:
            _XUnit_sequence = sys.maxint
_uniqueid = _unique_sequencer()

def generate():
    lock.acquire()
    try:
        frac, secs = math.modf(time.time())
        days, remain = divmod(secs, 86400)
        id = _uniqueid.next()
        return "%s%s%s%s" % (hexip, hex(int(days))[2:],
                               hex(int(remain))[2:], hex(id)[-7:])
    finally:
        lock.release()
