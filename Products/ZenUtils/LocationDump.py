#################################################################
#
#   Copyright (c) 2003 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""CmdBase

Dump location data from pre 0.11.7 database to text to be reloaded
in new location format

$Id: LocationDump.py,v 1.4 2003/11/21 21:18:11 edahl Exp $"""

__version__ = "$Revision: 1.4 $"[11:-2]


from ZCmdBase import ZCmdBase

class LocationDump(ZCmdBase):
    
    def dump(self):
        outfile = open(self.options.outfile, "w")
        if not hasattr(self.dataroot, "getSubDevices"):
            raise "DataRootError", "dataroot doesn't have getSubDevices"
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
        ZCmdBase.buildOptions(self)
        self.parser.add_option('-o', '--outfile',
                    dest='outfile',
                    default="locdump.out",
                    help='output file')
        

if __name__ == "__main__":
    ld = LocationDump()
    ld.dump()
