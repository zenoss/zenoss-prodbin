# Copyright (C) 2003 by Dr. Dieter Maurer, Eichendorffstr. 23, D-66386 St. Ingbert, Germany
# see "LICENSE.txt" for details
#       $Id: ValueProvider.py,v 1.5 2004/07/30 13:38:02 dieter Exp $
'''ValueProvider.

A 'ValueProvider' evaluates an object and returns a value.
A 'None' value is interpreted as if the object does not have
a value.

A 'ValueProvider' can ignore more values than 'None'.
It can specify a normalization for values which have not been ignored.

A 'ValueProvider' can specify how exceptions during evaluation
and postprocessing should be handled. They can be ignored
(this means, the object does not have a value) or propagated.

'ValueProviders' are 'SimpleItems' and provide comfiguration
via Properties, i.e. they are 'PropertyManagers'.
'''

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from ComputedAttribute import ComputedAttribute
from Acquisition import Acquired

from OFS.SimpleItem import SimpleItem
from OFS.PropertyManager import PropertyManager
from DocumentTemplate.DT_Util import safe_callable
from ZODB.POSException import ConflictError

from zope.tales.tales import CompilerError

from Evaluation import EvalAndCall, Ignore, Normalize


class ValueProvider(SimpleItem,PropertyManager,Ignore,Normalize):
  '''configuration for object evaluation.'''

  manage_options= (
    PropertyManager.manage_options
    + SimpleItem.manage_options
    )

  _properties= (
  (
    { 'id' : 'IgnoreExceptions', 'type' : 'boolean', 'mode' : 'w',},
    )
    + Ignore._properties
    + Normalize._properties
    )
  IgnoreExceptions= 1

  security= ClassSecurityInfo()
  security.declarePrivate('evaluate')


  def evaluate(self,object):
    '''evaluate *object* to a value.

    'None' means, the object does not have a value.
    '''
    __traceback_info__ = self.id
    try:
      value= self._evaluate(object)
      value= self._ignore(value,object)
      value= self._normalize(value,object)
    except (CompilerError, ConflictError): raise
    except:
      if self.IgnoreExceptions: return
      raise
    return value


  def __str__(self):
    return '; '.join(['%s : %s' % pi for pi in self.propertyItems()])

  title= ComputedAttribute(__str__)


  # abstract methods
  def _evaluate(self,object):
    raise NotImplementedError("'_ValueProvider._evaluate' is abstract")

InitializeClass(ValueProvider)


class AttributeLookup(ValueProvider):
  '''Configures attribute/method lookup.

  Configuration properties:

   'Name' -- the attribute/method which determines the value

   'AcquisitionType' -- controls how acquisition is used
     
     * 'implicit' -- use implicit acquisition

     * 'explicit' -- equivalent to 'implicit' unless the
       looked up value is a method and is called.
       In this case, the passed in object is an explicit
       acquisition wrapper.

     * 'none' -- do not use acquisition

   'CallType' -- controls how a callable result should be handled

     * 'call' -- call it and return the result

     * 'ignore' -- ignore value

     * 'return' -- return the value
   '''

  meta_type= 'Attribute Lookup'

  _properties= (
   (
     { 'id' : 'Name', 'type' : 'string', 'mode' : 'w',},
     { 'id' : 'AcquisitionType', 'type' : 'selection', 'select_variable' : 'listAcquisitionTypes', 'mode' : 'w',},
     { 'id' : 'CallType', 'type' : 'selection', 'select_variable' : 'listCallTypes', 'mode' : 'w',},
     )
     + ValueProvider._properties
     )

  Name= ''
  AcquisitionType= 'implicit'
  CallType= 'call'
   
  def _evaluate(self,object):
     aqType= self.AcquisitionType; orgObj = object
     name= self.Name or self.id
     # determine value
     if not hasattr(object,'aq_acquire'): aqType= 'implicit' # not wrapped
     elif hasattr(object.aq_base, name+'__index_aqType__'):
       aqType = getattr(object, name+'__index_aqType__')
     if aqType == 'explicit':
       # work around bug in "aq_acquire" (has 'default' argument but ignores it)
       try: value= object.aq_explicit.aq_acquire(name,default=None)
       except AttributeError: value= None
     else:
       if aqType == 'none': object= object.aq_base
       value= getattr(object,name,None)
       # allow acquisition for objets that explicitly called for it
       if value is Acquired: value = getattr(orgObj, name, None)
     # handle calls
     if safe_callable(value): 
       callType= self.CallType
       if callType == 'call': value= value()
       elif callType == 'ignore': value= None
     return value

  def listAcquisitionTypes(self):
    return ('implicit', 'none', 'explicit',)

  def listCallTypes(self):
    return ('call', 'return', 'ignore',)


class ExpressionEvaluator(ValueProvider,EvalAndCall):
  '''configures TALES evaluation.'''

  meta_type= 'Expression Evaluator'

  _properties= (
    EvalAndCall._properties
    + ValueProvider._properties
    )

  def _evaluate(self,object):
    return EvalAndCall._evaluate(self,object,object)
