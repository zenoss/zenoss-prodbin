
class NullProxy:
    
    def __init__(self, filename, classname):
        self.filename = filename
        self.classname = classname
        self.obj = None

    def start(self, timer, *args, **kw):
        fp = open(self.filename)
        try:
            locals = {}
            exec fp in locals
            self.obj = locals[self.classname](*args, **kw)
        finally:
            fp.close()

    def stop(self):
        if self.obj and hasattr(self.obj, 'close'):
            self.obj.close()
        self.obj = None

    def boundedCall(self, timer, method, *args, **kw):
        return getattr(self.obj, method)(*args, **kw)
