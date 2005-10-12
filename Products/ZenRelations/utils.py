from Exceptions import ZenImportError

def importClass(classpath, baseModule=None):
    """lookup a class by its path use baseModule path if passed"""
    if baseModule: classpath = ".".join((baseModule, classpath))
    try:
        mod = __import__(classpath)
    except ImportError:
        try:
            mod = __import__(".".join(classpath.split(".")[:-1]))
        except:
            raise ZenImportError("failed importing class %s" % classpath)
    for comp in classpath.split(".")[1:]:
        mod = getattr(mod, comp)
    classdef = getattr(mod, comp, None)
    if classdef: mod = classdef
    return mod


def importClasses(basemodule=None, skipnames=()):
    """
    import all classes listed in baseModule in the variable productNames
    and return them in a list.  Assume that classes are defined in a file
    with the same name as the class.
    """
    classList = []
    mod = __import__(basemodule)
    for comp in basemodule.split(".")[1:]:
        mod = getattr(mod, comp)
    for prodname in mod.productNames:
        if prodname in skipnames: continue
        classdef = importClass(prodname, basemodule) 
        classList.append(classdef)
    return classList
