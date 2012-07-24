##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from CollectionStatistic import CollectionStatistic
from PingTask import PingTask
from PingCollectionPreferences import PingCollectionPreferences
import nmap
import ping
import collections as _collections
 
# define a namedtuple to store hop results
TraceHop = _collections.namedtuple('TraceHop', 'ip rtt')
