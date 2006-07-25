import types

class WhereJavaScript:
    "Base class for converting to/from javascript"
    type = 'unknown'
    def __init__(self, label):
        self.label = label
    def genProperties(self, name):
        return '%s:{type:"%s",label:"%s"}' % (name, self.type, self.label)

class Text(WhereJavaScript):
    "Convert to/from javascript for text entries"
    type = 'text'
    def toJS(self, mode, value):
        # FIXME: SQL string quoting 'foo''bar' -> "foo'bar"
        value = eval(value)             # turn string "'%foo%'" -> "%foo%"
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
    def buildClause(self, name, value, mode):
        result = []
        for v in value:
            if mode == '~':
                result.append("%s like '%%%s%%'" % (name, v))
            if mode == '^':
                result.append("%s like '%s%%'" % (name, v))
            if mode == '$':
                result.append("%s like '%%%s'" % (name, v))
            if mode == '!~':
                result.append("%s not like '%%%s%%'" % (name, v))
            if mode == '':
                result.append("%s = '%s'" % (name, v))
            if mode == '!':
                result.append("%s != '%s'" % (name, v))
        if not result:
            return None
        return ' or '.join(result)
        

class Select(WhereJavaScript):
    "Convert to/from javascript and where clause element for select entries"
    type = 'select'
    def __init__(self, label, options):
        WhereJavaScript.__init__(self, label)
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
    def genProperties(self, name):
        return '%s:{type:"%s",label:"%s", options:%r}' % (
            name, self.type, self.label, [s[1] for s in self.options])
    def buildClause(self, name, value, mode):
        result = []
        for v in value:
            v = self.valueFromLabel(v)
            if mode == '':
                result.append("%s = %d" % (name, v))
            else:
                result.append("%s != %d" % (name, v))
        return ' or '.join(result)

class Compare(WhereJavaScript):
    "Convert to/from javascript and where clause elements for numeric comparisons"
    type = 'compare'
    def toJS(self, operator, value):
        return operator, [value]
    def buildClause(self, name, value, mode):
        result = []
        for v in value:
            result.append("%s %s %s" % (name, mode, v))
        return ' or '.join(result)

class Enumerated(Select):
    "Convert to/from javascript and where clause elements for enumerated types"
    type='cselect'
    def toJS(self, operator, value):
        return operator, [self.labelFromValue(value)]
    def buildClause(self, name, value, mode):
        result = []
        for v in value:
            result.append("%s %s %s" % (name, mode, self.valueFromLabel(v)))
        return ' or '.join(result)

_ParseSpec = r'''
parser WhereClause:
    ignore:    "[ \r\t\n]+"
    token END: "$"
    token NUM: "[0-9]+"
    token VAR: "[a-zA-Z0-9_]+"
    token BIN: ">=|<=|==|=|<|>|!=|<>"
    token STR: r'"([^\\"]+|\\.)*"'
    token STR2: r"'([^\\']+|\\.)*'"

    rule goal:    andexp END         {{ return andexp }}

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
                  | STR              {{ return STR }}
                  | STR2             {{ return STR2 }}
                  | "\\(" andexp "\\)" {{ return andexp }}
'''


class _Parser:
    def __init__(self, spec):
        from yapps import grammar, yappsrt
        from StringIO import StringIO
        scanner = grammar.ParserDescriptionScanner(spec)
        parser = grammar.ParserDescription(scanner)
        parser = yappsrt.wrap_error_reporter(parser, 'Parser')
        parser.output = StringIO()
        parser.generate_output()
        exec parser.output.getvalue() in self.__dict__

where = _Parser(_ParseSpec)

def toJavaScript(meta, clause):
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
            if meta.has_key(name):
                op, value = meta[name].toJS(op, value)
                result.append([name, op, value])
    result = []
    recurse(tree, result)
    return result

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
    toJavaScript(meta, 'severity = 3 or severity = 4')
    toJavaScript(meta, "severity >= 4 and eventState = 0 and prodState = 1000")
    toJavaScript(meta, "severity >= 2 and eventState = 0 and prodState = 1000")
    print toJavaScript(meta, '(prodState = 1000) and (eventState = 0 or eventState = 1) and (severity >= 3)')
    print fromFormVariables(dict(severity='Info',
                                 severity_mode='>',
                                 eventState='New',
                                 eventState_mode='=',
                                 prodState='Production',
                                 prodState_mode='='))
