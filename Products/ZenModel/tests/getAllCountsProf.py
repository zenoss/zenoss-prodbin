import Zope2
app = Zope2.app()
devs = app.zport.dmd.Devices.getOrganizer("/Server")

import hotshot, hotshot.stats

def runtest():
    prof = hotshot.Profile("allcounts.prof")
    prof.runcall(devs.getAllCounts)
    prof.close()

def showresults():
    stats = hotshot.stats.load("allcounts.prof")
    stats.strip_dirs()
    stats.sort_stats('time', 'calls')
    stats.print_stats(20)

#runtest()
#showresults()
