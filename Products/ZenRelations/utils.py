from Exceptions import ZenImportError

def importClass(classpath, baseModule=None):
    """
    Import a class by its path use baseModule path if passed
    First try and import top package.  If it failes and baseModule hasn't been 
    passed we raise. If baseModule exists, which is just a shorthand way of 
    specifying classes in relationships using the zenRelationsBaseModule 
    attribute trying importing the class using baseModule + classpath.
    """
    try:
        cp = classpath.split('.')
        mod = __import__(cp[0])
        clist = cp[1:]
    except (ImportError, ValueError):
        if baseModule is None:
            raise ZenImportError("failed importing class '%s'" % classpath)
        try:
            cp = baseModule.split('.')
            mod = __import__(cp[0])
            clist = cp[1:] + classpath.split('.')
        except:
            raise ZenImportError(
                "failed importing class '%s' base '%s'" % (
                    classpath, baseModule))
    if not clist: return mod
    for comp in clist:
        try: mod = getattr(mod, comp)
        except AttributeError:
            raise ZenImportError(
                "failed importing class '%s' base '%s'" % (
                    classpath, baseModule))
    return getattr(mod, comp, mod)


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
