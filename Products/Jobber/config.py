##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os

import attr

from Products.ZenUtils.config import Config, ConfigLoader
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils.RedisUtils import DEFAULT_REDIS_URL
from Products.ZenUtils.Utils import zenPath


_default_configs = {
    "logpath": "/opt/zenoss/log",
    "logseverity": 20,
    "maxlogsize": 10240,
    "maxbackuplogs": 3,
    "job-log-path": "/opt/zenoss/log/jobs",
    "zenjobs-job-expires": 604800,  # 7 days
    "scheduler-config-file": "/opt/zenoss/etc/zenjobs_schedules.yaml",
    "scheduler-max-loop-interval": 180,  # 3 minutes
    "zodb-config-file": "/opt/zenoss/etc/zodb.conf",
    "zodb-max-retries": 5,
    "zodb-retry-interval-limit": 30,  # 30 seconds
    "max-jobs-per-worker": 100,
    "concurrent-jobs": 1,
    "job-hard-time-limit": 21600,  # 6 hours
    "job-soft-time-limit": 18000,  # 5 hours
    "redis-url": DEFAULT_REDIS_URL,
}


_xform = {
    "concurrent-jobs": int,
    "job-hard-time-limit": int,
    "job-soft-time-limit": int,
    "logseverity": int,
    "maxbackuplogs": int,
    "max-jobs-per-worker": int,
    "maxlogsize": int,
    "scheduler-max-loop-interval": int,
    "zenjobs-job-expires": int,
    "zodb-max-retries": int,
    "zodb-retry-interval-limit": int,
}


_configuration = {}


def getConfig(filename=None):
    """Return a dict containing the configuration for zenjobs."""
    global _configuration

    if _configuration:
        return _configuration

    conf = _default_configs.copy()
    conf.update(getGlobalConfiguration())

    if filename is not None:
        if not os.path.exists(filename):
            filename = zenPath("etc", filename)

        app_config_loader = ConfigLoader([filename], Config)
        try:
            conf.update(app_config_loader())
        except IOError as ex:
            # Re-raise exception if the error is not "File not found"
            if ex.errno != 2:
                raise

    # Convert the configuration value types to useable types.
    for key, cast in _xform.items():
        if key not in conf:
            continue
        conf[key] = cast(conf[key])

    # only save it if a filename was specified
    if filename is not None:
        _configuration = conf

    return conf


# Broker settings
def buildBrokerUrl(cfg):
    usr = cfg.get("amqpuser")
    pwd = cfg.get("amqppassword")
    host = cfg.get("amqphost")
    port = cfg.get("amqpport")
    vhost = cfg.get("amqpvhost")
    return "amqp://{usr}:{pwd}@{host}:{port}/{vhost}".format(**locals())


@attr.s(slots=True, kw_only=True)
class CeleryConfig(object):
    """Celery configuration."""

    BROKER_URL = attr.ib()
    CELERY_RESULT_BACKEND = attr.ib()
    CELERY_TASK_RESULT_EXPIRES = attr.ib()
    CELERYD_CONCURRENCY = attr.ib()
    CELERYD_MAX_TASKS_PER_CHILD = attr.ib()
    CELERYD_TASK_TIME_LIMIT = attr.ib()
    CELERYD_TASK_SOFT_TIME_LIMIT = attr.ib()
    CELERYBEAT_MAX_LOOP_INTERVAL = attr.ib()

    CELERY_TIMEZONE = attr.ib(default=None)
    CELERY_ACCEPT_CONTENT = attr.ib(default=["without-unicode"])
    CELERY_IMPORTS = attr.ib(
        default=[
            "Products.Jobber.jobs",
            "Products.ZenCollector.configcache.task",
        ]
    )
    CELERY_ROUTES = attr.ib(
        default={"configcache.build_device_config": {"queue": "configcache"}}
    )
    CELERY_RESULT_SERIALIZER = attr.ib(default="without-unicode")
    CELERYD_PREFETCH_MULTIPLIER = attr.ib(default=1)
    CELERY_ACKS_LATE = attr.ib(default=True)
    CELERY_IGNORE_RESULT = attr.ib(default=False)
    CELERY_STORE_ERRORS_EVEN_IF_IGNORED = attr.ib(default=True)
    CELERY_TASK_SERIALIZER = attr.ib(default="without-unicode")
    CELERY_TRACK_STARTED = attr.ib(default=True)
    CELERYBEAT_REDIRECT_STDOUTS = attr.ib(default=True)
    CELERYBEAT_REDIRECT_STDOUTS_LEVEL = attr.ib(default="INFO")
    CELERY_SEND_EVENTS = attr.ib(default=True)
    CELERY_SEND_TASK_SENT_EVENT = attr.ib(default=True)
    CELERYD_LOG_COLOR = attr.ib(default=False)

    @classmethod
    def from_config(cls, cfg={}):
        args = {
            "BROKER_URL": buildBrokerUrl(cfg),
            "CELERY_RESULT_BACKEND": cfg.get("redis-url"),
            "CELERY_TASK_RESULT_EXPIRES": cfg.get("zenjobs-job-expires"),
            "CELERYD_CONCURRENCY": cfg.get("concurrent-jobs"),
            "CELERYD_MAX_TASKS_PER_CHILD": cfg.get("max-jobs-per-worker"),
            "CELERYD_TASK_TIME_LIMIT": cfg.get("job-hard-time-limit"),
            "CELERYD_TASK_SOFT_TIME_LIMIT": cfg.get("job-soft-time-limit"),
            "CELERYBEAT_MAX_LOOP_INTERVAL": cfg.get(
                "scheduler-max-loop-interval"
            ),
        }
        tz = os.environ.get("TZ")
        if tz:
            args["CELERY_TIMEZONE"] = tz

        return cls(**args)
