import Globals

from Products.ZenUtils.Utils import convToUnits

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


