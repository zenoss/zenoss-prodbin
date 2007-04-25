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
from socket import *

s = socket(AF_INET, SOCK_DGRAM)
import time
now = time.strftime('%b %d %T %Z %Y')
m = '''<165>%s localhost myproc[10]: %%%% It's time to make the do-nuts.  %%%%  Ingredients: Mix=OK, Jelly=OK # Devices: Mixer=OK, Jelly_Injector=OK, Frier=OK # Transport: Conveyer1=OK, Conveyer2=OK # %%%%''' % now
m = '''<165>%s xlocalhost myproc[10]: %%%% It's time to make the do-nuts.  %%%%  Ingredients: Mix=OK, Jelly=OK # Devices: Mixer=OK, Jelly_Injector=OK, Frier=OK # Transport: Conveyer1=OK, Conveyer2=OK # %%%%''' % now
s.sendto(m, ('localhost', 514) )




