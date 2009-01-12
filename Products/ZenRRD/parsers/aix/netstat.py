from Products.ZenRRD.parsers.darwin.netstat import netstat as darwin_netstat

class netstat(darwin_netstat):

    componentScanner = '^(?P<component>[^ ]*) '
    scanners = [
        r' +(?P<mtu>\d+)'
        r' +link.{34,34}'
        r' +(?P<ifInPackets>\d+)'
        r' +(?P<ifInErrors>\d+) '
        r' +(?P<ifOutPackets>\d+) '
        r' +(?P<ifOutErrors>\d+) '
        r' +(?P<lastColumn>\d*)-?$',
        ]

