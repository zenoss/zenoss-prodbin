import Zope
app = Zope.app()
c = app.dmd.Devices.myClassifier
ce = c.getClassifierEntry({'devicename':'dhcp160','community':'public'})
ce = c.getClassifierEntry({'devicename':'printer','community':'public'})
if ce:
    print "dc path =", ce.getDeviceClassPath
else:
    print 'Failed'
