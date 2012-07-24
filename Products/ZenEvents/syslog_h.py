##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


# constants from syslog.h
LOG_EMERGENCY   = 0
LOG_ALERT       = 1
LOG_CRITICAL    = 2
LOG_ERRROR      = 3
LOG_WARNING     = 4
LOG_NOTICE      = 5
LOG_INFO        = 6
LOG_DEBUG       = 7

LOG_PRIMASK     = 0x07

def LOG_PRI(p): return p & LOG_PRIMASK
def LOG_MAKEPRI(fac, pri): return fac << 3 | pri

LOG_KERN        = 0 << 3
LOG_USER        = 1 << 3
LOG_MAIL        = 2 << 3
LOG_DAEMON      = 3 << 3
LOG_AUTH        = 4 << 3
LOG_SYSLOG      = 5 << 3
LOG_LPR         = 6 << 3
LOG_NEWS        = 7 << 3
LOG_UUCP        = 8 << 3
LOG_CRON        = 9 << 3
LOG_AUTHPRIV    = 10 << 3
LOG_FTP         = 11 << 3
LOG_LOCAL0      = 16 << 3
LOG_LOCAL1      = 17 << 3
LOG_LOCAL2      = 18 << 3
LOG_LOCAL3      = 19 << 3
LOG_LOCAL4      = 20 << 3
LOG_LOCAL5      = 21 << 3
LOG_LOCAL6      = 22 << 3
LOG_LOCAL7      = 23 << 3

LOG_NFACILITIES = 24
LOG_FACMASK     = 0x03F8
def LOG_FAC(p): return (p & LOG_FACMASK) >> 3

def LOG_MASK(pri): return 1 << pri
def LOG_UPTO(pri): return (1 << pri + 1) - 1
# end syslog.h

def LOG_UNPACK(p): return (LOG_FAC(p), LOG_PRI(p))

fac_values = {}     # mapping of facility constants to their values
fac_names = {}      # mapping of values to names
pri_values = {}
pri_names = {}
for i, j in globals().items():
    if i[:4] == 'LOG_' and isinstance(j, int):
        if j > LOG_PRIMASK or i == 'LOG_KERN':
            n, v = fac_names, fac_values
        else:
            n, v = pri_names, pri_values
        i = i[4:].lower()
        v[i] = j
        n[j] = i
del i, j, n, v
