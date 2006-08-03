# Copyright (C) 2003 by Dr. Dieter Maurer, Eichendorffstr. 23, D-66386 St. Ingbert, Germany
# see "LICENSE.txt" for details
#       $Id: Utils.py,v 1.1 2004/05/22 17:40:18 dieter Exp $
'''Utilities.'''

from sys import maxint
from DateTime import DateTime


##############################################################################
## order support
class _OrderReverse:
  '''auxiliary class to provide order reversal.'''

  def __init__(self, value):
    self._OrderReverse_value = value

  getValue__roles__ = None # public
  def getValue(self): return self._OrderReverse_value

  def __cmp__(self,other):
    return - cmp(self._OrderReverse_value, other._OrderReverse_value)

##  def __getattr__(self, attr):
##    return getattr(_OrderReverse_value, attr)

_mdict = globals(); _cldict = _OrderReverse.__dict__

for _f,_op in [spec.split(':') for spec in
               'lt:> le:>= eq:== ne:!= gt:< ge:<='.split()]:
    exec('def %s(self, other): return self._OrderReverse_value %s other._OrderReverse_value\n\n' %
         (_f, _op),
         _mdict,
         _cldict,
         )

def reverseOrder(value):
  if isinstance(value, _OrderReverse): return value._OrderReverse_value
  return _OrderReverse(value)


##############################################################################
## Lazy
## this is private for the moment as otherwise, we would need to
## respect security aspects
class _LazyMap:
  '''an object applying a function lazyly.'''
  def __init__(self, f, seq):
    self._f = f
    self._seq = seq

  def __getitem__(self, i): return self._f(self._seq[i])



##############################################################################
## DateTime conversions

def convertToDateTime(value):
  '''convert *value* to a 'DateTime' object.'''
  if isinstance(value, DateTime): return value
  if isinstance(value, tuple): return DateTime(*value)
  return DateTime(value)

def convertToDateTimeInteger(value, exc=0):
  '''convert *value* into a DateTime integer (representing secs since
  epoch).

  *exc* controls whether an exception should be raised when the
  value cannot be represented in the integer range. If *exc* is
  false, values are truncated, if necessary.
  '''
  if isinstance(value, int): return value
  value = round(convertToDateTime(value)._t) # seconds since epoch
  ma = maxint; mi = -ma - 1
  if exc and value < mi or value > ma:
    raise TypeError('not in integer range: %s' % value)
  if value < mi: value = mi
  elif value > ma: value = ma
  return int(value)

def convertToDateInteger(value, round_dir=-1):
  '''convert *value* into a Date integer (400*y + 31*(m-1) + d-1).

  *round_dir* controls rounding: '0' means 'round', '1' means 'ceil'
  and '-1' 'floor')
  '''
  if isinstance(value, int): return value
  adjust = (0, 0.5, (0.999999))[round_dir]
  dt = convertToDateTime(value)
  if adjust: dt += adjust
  y,m,d = dt._year, dt._month, dt._day
  return 400*y +(m-1)*31 +d-1

