#################################################################
#
#   Copyright (c) 2003 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""RRDLoader

load rrd objects into the dmd
File format is as follows:

RRDTargetType|name|datasources,|views,|
RRDView|name|datasources,|height|width|units|linewidth|log|colors,|
RRDDataSource|name|rpn|limit|linetype|color|
RRDThreshold|name|datasources,|minval|maxval|minfunc|maxfunc|

$Id: RRDLoader.py,v 1.2 2004/02/18 16:19:18 edahl Exp $"""

__version__ = "$Revision: 1.2 $"[11:-2]

import sys

import Globals

from OFS.Folder import manage_addFolder

from Products.ZenUtils.Utils import getObjByPath
from Products.ZenUtils.Utils import lookupClass

from Products.ZenUtils.BasicLoader import BasicLoader

from Products.ZenRRD.RRDTargetType import RRDTargetType
from Products.ZenRRD.RRDView import RRDView
from Products.ZenRRD.RRDDataSource import RRDDataSource
from Products.ZenRRD.RRDThreshold import RRDThreshold


class RRDLoader(BasicLoader):

    def __init__(self):
        BasicLoader.__init__(self)
        self.configroot = getObjByPath(self.dmd, self.options.configroot)
        if not self.configroot:
            path = '/'.join(self.options.configroot.split('/')[:-1])
            context = getObjByPath(self.dmd, path)
            if not context:
                print "ERROR: can't find configroot %s" % \
                            self.options.configroot
                sys.exit(1)
            else:
                manage_addFolder(context, 'rrdconfig')
                self.configroot = context._getOb('rrdconfig')
                get_transaction().commit()

        
    def loaderBody(self, line):
        classname, id = line.split('|')[:2]
        self.log.info('loading %s type = %s' % (id, classname))
        constructor = lookupClass('Products.ZenRRD.'+classname)
        if constructor:
            obj = constructor(id)
        else:
            raise "NoConstructor", "No Constructor for %s" % classname 
        obj.textload(line.split('|')[2:])
        self.configroot._setObject(obj.id, obj)



    def buildOptions(self):
        BasicLoader.buildOptions(self)
        self.parser.add_option('-r', '--configroot',
                    dest='configroot',
                    default='/Devices/rrdconfig',
                    help='load location path (ie /Devices/rrdconfig)')


if __name__ == '__main__':
    rrdloader = RRDLoader()
    rrdloader.loadDatabase()
