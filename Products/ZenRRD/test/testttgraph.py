import Zope
app=Zope.app()
tt = app.zport.dmd.Devices.rrdconfig._getOb('RRDTargetType-SRPInterface')
print tt.graphView('SRPAllOctets', tt, 'lkj', 213423)
