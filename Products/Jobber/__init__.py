import sys
import warnings

class JobberBackCompatLoader(object):

    __path__ = []

    def find_module(self, fullname, mpath=None):
        if fullname=='Products.Jobber.status':
            return self

    def load_module(self, fullname):
        return self

    def __getattr__(self, attr):
        warnings.warn("Products.Jobber.status.%s has been removed." % attr, 
                      DeprecationWarning)

sys.meta_path.append(JobberBackCompatLoader())
