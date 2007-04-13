from twisted.web import xmlrpc

class XmlRpcService(xmlrpc.XMLRPC):

    def __init__(self, dmd):
        xmlrpc.XMLRPC.__init__(self)
        self.dmd = dmd
        self.zem = dmd.ZenEventManager

    def xmlrpc_sendEvent(self, data):
        'XMLRPC requests are processed asynchronously in a thread'
        return self.zem.sendEvent(data)

    def xmlrpc_sendEvents(self, data):
        return self.zem.sendEvents(data)

    def xmlrpc_getDevicePingIssues(self, *unused):
        return self.zem.getDevicePingIssues()
    
    def xmlrpc_getWmiConnIssues(self, *args):
        return self.zem.getWmiConnIssues(*args)

    def xmlrpc_getDeviceWinInfo(self, *args):
        return self.dmd.Device.Servers.Windows.getDeviceWinInfo(*args)

    def xmlrpc_applyDataMap(self, devName, datamap, 
                            relname="", compname="", modname=""):
        """Apply a datamap passed as a list of dicts through XML-RPC.
        """
        dev = self.dmd.findDevice(devName)
        adm = ApplyDataMap()
        adm.applyDataMap(dev, datamap, relname=relname,
                         compname=compname, modname=modname)
