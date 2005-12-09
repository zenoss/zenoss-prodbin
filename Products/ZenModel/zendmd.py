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

def zhelp():
    cmds = filter(lambda x: not x.startswith("_"), globals())
    cmds.sort()
    for cmd in cmds[2:]: print cmd
        

def reindex():
    sync()
    dmd.Devices.reIndexDevices(True)
    commit()

print "Welcome to zenmon dmd command shell!"
print "use zhelp() to list commnads"
