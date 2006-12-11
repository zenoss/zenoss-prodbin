__doc__="""BatchDeviceLoader.py

BatchDeviceLoader.py loads a list of devices read from a file.
The file can be formatted like this:

device0
/Path/To/Device
device1
device2
/Path/To/Other
    device3
    device4"""

import Globals
import transaction
from os.path import isfile
import logging
import re
log = logging.getLogger("zen.BatchDeviceLoader")

from Products.ZenUtils.ZCmdBase import ZCmdBase


class BatchDeviceLoader:

    def __init__(self):
        self.dmd = ZCmdBase().dmd
        self.loader = self.dmd.DeviceLoader
        self.device_list = []

    def readFile(self, filename=""):
        if not isfile(filename):
            log.critical("File %s does not exist." % filename)
        else:
            f = open(filename, 'r')
            self.device_list = self.parseDevices(f.read())
            f.close()
            log.info("Loading devices from %s..." % filename)

    def loadDevices(self):
        if not self.device_list:
            log.error("No devices to load!")
        else:
            for device in self.device_list:
                if device['deviceName']:
                    log.info("Attempting to load %s" % device['deviceName'])
                    self.loader.loadDevice(**device)

    def parseDevices(self, rawDevices):
        _slash = re.compile(r'\s*/', re.M)
        _sp = re.compile(r'\s+', re.M)
        _r = re.compile(r'\s+/', re.M)
        if not _slash.match(rawDevices): rawDevices = "/Discovered\n" + rawDevices
        sections = [re.split(_sp, x) for x in re.split(_r, rawDevices)]
        print sections, self.device_list
        finalList = []
        for s in sections:
            path, devs = s[0], s[1:]
            if not path.startswith('/'): path = '/' + path
            finalList += [{'deviceName':x,'devicePath':path} for x in devs]
        return finalList

if __name__=='__main__':
    import sys
    filename = sys.argv[1] or ''
    b = BatchDeviceLoader()
    b.readFile(filename)
    b.loadDevices()
