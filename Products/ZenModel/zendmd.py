import Globals
import transaction
from Products.ZenUtils.ZCmdBase import ZCmdBase

class zendmd(ZCmdBase): pass
    
zendmd = zendmd()
dmd = zendmd.dmd
find = dmd.Devices.findDevice
devices = dmd.Devices
sync = dmd._p_jar.sync
commit = transaction.commit
abort = transaction.abort

def rebuildidx():
    for dev in dmd.Devices.getSubDevicesGen():
        dev.unindex_object()
        dev.index_object()
    commit()
