from Uname_A import Uname_A
from CiscoDhcpHelperAddress import CiscoDhcpHelperAddress
from CiscoShowHardware import CiscoShowHardware

def initCommandParsers(dataCollector):
    dataCollector.addCommandParser(Uname_A)
    dataCollector.addCommandParser(CiscoDhcpHelperAddress)
    dataCollector.addCommandParser(CiscoShowHardware)
