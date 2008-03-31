#!/usr/bin/env python
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import sys, re

if (len(sys.argv) < 2):
    print "Usage: mib_split <MIB filaname>"
    sys.exit(1)

begun = 0
begin_re = re.compile(r'^(\S+)\s+DEFINITIONS\s+::=\s+BEGIN')

source_mib = open(sys.argv[1], 'r')
dest_mib = None

for line in source_mib:
    matches = begin_re.search(line)
    if matches:
        begun += 1

        filename = matches.groups()[0] + '.txt'
        print "Writing " + filename

        if dest_mib: dest_mib.close()
        dest_mib = open(filename, 'w')

    if begun:
        dest_mib.write(line)

dest_mib.close()
source_mib.close()
