import Zope
app = Zope.app()
#linux = app.zport.dmd.Devices.Servers.Linux._getOb('edahl04.confmon.loc')
win = app.zport.dmd.Devices.Servers.Windows._getOb('dhcp160.confmon.loc')
router = app.zport.dmd.Devices.NetworkDevices.Router._getOb(
