###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from zenagios import zenagios

class zencacti(zenagios):
    dataSourceType = 'CACTI'
    
    def parseResults(self, cmd):
        output = cmd.result.output.replace(':', '=')
        if output.find('=') < 0:
            pointName = cmd.points.keys()[0]
            output = '|%s=%s' % (pointName,output)
        else:
            output = '|' + output
        cmd.result.output = output
        print output
        return zenagios.parseResults(self, cmd)
    

if __name__ == '__main__':
    z = zencacti()
    z.main()

