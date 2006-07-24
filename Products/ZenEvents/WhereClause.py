import os
# FIXME
if 0:
    os.system('rm -f where.py')
    os.system('yapps2 where.g')
    os.system('chmod uog-w where.py')
import where
import types
from ActionRule import meta

def _tree2str(root):
    if type(root) == type(()):
        if len(root) == 1:
            if type(root[0]) == type(()):
                return '(%s)' % root[0]
            return '%s' % root[0]
        return '(%s %s %s)' % (_tree2str(root[1]), root[0], _tree2str(root[2]))
    return '%s' % root

def _noWildcards(s):
    return s.strip('%')


def toJavaScript(meta, clause):
    # P = where.WhereClause(where.WhereClauseScanner('2+2'))
    # print where.yappsrt.wrap_error_reporter(P, 'goal')
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

def fromFormVariables(form):
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
