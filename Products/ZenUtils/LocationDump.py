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

__doc__="""LocationDump

Dump location data from pre 0.11.7 database to text to be reloaded
in new location format
"""

from ZCmdBase import ZCmdBase

class LocationDump(ZCmdBase):
    """
    Dump location data
    """
    
    def dump(self):
        """
        Dump location data to the specified output file.
        """
        outfile = open(self.options.outfile, "w")
        if not hasattr(self.dataroot, "getSubDevices"):
            raise RuntimeError, "dataroot doesn't have getSubDevices"
        devs = self.dataroot.getSubDevices()
        for dev in devs:
            dcname = dev.getDataCenterName()
            rname = dev.getRackName()
            if rname: 
                locpath = dcname.split("-")
                locpath.append(rname)
            else:
                locpath = ("NoLocation",)
            line = "%s|%s\n" % (dev.getId(), "/" + "/".join(locpath))
            outfile.write(line)
        outfile.close()


    def buildOptions(self):
        """
        Command-line options for LocationDump
        """
        ZCmdBase.buildOptions(self)
        self.parser.add_option('-o', '--outfile',
                    dest='outfile',
                    default="locdump.out",
                    help='output file')
        

if __name__ == "__main__":
    ld = LocationDump()
    ld.dump()
