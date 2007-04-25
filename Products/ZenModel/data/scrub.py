###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import re

subs = (
("\S+\@\S+\.(com|org|net)", "email@email.com"),
("\d+\.\d+\.\d+\.\d+", "1.1.1.1"),
)

lines = open("events.xml").readlines()
out = open("events.xml.new", "w")
for line in lines:
    for regex, sub in subs:
        line = re.sub(regex, sub, line) 


