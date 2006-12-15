import Globals

from Products.ZenUtils.Utils import convToUnits

def args(g):
    if g.get('dmd', None) and g.get('args', None):
        return g['dmd'], g['args']
    
    import sys
    result = {}
    for a in sys.argv[1:]:
        k, v = a.split('=', 1)
        if k:
            if result.has_key(k):
                if type(result[k]) != type(()):
                    result[k] = tuple(result[k], v)
                else:
                    result[k] = result[k] + (v, )
            else:
                result[k] = v
    from Products.ZenUtils.ZCmdBase import ZCmdBase
    return ZCmdBase(noopts=True).dmd, result

def pprint(report, g):
    if g.get('REQUEST', None):
        return
    import pprint
    pprint.pprint(report)

UNAVAILABLE = 'N/A'

def percent(partial, total):
    if partial is None or total is None:
        return None
    if not total:
        return None
    return partial * 100 / total


def percentString(n, decimals=0):
    if n is None:
        return UNAVAILABLE
    return '%*.*f' % (2, decimals, n)


from AccessControl import ClassSecurityInfo


class Record:
    __allow_access_to_unprotected_subobjects__ = 1

    def __init__(self, **kw):
        self.values = kw.copy()


    def __str__(self):
        return str(self.values)


    def __repr__(self):
        return repr(self.values)


    def __getitem__(self, name):
        return self.values[name]

    def __getattr__(self, name):
        return self.values.get(name)

    def percent(self, partial, total):
        return percent(partial, total, decimals)

    def percentString(self, n, decimals=0):
        return percentString(n, decimals)

    def humanBytes(self, value, scale=1):
        if value is None:
            return UNAVAILABLE
        return convToUnits(value * scale)

    def humanBits(self, value, scale=1):
        if value is None:
            return UNAVAILABLE
        return convToUnits(value * scale, 1000)

    def fmt(self, fmt, value):
        if value is None:
            return UNAVAILABLE
        return fmt % value


