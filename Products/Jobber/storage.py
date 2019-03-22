##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import json
import logging
import re
import redis

from collections import Container, Iterable, Sized

from .config import Celery

_keybase = "zenjobs:job:"
_keypattern = _keybase + "*"
_keytemplate = "{}{{}}".format(_keybase)


log = logging.getLogger("zen.zenjobs")


def makeJobStore():
    """Create and return the ZenJobs JobStore client."""
    client = redis.StrictRedis.from_url(Celery.CELERY_RESULT_BACKEND)
    return JobStore(client, expires=Celery.CELERY_TASK_RESULT_EXPIRES)


class _Converter(object):

    __slots__ = ("dumps", "loads")

    def __init__(self, dumps, loads):
        self.dumps = dumps
        self.loads = loads


def _float_str(f):
    return "{:.6f}".format(f).strip("0")


class _Fields(dict):
    """Describes all the attributes of a job record.

    The keys are the names of the attributes and the values are tuples
    containing the encode and encode functions for the attribute value.

    Redis stores everything as strings, including integers and floats.
    """

    def __init__(self):
        super(_Fields, self).__init__((
            ("jobid", _Converter(str, str)),
            ("name", _Converter(str, str)),
            ("summary", _Converter(str, str)),
            ("description", _Converter(str, str)),
            ("userid", _Converter(str, str)),
            ("logfile", _Converter(str, str)),
            ("created", _Converter(_float_str, float)),
            ("started", _Converter(_float_str, float)),
            ("finished", _Converter(_float_str, float)),
            ("status", _Converter(str, str)),
            ("details", _Converter(json.dumps, json.loads)),
        ))


Fields = _Fields()


class _Any(object):
    """Mimics the 'in' operator's behavior via equality comparison.

    Returns True if the given value matches any of the initialized values.
    E.g.

        okvalues = _Any("foo", "bar", "baz")
        assert "foo" == okvalues
    """

    def __init__(self, *matches):
        if not all(isinstance(m, basestring) for m in matches):
            raise ValueError(
                "All values must be strings %s" % (matches,),
            )
        self.__matches = matches

    def __eq__(self, other):
        return any((m == other) for m in self.__matches)

    def __ne__(self, other):
        return not self.__eq__(other)


class _RegEx(object):
    """Applies a regular expression object using equality comparison.

    Returns True if the given value regular expression object's search
    method returns True. E.g.

        expr = _RegEx(re.compile("lan_c"))
        assert expr == "lan_c120_3v"
    """

    def __init__(self, expr):
        self.__expr = expr

    def __eq__(self, other):
        return self.__expr.search(other) is not None


class JobStore(Container, Iterable, Sized):
    """Implements an API for managing zenjobs' job data."""

    def __init__(self, client, expires=None):
        """Initialize a JobStore instance.

        :param client: A Redis client instance.
        :type client: redis.StrictRedis
        """
        self.__client = client
        self.__expires = expires

    def search(self, **fields):
        """Return the job IDs for jobs matching the search criteria.

        The job IDs are returned as an iterable.

        The field value(s) may be a string, a float, a sequence of strings,
        or a regular expression.  All other values will raise a TypeError
        exception.

        Specifying a field that does not exist in a record will raise an
        AttributeError exception.

        :param fields: The search criteria by field name.
        :type fields: Mapping[str, Union[str, float, RegEx, Interable[str]]]
        :return: The IDs for jobs matching the search criteria.
        :rtype: Iterable[str]
        :raises TypError: if an unsupported value type is given for a field
        """
        field_names = fields.keys()
        _verifyfields(field_names)
        matchers = {}
        for name, match in fields.items():
            # Note: check for string first because strings are also
            # iterable.
            if isinstance(match, basestring):
                matchers[name] = match
            elif isinstance(match, Iterable):
                matchers[name] = _Any(*match)
            elif isinstance(match, re._pattern_type):
                matchers[name] = _RegEx(match)
            elif isinstance(match, float):
                matchers[name] = "{:f}".format(match)
            else:
                raise TypeError(
                    "Type '%s' not supported for field '%s'"
                    % (type(match), name),
                )
        return (
            self.__client.hget(key, "jobid")
            for key in _iterkeys(self.__client)
            if matchers == dict(zip(
                field_names, self.__client.hmget(key, *field_names),
            ))
        )

    def getfield(self, jobid, name, default=None):
        """Return the field value in the job data identified by jobid.

        If jobid does not identify a job, the default value is returned.

        If the named field does not exist, an AttributeError
        exception is raised.

        :param str jobid: the job ID
        :param str name: the name of a field in the job data
        :return: the value of field or the default value
        :rtype: Any
        :raise AttributeError: if name is not a known field
        """
        if name not in Fields:
            raise AttributeError("Job record has no attribute '%s'" % name)
        key = _key(jobid)
        if not self.__client.exists(key):
            return default
        raw = self.__client.hget(key, name)
        if raw is None:
            return default
        return Fields[name].loads(raw)

    def update(self, jobid, **fields):
        """Set the field values on the identified job.

        If jobid does not identify a job, a KeyError exception is raised.

        If a field name does not identify a known field, an AttributeError
        exception is raised.

        @param jobid {str}
        @param fields {Mapping[str, Union[str, float, int, dict]]}
        @returns {None}
        @raises Union[AttributeError, KeyError]
        """
        badfields = fields.viewkeys() - Fields.viewkeys()
        if badfields:
            raise AttributeError(
                "Job record has no attribute%s %s" % (
                    "" if len(badfields) == 1 else "s",
                    ", ".join("'%s'" % name for name in badfields),
                ),
            )
        key = _key(jobid)
        if not self.__client.exists(key):
            raise KeyError("Job not found: %s" % jobid)
        deleted_fields = [k for k, v in fields.items() if v is None]
        if deleted_fields:
            self.__client.hdel(key, *deleted_fields)
        fields = {
            k: Fields[k].dumps(v)
            for k, v in fields.items() if v is not None
        }
        self.__client.hmset(key, fields)
        self.__expire_key_if_finished(key)

    def keys(self):
        """Return all existing job IDs.

        @returns {Iterable[str]}
        """
        return (
            self.__client.hget(key, "jobid")
            for key in _iterkeys(self.__client)
        )

    def values(self):
        """Return all existing job data.

        @returns {Iterable[Mapping[str, Union[str, float]]]}
        """
        items = _iteritems(self.__client)
        return (
            {k: Fields[k].loads(v) for k, v in fields.iteritems()}
            for _, fields in items
        )

    def items(self):
        """Return all existing jobs as (ID, data) pairs.

        @returns {Iterable[Tuple[str, Mapping[str, Union[str, float]]]]}
        """
        items = _iteritems(self.__client)
        return (
            (
                fields["jobid"],
                {k: Fields[k].loads(v) for k, v in fields.iteritems()},
            )
            for _, fields in items
        )

    def mget(self, *jobids):
        """Return job data for each provided job ID.

        The returned iterable will produce the job data in the same
        order given in the jobids parameter.

        @param jobids {Iterable[str]}
        @returns {Iterable[Mapping[str, Union[str, float]]]}
        """
        keys = (_key(jobid) for jobid in jobids)
        raw = (
            self.__client.hgetall(key)
            for key in keys
            if self.__client.exists(key)
        )
        return (
            {k: Fields[k].loads(v) for k, v in item.iteritems()}
            for item in raw
        )

    def get(self, jobid, default=None):
        """Return the job data for the given job ID.

        If the job ID is not found, the default argument is returned.

        @param jobid {str}
        @param default {Any}
        @returns {Mapping[str, Union[str, float]]}
        """
        key = _key(jobid)
        if not self.__client.exists(key):
            return default
        item = self.__client.hgetall(key)
        return {k: Fields[k].loads(v) for k, v in item.iteritems()}

    def __getitem__(self, jobid):
        """Return the job data for the given job ID.

        If the job ID is not found, a KeyError exception is raised.

        @param jobid {str}
        @returns {Mapping[str, Union[str, float]]}
        @raises {KeyError}
        """
        key = _key(jobid)
        if not self.__client.exists(key):
            raise KeyError("Job not found: %s" % jobid)
        item = self.__client.hgetall(key)
        return {k: Fields[k].loads(v) for k, v in item.iteritems()}

    def __setitem__(self, jobid, data):
        """Insert or replace the job data for the given job ID.

        If the data contains unknown fields, a ValueError exception is raised.

        @param jobid {str}
        @param data {Mapping[str, Union[str, float]]}
        @raises {ValueError}
        """
        _verifyfields(data.keys())
        data = {
            k: Fields[k].dumps(v)
            for k, v in data.items() if v is not None
        }
        key = _key(jobid)
        olddata = self.__client.hgetall(key)
        deleted_fields = set(olddata) - set(data)
        if deleted_fields:
            self.__client.hdel(key, *deleted_fields)
        self.__client.hmset(key, data)
        self.__expire_key_if_finished(key)

    def mdelete(self, *jobids):
        """Delete the job data associated with each of the given job IDs.

        @param jobsids {Iterable[str]} An iterable producing Job IDs
        """
        if not jobids:
            return
        jobids = (_key(jobid) for jobid in jobids)
        self.__client.delete(*jobids)

    def __delitem__(self, jobid):
        """Delete the job data associated with the given job ID.

        If the job ID does not exist, a KeyError is raised.

        @param jobid {str}
        """
        key = _key(jobid)
        if not self.__client.exists(key):
            raise KeyError("Job not found: %s" % jobid)
        self.__client.delete(key)

    def __contains__(self, jobid):
        """Return True if job data exists for the given job ID."""
        return self.__client.exists(_key(jobid))

    def __len__(self):
        cursor = 0
        count = 0
        while True:
            cursor, keys = self.__client.scan(cursor, match=_keypattern)
            count += len(keys)
            if cursor == 0:
                break
        return count

    def __iter__(self):
        """Return an iterable producing all the job IDs in the datastore.

        @returns {Iterable[str]}
        """
        return self.keys()

    def __expire_key_if_finished(self, key):
        finished = self.__client.hget(key, "finished")
        if self.__expires and finished:
            self.__client.expire(key, self.__expires)


def _key(jobid):
    """Return the redis key for the given job ID."""
    return _keytemplate.format(jobid)


def _iterkeys(client):
    """Return an iterable of redis keys to job data."""
    cursor = 0
    while True:
        cursor, data = client.scan(cursor, match=_keypattern)
        for key in data:
            yield key
        else:
            if cursor == 0:
                break


def _iteritems(client):
    """Return an iterable of (redis key, job data) pairs.

    Only (key, data) pairs where data is not None are returned.
    """
    keys = _iterkeys(client)
    raw = ((key, client.hgetall(key)) for key in keys)
    return ((key, data) for key, data in raw if data)


def _verifyfields(fields):
    bad_fields = set(fields) - set(Fields)
    if len(bad_fields):
        raise AttributeError("Invalid field%s %s" % (
            "" if len(bad_fields) == 1 else "s",
            ", ".join("'%s'" % n for n in bad_fields),
        ))
