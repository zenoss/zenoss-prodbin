from Products import Zuul

def decorator(decorator_func):
    """
    Turns a function into a well-behaved decorator.

    Requires the signature (func, *args, **kwargs).
    
    Updates the inner function to look like the decorated version by
    copying attributes from the one to the other.
    """
    def _decorator(func):
        def inner(*args, **kwargs):
            return decorator_func(func, *args, **kwargs)
        inner.__name__ = func.__name__
        inner.__doc__ = func.__doc__
        inner.__module__ = func.__module__
        try:
            inner.__dict__.update(func.__dict__)
        except:
            pass
        return inner
    return _decorator


@decorator
def marshal(f, *args, **kwargs):
    result = f(*args, **kwargs)
    return Zuul.marshal(result)
    

def marshalto(keys=None, marshallerName=''):
    @decorator
    def marshal(f, *args, **kwargs):
        result = f(*args, **kwargs)
        return Zuul.marshal(result, keys=keys, marshallerName=marshallerName)
    return marshal


@decorator
def info(f, *args, **kwargs):
    """
    Apply Zuul.info to results.
    """
    result = f(*args, **kwargs)
    return Zuul.info(result)


def infoto(adapterName=''):
    @decorator
    def info(f, *args, **kwargs):
        result = f(*args, **kwargs)
        return Zuul.info(result, adapterName=adapterName)
    return info

