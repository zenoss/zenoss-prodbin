##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################
import re

REDIS_URL_RE = re.compile("^redis://(?P<host>[^:/]+)(:(?P<port>\d+))?(/(?P<db>\d+))?(\?(?P<optionStr>.+))?$")

def parseRedisUrl(url):
    """
    Parses url and returns a dict of redis options suitable for the the redis client.
    """
    parsedUrl = REDIS_URL_RE.match(url)
    if parsedUrl is None:
        raise ValueError("malformed redis URL")
    host = parsedUrl.group('host')
    port = 16379 if parsedUrl.group('port') is None else int(parsedUrl.group('port'))
    db = 0 if parsedUrl.group('db') is None else int(parsedUrl.group('db'))
    options = {'host': host, 'port': port, 'db': db}
    optStr = parsedUrl.group('optionStr')
    if optStr is not None and len(optStr):
        try:
            for s in optStr.split(","):
                key, value = s.split("=", 1)
                if value.isdigit():
                    value = int(value)
                if s in ['host', 'port', 'db']:
                    raise ValueError("malformed redis URL, can not specify %r in options string" % key)
                options[key] = value
        except ValueError:
            raise
        except Exception as ex:
            raise ValueError("malformed redis URL: %s", ex)
    return options


