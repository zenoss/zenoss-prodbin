#!/usr/bin/env python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


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
    path = "%s/perf/Devices/%s" % (os.environ['ZENHOME'], device)
    if not os.path.isdir(path):
        # No RRD files for the specified device
        return
    with tempfile.NamedTemporaryFile('r+w') as t:
        p = subprocess.Popen(["find", path, "-name", "*.rrd"],
                             stdout=subprocess.PIPE)
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
    sockfile = None
    try:
        zenhome = os.environ['ZENHOME']

        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(zenhome + "/var/rrdcached.sock")
        sockfile = s.makefile('rw', 1024)
        if sys.stdin.isatty():
            prompt = "rrdcached> "
        else:
            prompt = ""

        in_batch = False
        while True:
            if cmds is not None:
                cmd = cmds.pop(0)
            else:
                try:
                    cmd = raw_input(prompt)
                    upper_cmd = cmd.rstrip().upper()
                    if upper_cmd in ('\Q', 'QUIT', 'EXIT', 'BYE', ':Q'):
                        break
                except EOFError:
                    break

            if cmd:
                sockfile.write(cmd + "\n")
                sockfile.flush()
                # Read response which consists of '<status_code> <message>'.
                # If <status_code> is > 0, then it signals the number of lines
                # which follow in the response. If it is negative, there was an
                # error.
                if in_batch and cmd == ".":
                    in_batch = False

                if not in_batch:
                    data = sockfile.readline().rstrip()
                    numlines, message = data.split(None, 1)
                    numlines = int(numlines)
                    print data
                    for i in range(numlines):
                        print sockfile.readline(),
                if cmd.upper() == "BATCH":
                    in_batch = True

            if cmds is not None and len(cmds) == 0:
                break

    finally:
        if sockfile:
            sockfile.write("QUIT\n")
            sockfile.flush()
            sockfile.readline()
            sockfile.close()
        if s:
            s.close()
        # reset the terminal in case things go south
        with open(os.devnull, 'rw') as devnull:
            subprocess.call('stty sane', shell=True, stdout=devnull,
                            stderr=devnull)

if __name__ == "__main__":
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
