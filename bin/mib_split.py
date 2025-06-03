#!/usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

import re
import sys

if len(sys.argv) < 2:
    print("Usage: mib_split <MIB filaname>")
    sys.exit(1)

begin_re = re.compile(r"^(\S+)\s+DEFINITIONS\s+::=\s+BEGIN")

with open(sys.argv[1], "r") as source_mib:
    dest_mib = None

    for line in source_mib:
        matches = begin_re.search(line)
        if matches:
            filename = matches.groups()[0] + ".txt"
            print("Writing " + filename)

            if dest_mib:
                dest_mib.close()
                dest_mib = None
            dest_mib = open(filename, "w")

        if dest_mib:
            dest_mib.write(line)

    if dest_mib:
        dest_mib.close()
