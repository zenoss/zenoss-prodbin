import socket
import Globals
import transaction
from Products.ZenUtils.ZCmdBase import ZCmdBase

class zendmd(ZCmdBase): pass
    
zendmd = zendmd()
dmd = zendmd.dmd
app = dmd.getPhysicalRoot()
zport = app.zport
find = dmd.Devices.findDevice
devices = dmd.Devices
sync = dmd._p_jar.sync
commit = transaction.commit
abort = transaction.abort
me = find(socket.getfqdn())

def zhelp():
    cmds = filter(lambda x: not x.startswith("_"), globals())
    cmds.sort()
    for cmd in cmds[2:]: print cmd
        

def reindex():
    sync()
    dmd.Devices.reIndex()
    dmd.Events.reIndex()
    dmd.Manufacturers.reIndex()
    dmd.Networks.reIndex()
    commit()

print "Welcome to zenoss dmd command shell!"
print "use zhelp() to list commnads"
