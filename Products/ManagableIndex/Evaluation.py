# Copyright (C) 2003 by Dr. Dieter Maurer, Eichendorffstr. 23, D-66386 St. Ingbert, Germany
# see "LICENSE.txt" for details
#       $Id: Evaluation.py,v 1.5 2006/04/09 16:52:03 dieter Exp $
'''TALES evaluation for different purposes.'''

from AccessControl import getSecurityManager
from Acquisition import Explicit, Implicit
from Persistence import Persistent

from OFS.PropertyManager import PropertyManager
from DocumentTemplate.DT_Util import safe_callable

from Products.PageTemplates.Expressions import getEngine, SecureModuleImporter

import ManagableIndex


class Eval(PropertyManager,Explicit,Persistent):
  '''evaluate a TALES expression and return the result.'''
  # to be overridden by derived classes
  ExpressionProperty= 'Expression'

  _properties= (
    { 'id' : ExpressionProperty, 'type' : 'string', 'mode' : 'w',},
    )

  Expression= ''

  def __init__(self,exprProperty= None):
    if exprProperty: self.ExpressionProperty= exprProperty

  def _evaluate(self,value,object):
    '''evaluate our expression property in a context containing
    *value*, *object*, 'index', 'catalog' and standard names.'''
    index= self._findIndex()
    catalog= index.aq_inner.aq_parent # ATT: do we need to go up an additional level?
    # work around bug in "aq_acquire" (has 'default' argument but ignores it)
    try: request= object.aq_acquire('REQUEST',default=None)
    except AttributeError: request= None
    try: container= object.aq_inner.aq_parent
    except AttributeError: container= None
    data= {
      'value' : value,
      'index' : index,
      'catalog' : catalog,
      'object' : object,
      'here' : object, # compatibility
      'container' : container,
      'nothing' : None,
      'root' : index.getPhysicalRoot(),
      #'request': object.aq_acquire('REQUEST',default=None),
      'request': request,
      'modules' : SecureModuleImporter,
      'user' : getSecurityManager().getUser(),
      }
    context= getEngine().getContext(data)
    expr= self._getExpression()
    return expr(context)

  def _findIndex(self):
    '''return the nearest 'ManagableIndex' above us.'''
    obj= self
    while not isinstance(obj,ManagableIndex.ManagableIndex):
      obj= obj.aq_inner.aq_parent
    return obj

  _v_expression= 0
  _v_expr_string= None
  def _getExpression(self):
    '''return the TALES expression to be evaluated.'''
    expr= self._v_expression
    expr_string= self.aq_acquire(self.ExpressionProperty)
    if expr != 0 and self._v_expr_string == expr_string: return expr
    expr= self._v_expression= getEngine().compile(expr_string)
    self._v_expr_string= expr_string
    return expr

  def _getExpressionString(self):
    # this uses 'aq_aquire', because we want to support independent multiple inheritance
    return self.aq_acquire(self.ExpressionProperty)


class EvalAndCall(Eval):
  '''evaluate and then call with *value*, if possible.'''
  def _evaluate(self,value,object):
    v= EvalAndCall.inheritedAttribute('_evaluate')(self,value,object)
    if safe_callable(v): v= v(value)
    return v


class Ignore(PropertyManager,Implicit):
  '''ignore values for which 'IgnorePredicate' gives true.'''
  IgnoreProperty= 'IgnorePredicate'

  _properties= (
    {'id' : IgnoreProperty, 'type' : 'string', 'mode' : 'w',},
    )
  IgnorePredicate= ''

  _v_IgnoreEvaluator= None
  def _ignore(self,value,object):
    if value is None: return
    if not self._hasIgnorer(): return value
    evaluator= self._v_IgnoreEvaluator
    if evaluator is None:
      evaluator= self._v_IgnoreEvaluator= EvalAndCall(self.IgnoreProperty)
      evaluator= evaluator.__of__(self)
    if evaluator._evaluate(value,object): return
    return value

  def _hasIgnorer(self):
    return getattr(self,self.IgnoreProperty,None)

class Normalize(PropertyManager,Implicit):
  '''normalize value by the 'Normalizer' expression.'''
  NormalizerProperty= 'Normalizer'

  _properties= (
    {'id' : NormalizerProperty, 'type' : 'string', 'mode' : 'w',},
    )
  Normalizer= ''

  _v_NormalizeEvaluator= None
  def _normalize(self,value,object):
    if value is None: return
    if not self._hasNormalizer(): return value
    evaluator= self._v_NormalizeEvaluator
    if evaluator is None:
      evaluator= self._v_NormalizeEvaluator= EvalAndCall(self.NormalizerProperty)
      evaluator= evaluator.__of__(self)
    if not evaluator._getExpressionString(): return value
    return evaluator._evaluate(value,object)

  def _hasNormalizer(self):
    return getattr(self,self.NormalizerProperty,None)
