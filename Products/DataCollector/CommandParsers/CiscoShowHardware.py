#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__ = """CiscoShowHardware

Parses the show hardware command and returns CPU type and total memeory

$Id: CiscoShowHardware.py,v 1.3 2003/12/16 21:50:40 edahl Exp $"""

__version__ = '$Revision: 1.3 $'[11:-2]

import re

from Products.ZenModel.IpAddress import findIpAddress

from CommandParser import CommandParser

class CiscoShowHardware(CommandParser):
    
    command = 'show hardware'

    def condition(self, device, log):
        return device.getManufacturerName() == "Cisco"


    def parse(self, device, results, log):
        cpumem = re.compile("\((.+)\) processor .* ([\d\/K]+) bytes").search
        om = self.newObjectMap()
        for line in results.split('\n'):
            m = cpumem(line) 
            if m:
                om['cpuType'] = m.group(1)
                mems = m.group(2)
                if mems.find('/') > -1:
                    mems = mems.split('/')
                else:
                    mems = (mems,)
                tmem = 0.0
                for mem in mems:
                    if mem[-1] == 'K': mem = float(mem[:-1])
                    tmem += mem
                tmem /= 1024.0
                om['totalMemory'] = round(tmem)
        return om


    def description(self):
        return "Get the CPUType and Total Memory from the show hardware command"
