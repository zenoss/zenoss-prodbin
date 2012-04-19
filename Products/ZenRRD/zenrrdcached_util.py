#!/usr/bin/env python
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import subprocess
import socket
import sys
import os
import optparse
import tempfile

"""
This utility will create a unix socket connection to rrdcached. It
can be used to send commands to the rrdcached daemon managed by
zenrrdcached.
"""

def flushDevice(device):
    with tempfile.NamedTemporaryFile('r+w') as t:
        path = "%s/perf/Devices/%s" % (os.environ['ZENHOME'], device)
        p = subprocess.Popen(["find", path, "-name", "*.rrd"], stdout=subprocess.PIPE)
        stdout, err = p.communicate()

        for rrds in stdout.splitlines():
            if rrds:
                t.write("FLUSH ")
                t.write(rrds.replace(" ", "\\ "))
                t.write("\n")
        t.flush()
        t.seek(0)
        p = subprocess.Popen([os.path.abspath(__file__), '-'], stdin=t)
        p.wait()

def commandLoop(cmds=None):
    s = None
    try:
        zenhome = os.environ['ZENHOME']

        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(zenhome + "/var/rrdcached.sock")
        if sys.stdin.isatty():
            prompt = "rrdcached> "
        else:
            prompt = ""

        while True:
            try:
                if cmds is not None:
                   cmd = cmds.pop(0)
                else:
                   cmd = raw_input(prompt)
            except EOFError as e:
                sys.exit()
            if cmd.lower() in ('\q', 'quit', 'exit', 'bye', ':q'):
                sys.exit()

            if len(cmd) > 0:
                s.send(cmd + "\n")
                data = s.recv(1024)
                print data,

            if cmds is not None and len(cmds) == 0:
                break

    finally:
        if s:
            s.send("QUIT\n")
            s.recv(1024)
            s.close()
        # reset the terminal in case things go south
        devnull = open(os.devnull, 'rw')
        subprocess.call('stty sane', shell=True, stdout=devnull, stderr=devnull)
        devnull.close()
        print

if __name__=="__main__":
 
    usage = """usage: %prog COMMAND

 -                  Interactively send commands to rrdcached.
 flush DEVICE_ID    Flush all the RRD files for the given device. 
 stats              Print zenrrdcached STATS."""
    parser = optparse.OptionParser(usage=usage)    
    options, args = parser.parse_args()

    if len(args) == 0:
        parser.print_usage()
    elif args[0] == "-":
        commandLoop()
    elif args[0].lower() == "flush":
        if len(args) < 2:
            parser.print_usage()
        for d in args[1:]:
            flushDevice(d)
    elif args[0].lower() == 'stats':
        commandLoop(['STATS'])
    else:
        parser.print_usage()


