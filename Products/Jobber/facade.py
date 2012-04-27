###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from zope.dottedname.resolve import resolve
from celery.utils import fun_takes_kwargs
from .jobs import Job


class FacadeMethodJob(Job):
    """
    Serializes the details of a facade method call for later execution by
    zenjobs.
    """
    @classmethod
    def getJobType(cls):
        return "Python API"

    @classmethod
    def getJobDescription(cls, facadefqdn, method, *args, **kwargs):
        facade = facadefqdn.split('.')[-1]
        return "%s.%s %s" % (facade, method, args[0] if args else '')

    def _run(self, facadefqdn, method, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        facadeclass = resolve(facadefqdn)
        facade = facadeclass(self.dmd)
        bound_method = getattr(facade, method)
        accepted = fun_takes_kwargs(bound_method, kwargs)
        kwargs = dict((k, v) for k, v in kwargs.iteritems() if k in accepted)
        result = bound_method(*args, **kwargs)

