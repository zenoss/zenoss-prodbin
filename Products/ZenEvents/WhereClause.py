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
import types
from Products.ZenUtils.jsonutils import json


new_name_mapping = {
    ### evt context items:

    # This mapping has been confirmed.
    # Currently exists in current trigger plugin.
    # Confirmed exists in RuleBuilder subjects.
    'eventClass':'evt.event_class',

    # This mapping has been confirmed.
    # Currently exists in current trigger plugin.
    # Confirmed exists in RuleBuilder subjects.
    'summary':'evt.summary',

    # This mapping has been confirmed.
    # Currently exists in current trigger plugin.
    # Confirmed exists in RuleBuilder subjects.
    'message':'evt.message',

    # This is here for completeness - I just wanted to make sure I accounted for
    # all of the provided context in the current trigger plugin. There are some
    # new things made available, like 'fingerprint', that were not available to
    # previous rules.
    # There is no reason to include it in the actual mapping.
    # Confirmed exists in RuleBuilder subjects.
    # 'fingerprint' : 'evt.fingerprint'

    # This mapping has been confirmed.
    # Currently exists in current trigger plugin.
    # Confirmed exists in RuleBuilder subjects.
    'eventKey':'evt.event_key',

    # This mapping has been confirmed.
    # Currently exists in current trigger plugin.
    # Confirmed exists in RuleBuilder subjects.
    'agent':'evt.agent',

    # This mapping has been confirmed (manager -> monitor).
    # Currently exists in current trigger plugin.
    # Confirmed exists in RuleBuilder subjects.
    'manager':'evt.monitor',

    # This mapping has been confirmed.
    # Currently exists in current trigger plugin.
    # Confirmed exists in RuleBuilder subjects.
    'severity':'evt.severity',

    # This mapping has been confirmed.
    # Currently exists in current trigger plugin.
    # Confirmed exists in RuleBuilder subjects.
    'eventState':'evt.status',

    # This mapping has been confirmed.
    # Currently exists in current trigger plugin.
    # Confirmed exists in RuleBuilder subjects.
    'count':'evt.count',


    ### dev, elem and sub_elem context items

    # This mapping has been confirmed.
    # Currently exists in current trigger plugin.
    # Confirmed exists in RuleBuilder subjects.
    'prodState':'dev.production_state',

    # The element_identifier property of the event actor is set as the id, which
    # is then set as the name of the device.
    # This mapping has been confirmed.
    # Currently exists in current trigger plugin.
    # Confirmed exists in RuleBuilder subjects.
    # @TODO: Cofirm mapping in rulebuilder subjects is correct (Currently elem.name)
    'device':'dev.name',

    # 'uuid' was not previously available, but is included here for completeness.
    # There is no reason to include it in the actual mapping.
    # 'uuid' : 'dev.uuid'

    # This mapping has been confirmed. This is not to be confused with the
    # 'priority' -> 'evt.syslog_priority' mapping that is possible.
    # Currently exists in current trigger plugin.
    # Confirmed exists in RuleBuilder subjects.
    'devicePriority':'dev.priority',

    # This mapping has been confirmed.
    # Currently exists in current trigger plugin.
    # Confirmed exists in RuleBuilder subjects.
    'component':'sub_elem.name',
        

    # The mapping has been confirmed
    # @TODO: Make this available in the context items within trigger plugin.
    # @TODO: Make a RuleBuilder subject for this property.
    'eventClassKey':'evt.event_class_key',

    # The mapping has been confirmed
    # @TODO: Make this available in the context items within trigger plugin.
    # @TODO: Make a RuleBuilder subject for this property.
    'priority':'evt.syslog_priority',

    # @TODO: Confirm mapping (none in proxy.py).
    # @TODO: Make the mapping of this detail(?) available within trigger plugin.
    # @TODO: Make a RuleBuilder subject for this property.
    # @TODO: This will come from a DETAIL
    'location':'location',

    # @TODO: Confirm mapping (none in proxy.py).
    # @TODO: Do we have to update protos and add this property to actors?
    # @TODO: Make this property available.
    # @TODO: Make a RuleBuilder subject for this property.
    # @TODO: This will come from a DETAIL
    'deviceClass':'deviceClass',

    # This mapping has been confirmed.
    # @TODO: Make this available in the context items within trigger plugin.
    # @TODO: Make a RuleBuilder subject for this property.
    'facility':'evt.syslog_facility',

    # This mapping has been confirmed.
    # @TODO: Make this available in the context items within trigger plugin.
    # @TODO: Make a RuleBuilder subject for this property.
    'ntevid':'evt.nt_event_code',

    # @TODO: Confirm mapping (none in proxy.py).
    # @TODO: Make the mapping of this detail(?) available within trigger plugin.
    # @TODO: Make a RuleBuilder subject for this property.
    # @TODO: This comes from a DETAIL
    'ipAddress':'ipAddress',

    # @TODO: Confirm mapping (proxy.py maps to a summary field)
    # @TODO: Make this available in the context items within trigger plugin.
    # @TODO: Make a RuleBuilder subject for this property.
    'ownerId':'evt.current_user_name',

    # @TODO: Confirm mapping (none in proxy.py).
    # @TODO: Make the mapping of this detail(?) available within trigger plugin.
    # @TODO: Make a RuleBuilder subject for this property.
    # @TODO: This will come from a DETAIL
    'systems':'systems',

    # @TODO: Confirm mapping
    # @TODO: Make the mapping of this available within trigger plugin.
    # @TODO: Make a RuleBuilder subject for this property.
    # @TODO: This will come from a DETAIL
    'deviceGroups':'deviceGroups',
}

def getName(str):
    # lookup the old to new map
    if str in new_name_mapping:
        return new_name_mapping[str]
    # don't know a better way to error yet.
    return str

def getValue(val):
    # escape things
    if isinstance(val, basestring):
        return "'%s'" % val.replace("'", "\'")
    else:
        return val

def getEndsWith(name, value):
    return "{name}.endswith({value})".format(
            name=getName(name),
            value=getValue(value)
            )

def getBeginsWith(name, value):
    return "{name}.beginswith({value})".format(
            name=getName(name),
            value=getValue(value)
            )

def getIn(name, value):
    return "{value} in {name}".format(
            name=getName(name),
            value=getValue(value)
            )

def getNotIn(name, value):
    return "{value} not in {name}".format(
            name=getName(name),
            value=getValue(value)
            )

def getEquality(name, op, value):
    return "{name} {op} {value}".format(
            name=getName(name),
            op=op,
            value=getValue(value)
            )


negativeModes = (
'!', # is not
'!~', # does not contain
'!^',   # does not begin with
)

def q(s):
    # turn string "fo'o" -> "'fo''o'"
    return "'%s'" % "''".join(s.split("'"))

class Error(Exception): pass

class WhereJavaScript:
    "Base class for converting to/from javascript"
    type = 'unknown'

    def __init__(self, label):
        self.label = label

    def genProperties(self, name):
        return '%s:{type:"%s",label:"%s"}' % (name, self.type, self.label)

    def buildClause(self, name, value, mode):
        foundNegativeMatch = False
        result = []
        for v in value:
            if not v: return None
            if mode in negativeModes: foundNegativeMatch = True
            result.append(self.buildClause1(name, v, mode))
        if not result:
            return None
        if foundNegativeMatch:
            return ' and '.join(result)
        else:
            return ' or '.join(result)

class Text(WhereJavaScript):
    "Convert to/from javascript for text entries"
    type = 'text'

    def toJS(self, mode, value):
        if mode == 'like':
            if value.startswith('%') and not value.endswith('%'):
                return '$', [value[1:]]
            elif not value.startswith('%') and value.endswith('%'):
                return '^', [value[:-1]]
            elif value.startswith('%') and value.endswith('%'):
                return '~', [value[1:-1]]
        if mode == 'not like':
            return '!~', [value[1:-1]]
        if mode == '=':
            return '', [value]
        if mode == '!=':
            return '!', [value]

    def buildPython(self, name, mode, value):
        if mode == 'like':
            if value.startswith('%') and not value.endswith('%'):
                return getEndsWith(name, value[1:])
            elif not value.startswith('%') and value.endswith('%'):
                return getBeginsWith(name, value[:-1])
            elif value.startswith('%') and value.endswith('%'):
                return getIn(name, value[1:-1])
        if mode == 'not like':
            return getNotIn(name, value[1:-1])
        if mode == '=':
            return getEquality(name, '==', value)
        if mode == '!=':
            return getEquality(name, '!=', value)

    def buildClause1(self, name, v, mode):
        if mode == '~':
            return "%s like %s" % (name, q('%' + v + '%'))
        if mode == '^':
            return "%s like %s" % (name, q(v + '%'))
        if mode == '$':
            return "%s like %s" % (name, q('%' + v))
        if mode == '!~':
            return "%s not like %s" % (name, q('%' + v + '%'))
        if mode == '':
            return "%s = %s" % (name, q(v))
        if mode == '!':
            return "%s != %s" % (name, q(v))


class Select(WhereJavaScript):
    "Convert to/from javascript and where clause element for select entries"
    type = 'select'

    def __init__(self, label, options):
        WhereJavaScript.__init__(self, label)
        if options:
            if type(options[0]) != type(()):
                options = zip(range(len(options)), options)
        self.options = options

    def labelFromValue(self, value):
        return dict(self.options).get(value, 'Unknown')

    def valueFromLabel(self, value):
        return dict([(v, l) for l, v in self.options]).get(value, -1)

    def toJS(self, operator, value):
        if operator == '=':
            return ('', [self.labelFromValue(value)])
        if operator == '!=':
            return ('!', [self.labelFromValue(value)])
        result = []
        if operator in ('<', '>', '<=', '>='):
            for i, name in self.options:
                if eval('%d %s %d' % (i, operator, value)):
                    result.append(name)
        return ('', result)

    def buildPython(self, name, operator, value):
        if operator == '=':
            return getEquality(name, '==', value)
        else:
            return getEquality(name, operator, value)

    def genProperties(self, name):
        return '%s:{type:"%s",label:"%s", options:%r}' % (
            name, self.type, self.label, [s[1] for s in self.options])

    def buildClause1(self, name, v, mode):
        v = self.valueFromLabel(v)
        if type(v) in types.StringTypes:
            v = q(v)
        if mode == '':
            return "%s = %s" % (name, v)
        else:
            return "%s != %s" % (name, v)

    def buildMultiValuePython(self, name, mode, value):

        value = value.strip('%|')

        # if mode == 'like':
        #     if value.startswith('%') and not value.endswith('%'):
        #         return 'any(d.endswith({value}) for d in {name})'.format(value=getValue(bare_value), name=getName(name))
        #     elif not value.startswith('%') and value.endswith('%'):
        #         return 'any(d.startswith({value}) for d in {name})'.format(value=getValue(bare_value), name=getName(name))
        #     elif value.startswith('%') and value.endswith('%'):
        #         return 'any({value} in d for d in {name})'.format(value=getValue(bare_value), name=getName(name))
        #     else:
        #         return getIn(name, bare_value)
        #
        # if mode == 'not like':
        #     if value.startswith('%') and not value.endswith('%'):
        #         return 'not any(d.endswith({value}) for d in {name})'.format(value=getValue(bare_value), name=getName(name))
        #     elif not value.startswith('%') and value.endswith('%'):
        #         return 'not any(d.startswith({value}) for d in {name})'.format(value=getValue(bare_value), name=getName(name))
        #     elif value.startswith('%') and value.endswith('%'):
        #         return 'not any({value} in d for d in {name})'.format(value=getValue(bare_value), name=getName(name))
        #     else:
        #         return getNotIn(name, bare_value)

        if mode == 'like':
            return getIn(name, value)
        if mode == 'not like':
            return getNotIn(name, value)


class Compare(WhereJavaScript):
    "Convert to/from javascript and where clause elements for numeric comparisons"
    type = 'compare'

    def toJS(self, operator, value):
        return operator, [value]

    def buildPython(self, name, operator, value):
        if operator == '=':
            return getEquality(name, '==', value)
        else:
            return getEquality(name, operator, value)

    def buildClause1(self, name, v, mode):
        return "%s %s %s" % (name, mode, v)


class DeviceGroup(Select):
    def toJS(self, operator, value):
        if operator == 'like':
            return ['', [value[2:-1]]]
        if operator == 'not like':
            return ['!', [value[2:-1]]]

    def buildPython(self, name, operator, value):
        return self.buildMultiValuePython(name, operator, value)

    def buildClause1(self, name, v, mode):
        if mode == '':
            return "%s like %s" % (name, q('%|' + v + '%'))
        else:
            return "%s not like %s" % (name, q('%|' + v + '%'))
    
class EventClass(Select):
    type = 'evtClass'

    def toJS(self, operator, value):
        value = value.rstrip('%')
        if operator == '=':
            return ['', [value]]
        if operator == '!=':
            return ['!', [value]]
        if operator == 'like':
            return ['^', [value]]
        if operator == 'not like':
            return ['!^', [value]]

    def buildPython(self, name, operator, value):
                
        mode = operator
        if mode == 'like':
            if value.startswith('%') and not value.endswith('%'):
                return getEndsWith(name, value[1:])
            elif not value.startswith('%') and value.endswith('%'):
                return getBeginsWith(name, value[:-1])
            elif value.startswith('%') and value.endswith('%'):
                return getIn(name, value[1:-1])
            else:
                return 
        if mode == 'not like':
            return getNotIn(name, value[1:-1])
        if mode == '=':
            return getEquality(name, '==', value)
        if mode == '!=':
            return getEquality(name, '!=', value)

    def buildClause1(self, name, v, mode):
        if mode == '':
            return "%s = %s" % (name, q(v))
        elif mode == '^':
            return "%s like %s" % (name, q(v + '%'))
        elif mode == '!^':
            return "%s not like %s" % (name, q(v + '%'))
        else:
            return "%s != %s" % (name, q(v))



class Enumerated(Select):
    "Convert to/from javascript and where clause elements for enumerated types"
    type='cselect'

    def toJS(self, operator, value):
        return operator, [self.labelFromValue(value)]

    def buildPython(self, name, operator, value):
        if operator == '=':
            return getEquality(name, '==', value)
        else:
            return getEquality(name, operator, value)

    def buildClause1(self, name, v, mode):
        return "%s %s %s" % (name, mode, self.valueFromLabel(v))

_Definitions = r'''
def u(s):
    # turn string "'fo''o'" -> "fo'o"
    c = s[0]
    s = c.join(s.split(c+c))
    return s[1:-1]

'''

_ParseSpec = r'''
parser WhereClause:
    ignore:    "[ \r\t\n]+"
    token END: "$"
    token NUM: "[0-9]+"
    token VAR: "[a-zA-Z0-9_]+"
    token BIN: ">=|<=|==|=|<|>|!=|<>"
    token STR: r'"([^\\"]+|\\.)*"'
    token STR2: r"'([^\\']+'{2,}|[^\\']+|\\.)*'"

    rule goal:    andexp ? END       {{ return locals().get('andexp', None) }}

    rule andexp:  orexp              {{ e = orexp }}
                  ( "and" orexp      {{ e = ('and', e, orexp) }}
                  )*                 {{ return e }}

    rule orexp:   binary             {{ e = binary }}
                  ( "or" binary      {{ e = ('or', e, binary) }}
                  )*                 {{ return e }}

    rule binary:  term               {{ e = term }}
                  ( BIN term         {{ e = (BIN, e, term) }}
                    | 'like' term    {{ e = ('like', e, term) }}
                    | 'not' 'like' term
                                     {{ e = ('not like', e, term) }}
                  )*                 {{ return e }}

    rule term:    NUM                {{ return int(NUM) }}
                  | VAR              {{ return VAR }}
                  | STR              {{ return u(STR) }}
                  | STR2             {{ return u(STR2) }}
                  | "\\(" andexp "\\)" {{ return andexp }}
'''

class _Parser:
    def __init__(self, spec):
        from yapps import grammar, yappsrt
        from StringIO import StringIO

        scanner = grammar.ParserDescriptionScanner(spec)
        parser = grammar.ParserDescription(scanner)
        parser = yappsrt.wrap_error_reporter(parser, 'Parser')
        parser.preparser = _Definitions
        parser.output = StringIO()
        parser.generate_output()
        exec parser.output.getvalue() in self.__dict__

where = _Parser(_ParseSpec)

@json
def toJavaScript(meta, clause):
    # sql is case insensitive, map column names to lower-case versions
    lmeta = dict([(n.lower(), n) for n in meta.keys()])
    tree = where.parse('goal', clause)

    def recurse(root, result):
        if type(root) == types.TupleType:
            n = len(root)
            if n == 1:
                recurse(root[0], result)
            op, name, value = root
            if op in ('and', 'or'):
                recurse(root[1], result)
                recurse(root[2], result)
            else:
                name = lmeta.get(name.lower(), None)
                if name is not None:
                    op, value = meta[name].toJS(op, value)
                    result.append([name, op, value])

    result = []
    recurse(tree, result)
    result.sort()
    return result


def toPython(meta, clause):
    # sql is case insensitive, map column names to lower-case versions
    lmeta = dict([(n.lower(), n) for n in meta.keys()])
    tree = where.parse('goal', clause)
    
    def recurse(root, result):
        if type(root) == types.TupleType:
            n = len(root)
            if n == 1:
                recurse(root[0], result)
            op, name, value = root
            if op in ('and', 'or'):
                recurse(root[1], result)
                result.append(op)
                recurse(root[2], result)
            else:
                name = lmeta.get(name.lower(), None)
                if name is not None:
                    python_statement = meta[name].buildPython(name, op, value)
                    result.append('(%s)' % python_statement)

    result = []
    recurse(tree, result)
    return ' '.join(result)


def fromFormVariables(meta, form):
    result = []
    for n, attrType in meta.items():
        if form.has_key(n):
            value = form[n]
            if type(value) != type([]):
                value = [value]
            mode = form.get(n + "_mode", None)
            clause = attrType.buildClause(n, value, mode)
            if clause:
                result.append('(%s)' % clause)
    return ' and '.join(result);


if __name__ == '__main__':
    meta = {}
    toJavaScript(meta, 'severity = 3 or severity = 4')
    toJavaScript(meta, "severity >= 4 and eventState = 0 and prodState = 1000")
    toJavaScript(meta, "severity >= 2 and eventState = 0 and prodState = 1000")
    print toJavaScript(meta, '(prodState = 1000) and (eventState = 0 or eventState = 1) and (severity >= 3)')
    print fromFormVariables(meta,
                            dict(severity='Info',
                                 severity_mode='>',
                                 eventState='New',
                                 eventState_mode='=',
                                 prodState='Production',
                                 prodState_mode='='))
