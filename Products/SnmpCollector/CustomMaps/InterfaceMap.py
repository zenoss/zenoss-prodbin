#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""InterfaceMap

InterfaceMap maps the interface and ip tables to interface objects

$Id: InterfaceMap.py,v 1.24 2003/10/30 18:42:19 edahl Exp $"""

__version__ = '$Revision: 1.24 $'[11:-2]

import re

from Products.ZenUtils.IpUtil import maskToBits
from Products.ZenUtils.Utils import cleanstring

from CustomRelMap import CustomRelMap

class InterfaceMap(CustomRelMap):

    remoteClass = "Products.ZenModel.IpInterface"
    relationshipName = "interfaces"
    componentName = "os"

    intTableOid = '.1.3.6.1.2.1.2.2.1'
    intMap = {'.1': 'ifindex',
             '.2': 'id',
             '.3': 'type',
             '.4': 'mtu',
             '.5': 'speed',
             '.6': 'macaddress',
             '.7': 'adminStatus',
             '.8': 'operStatus'}

    ipTableOid = '.1.3.6.1.2.1.4.20.1'
    ipMap = {'.1': 'ipAddress',
             '.2': 'ifindex',
             '.3': 'netmask'}

    #dontCollectInterfaceTypes = (1, 18, 76, 77, 81, 134)
    
   
    ionSpeed = re.compile(r'ION:(?P<speed>\d+)MB')

    srpInt = re.compile(r'^SRP\d+.\d+$')
    srpSideInt = re.compile(r'^(?P<baseint>SRP.+)-side .-SONET')
    srpSideA = re.compile(r'A')

    ciscoIfDescrTable = {}
    ciscoSRPInts = {}


    def condition(self, device, snmpsess, log):
        """does device meet the proper conditions for this collector to run"""
        return 1


    def collect(self, device, snmpsess, log):
        """collect snmp information from this device"""
        self.log = log
        log.info('Collecting interfaces for device %s' % device.id)
        bulk=0
        if device.snmpOid.find('.1.3.6.1.4.1.9') > -1:
            bulk=1
            self.getCiscoDescr(snmpsess)
        inttable = snmpsess.collectSnmpTableMap(self.intTableOid, 
                                                self.intMap, bulk)
        iptable = snmpsess.collectSnmpTableMap(self.ipTableOid, 
                                               self.ipMap, bulk)
        datamaps = []
        for iprow in iptable.values():
            strindex = str(iprow['ifindex'])
            if not inttable.has_key(strindex):
                if int(iprow['ifindex']) >= len(inttable): #hack for bad 
                    strindex = str(len(inttable))          #ifindex on wrt54g
                else: 
                    continue                                 
            nrow = inttable[strindex]
            if not nrow.has_key('_processed'):
                nrow = self.processInt(device, snmpsess, nrow)
            if not nrow: 
                continue
            if not nrow.has_key('setIpAddresses'):
                nrow['setIpAddresses'] = []
            ip = iprow['ipAddress'] + "/" + str(maskToBits(iprow['netmask']))
            nrow['setIpAddresses'].append(ip)
            nrow['ifindex'] = iprow['ifindex'] #FIXME ifindex is not set!
            inttable[strindex] = nrow

        for index,iface in inttable.items():        
            if iface.has_key('_processed'): 
                del inttable[index]
                datamaps.append(iface)

        for iface in inttable.values():
            #nrow = snmpsess.snmpRowMap(iface, self.intMap)
            nrow = self.processInt(device, snmpsess, iface)
            if nrow: 
                datamaps.append(nrow)
        return datamaps


    def processInt(self, device, snmpsess, nrow):
        if nrow.has_key('_processed'): return nrow
        strindex = str(nrow['ifindex'])
        nrow['id'] = cleanstring(nrow['id']) #take off \x00 at end of string
        nrow['name'] = nrow['id']
        nrow['id'] = self.prepId.sub('_', nrow['id'])
        if nrow['id'].startswith('_'): nrow['id'] = nrow['id'][1:]
        dontCollectIntNames = getattr(device, 'zInterfaceMapIgnoreNames', None)
        if dontCollectIntNames and re.search(dontCollectIntNames, nrow['id']):
            return None
        try:
            nrow['type'] = self.ifTypes[str(nrow['type'])]
        except: pass
        dontCollectIntTypes = getattr(device, 'zInterfaceMapIgnoreTypes', None)
        if (dontCollectIntTypes and 
            re.search(dontCollectIntTypes, nrow['type'])):
            return None
        
        if nrow.has_key('macaddress'):
            nrow['macaddress'] = snmpsess.asmac(nrow['macaddress'])

        if self.ciscoIfDescrTable and self.ciscoIfDescrTable.has_key(strindex):
            nrow['description'] = self.ciscoIfDescrTable[strindex]
            #get the speed from description field that looks like this
            #ION:622MB Downstream Link to DSTSWR2.RH.FRPTNY - Port GE3/
            match = self.ionSpeed.search(nrow['description'])
            if match: nrow['speed'] = int(match.group('speed')) * 1000000

        nrow = self.processSRP(nrow)

        nrow['_processed'] = 1
        return nrow
   

    def processSRP(self, nrow):
        """set the interface index for the two sides of an srp interface"""
        name = nrow['name']
        if self.srpInt.search(name):
            self.ciscoSRPInts[name] = nrow['ifindex'] 
        baseSrp = self.srpSideInt.search(name)
        if baseSrp:
            baseSrp = baseSrp.group('baseint')
            if not self.ciscoSRPInts.has_key(baseSrp):
                self.log.warn(
                    "failed to find SRP Parent for interface %s" % name)
                return nrow
            ifindex = str(self.ciscoSRPInts[baseSrp])
            if self.srpSideA.search(name):
                ifindex += ".1.1"
            else:
                ifindex += ".2.1"
            nrow['ifindex'] = "\"'"+ifindex+"'\""
        return nrow


    def getCiscoDescr(self, snmpsess):
        #try:
        ciscoIfDescrOid = '.1.3.6.1.4.1.9.2.2.1.1.28'
        data = snmpsess.getTable(ciscoIfDescrOid, bulk=1)
        for key,value in data.items():
            index = key.split('.')[-1]
            data[index] = value
            del[key]
        self.ciscoIfDescrTable = data
        #except: pass

    ifTypes = {'1': 'Other',
     '2': 'regular1822',
     '3': 'hdh1822',
     '4': 'ddnX25',
     '5': 'rfc877x25',
     '6': 'ethernetCsmacd',
     '7': 'iso88023Csmacd',
     '8': 'iso88024TokenBus',
     '9': 'iso88025TokenRing',
     '10': 'iso88026Man',
     '11': 'starLan',
     '12': 'proteon10Mbit',
     '13': 'proteon80Mbit',
     '14': 'hyperchannel',
     '15': 'fddi',
     '16': 'lapb',
     '17': 'sdlc',
     '18': 'ds1',
     '19': 'e1',
     '20': 'basicISDN',
     '21': 'primaryISDN',
     '22': 'propPointToPointSerial',
     '23': 'ppp',
     '24': 'softwareLoopback',
     '25': 'eon',
     '26': 'ethernet-3Mbit',
     '27': 'nsip',
     '28': 'slip',
     '29': 'ultra',
     '30': 'ds3',
     '31': 'sip',
     '32': 'frame-relay',
     '33': 'rs232',
     '34': 'para',
     '35': 'arcnet',
     '36': 'arcnetPlus',
     '37': 'atm',
     '38': 'miox25',
     '39': 'sonet',
     '40': 'x25ple',
     '41': 'iso88022llc',
     '42': 'localTalk',
     '43': 'smdsDxi',
     '44': 'frameRelayService',
     '45': 'v35',
     '46': 'hssi',
     '47': 'hippi',
     '48': 'modem',
     '49': 'aal5',
     '50': 'sonetPath',
     '51': 'sonetVT',
     '52': 'smdsIcip',
     '53': 'propVirtual',
     '54': 'propMultiplexor',
     '55': '100BaseVG',
     '56': 'Fibre Channel',
     '57': 'HIPPI Interface',
     '58': 'Obsolete for FrameRelay',
     '59': 'ATM Emulation of 802.3 LAN',
     '60': 'ATM Emulation of 802.5 LAN',
     '61': 'ATM Emulation of a Circuit',
     '62': 'FastEthernet (100BaseT)',
     '63': 'ISDN & X.25',
     '64': 'CCITT V.11/X.21',
     '65': 'CCITT V.36',
     '66': 'CCITT G703 at 64Kbps',
     '67': 'Obsolete G702 see DS1-MIB',
     '68': 'SNA QLLC',
     '69': 'Full Duplex Fast Ethernet (100BaseFX)',
     '70': 'Channel',
     '71': 'Radio Spread Spectrum (802.11)',
     '72': 'IBM System 360/370 OEMI Channel',
     '73': 'IBM Enterprise Systems Connection',
     '74': 'Data Link Switching',
     '75': 'ISDN S/T Interface',
     '76': 'ISDN U Interface',
     '77': 'Link Access Protocol D (LAPD)',
     '78': 'IP Switching Opjects',
     '79': 'Remote Source Route Bridging',
     '80': 'ATM Logical Port',
     '81': 'AT&T DS0 Point (64 Kbps)',
     '82': 'AT&T Group of DS0 on a single DS1',
     '83': 'BiSync Protocol (BSC)',
     '84': 'Asynchronous Protocol',
     '85': 'Combat Net Radio',
     '86': 'ISO 802.5r DTR',
     '87': 'Ext Pos Loc Report Sys',
     '88': 'Apple Talk Remote Access Protocol',
     '89': 'Proprietary Connectionless Protocol',
     '90': 'CCITT-ITU X.29 PAD Protocol',
     '91': 'CCITT-ITU X.3 PAD Facility',
     '92': 'MultiProtocol Connection over Frame/Relay',
     '93': 'CCITT-ITU X213',
     '94': 'Asymetric Digitial Subscriber Loop (ADSL)',
     '95': 'Rate-Adapt Digital Subscriber Loop (RDSL)',
     '96': 'Symetric Digitial Subscriber Loop (SDSL)',
     '97': 'Very High Speed Digitial Subscriber Loop (HDSL)',
     '98': 'ISO 802.5 CRFP',
     '99': 'Myricom Myrinet',
     '100': 'Voice recEive and transMit (voiceEM)',
     '101': 'Voice Foreign eXchange Office (voiceFXO)',
     '102': 'Voice Foreign eXchange Station (voiceFXS)',
     '103': 'Voice Encapulation',
     '104': 'Voice Over IP Encapulation',
     '105': 'ATM DXI',
     '106': 'ATM FUNI',
     '107': 'ATM IMA',
     '108': 'PPP Multilink Bundle',
     '109': 'IBM IP over CDLC',
     '110': 'IBM Common Link Access to Workstation',
     '111': 'IBM Stack to Stack',
     '112': 'IBM Virtual IP Address (VIPA)',
     '113': 'IBM Multi-Protocol Channel Support',
     '114': 'IBM IP over ATM',
     '115': 'ISO 802.5j Fiber Token Ring',
     '116': 'IBM Twinaxial Data Link Control (TDLC)',
     '117': 'Gigabit Ethernet',
     '118': 'Higher Data Link Control (HDLC)',
     '119': 'Link Access Protocol F (LAPF)',
     '120': 'CCITT V.37',
     '121': 'CCITT X.25 Multi-Link Protocol',
     '122': 'CCITT X.25 Hunt Group',
     '123': 'Transp HDLC',
     '124': 'Interleave Channel',
     '125': 'Fast Channel',
     '126': 'IP (for APPN HPR in IP Networks)',
     '127': 'CATV MAC Layer',
     '128': 'CATV Downstream Interface',
     '129': 'CATV Upstream Interface',
     '130': 'Avalon Parallel Processor',
     '131': 'Encapsulation Interface',
     '132': 'Coffee Pot',
     '133': 'Circuit Emulation Service',
     '134': 'ATM Sub Interface',
     '135': 'Layer 2 Virtual LAN using 802.1Q',
     '136': 'Layer 3 Virtual LAN using IP',
     '137': 'Layer 3 Virtual LAN using IPX',
     '138': 'IP Over Power Lines',
     '139': 'Multi-Media Mail over IP',
     '140': 'Dynamic synchronous Transfer Mode (DTM)',
     '141': 'Data Communications Network',
     '142': 'IP Forwarding Interface',
     '143': 'Multi-rate Symmetric DSL',
     '144': 'IEEE1394 High Performance Serial Bus',
     '145': 'HIPPI-6400',
     '146': 'DVB-RCC MAC Layer',
     '147': 'DVB-RCC Downstream Channel',
     '148': 'DVB-RCC Upstream Channel',
     '149': 'ATM Virtual Interface',
     '150': 'MPLS Tunnel Virtual Interface',
     '151': 'Spatial Reuse Protocol',
     '152': 'Voice Over ATM',
     '153': 'Voice Over Frame Relay',
     '154': 'Digital Subscriber Loop over ISDN',
     '155': 'Avici Composite Link Interface',
     '156': 'SS7 Signaling Link',
     '157': 'Prop. P2P wireless interface',
     '158': 'Frame Forward Interface',
     '159': 'Multiprotocol over ATM AAL5',
     '160': 'USB Interface',
     '161': 'IEEE 802.3ad Link Aggregate',
     '162': 'BGP Policy Accounting',
     '163': 'FRF .16 Multilink Frame Relay',
     '164': 'H323 Gatekeeper',
     '165': 'H323 Voice and Video Proxy',
     '166': 'MPLS',
     '167': 'Multi-frequency signaling link',
     '168': 'High Bit-Rate DSL - 2nd generation',
     '169': 'Multirate HDSL2',
     '170': 'Facility Data Link 4Kbps on a DS1',
     '171': 'Packet over SONET/SDH Interface',
     '172': 'DVB-ASI Input',
     '173': 'DVB-ASI Output',
     '174': 'Power Line Communtications',
     '175': 'Non Facility Associated Signaling',
     '176': 'TR008',
     '177': 'Remote Digital Terminal',
     '178': 'Integrated Digital Terminal',
     '179': 'ISUP',
     '180': 'prop/Maclayer',
     '181': 'prop/Downstream',
     '182': 'prop/Upstream',
     '183': 'HIPERLAN Type 2 Radio Interface',
     '184': 'PropBroadbandWirelessAccesspt2multipt',
     '185': 'SONET Overhead Channel',
     '186': 'Digital Wrapper',
     '187': 'ATM adaptation layer 2',
     '188': 'MAC layer over radio links',
     '189': 'ATM over radio links',
     '190': 'Inter Machine Trunks',
     '191': 'Multiple Virtual Lines DSL',
     '192': 'Long Rach DSL',
     '193': 'Frame Relay DLCI End Point',
     '194': 'ATM VCI End Point',
     '195': 'Optical Channel',
     '196': 'Optical Transport',
     '197': 'Proprietary ATM',
     }
