# Working past #2288.  Zenoss 2.5.x --> 3.0 upgrades fail otherwise.

def _createExceptionRaiser(name):
    def raiser():
        raise Exception('The %s function should be imported from Products.ZenUtils.scripts.jsonutils.' % name)
    return raiser

def json(value):
    return _createExceptionRaiser('json')

def unjson(value):
    return _createExceptionRaiser('unjson')
