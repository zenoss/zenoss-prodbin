##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

from twisted.spread.jelly import jelly, unjelly


class _Converter(object):

    __slots__ = ("dumps", "loads")

    def __init__(self, dumps, loads):
        self.dumps = dumps
        self.loads = loads


def _float_str(f):
    return "{:.6f}".format(f).strip("0")


def _immutable(self, *args, **kw):
    raise TypeError("Object is immutable")


class _Fields(dict):
    """
    Describes all the attributes of a configuration record.
    """

    def __init__(self):
        super(_Fields, self).__init__(
            (
                ("data", _Converter(jelly, unjelly)),
                ("monitor", _Converter(str, str)),
                ("configid", _Converter(str, str)),
                ("service", _Converter(str, str)),
                ("updated", _Converter(_float_str, float)),
            )
        )

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable


Fields = _Fields()


class ConfigurationRecord(object):
    """
    Configuration data and associated metadata.

    :ivar data: Configuration data.
    :itype data: twisted.spread.pb.{Copyable,RemoteCopy}
    :ivar monitor: Name of the monitor (collector) associated with the data.
    :itype monitor: str
    """

    __slots__ = tuple(key for key in Fields.keys())

    @classmethod
    def make(cls, data):
        if not(data.viewkeys() <= Fields.viewkeys()):
            bad = data.viewkeys() ^ Fields.viewkeys()
            raise AttributeError(
                "ConfigurationRecord does not have attribute%s %s"
                % (
                    "" if len(bad) == 1 else "s",
                    ", ".join("'%s'" % v for v in bad),
                )
            )
        record = cls()
        for k, v in data.viewitems():
            setattr(record, k, v)
        return record

    @property
    def config_id(self):
        """
        The configuration ID.

        :rtype: str
        """
        return self.configid

    @property
    def service_name(self):
        """
        The name of the service that generated the configuration data.

        :rtype: str
        """
        return self.service

    @property
    def last_updated(self):
        """
        The timestamp of this record's most recent update.

        :returns: Unix timestamp
        :rtype: float
        """
        return self.updated

    def __str__(self):
        return "<{0.__class__.__name__}: {1}>".format(
            self,
            " ".join(
                "{0}={1!r}".format(name, getattr(self, name, None))
                for name in self.__slots__
            ),
        )

    def __hash__(self):
        raise TypeError("unhashable type: %r" % (type(self).__name__))
