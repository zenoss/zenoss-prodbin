from Uname_A import Uname_A
from Unix_df_k import Unix_df_k
from CiscoDhcpHelperAddress import CiscoDhcpHelperAddress
from CiscoShowHardware import CiscoShowHardware

def initCommandParsers(dataCollector):
    dataCollector.addCommandParser(Uname_A)
    dataCollector.addCommandParser(Unix_df_k)
    dataCollector.addCommandParser(CiscoDhcpHelperAddress)
    dataCollector.addCommandParser(CiscoShowHardware)
