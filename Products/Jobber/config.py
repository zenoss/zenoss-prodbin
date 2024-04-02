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
    "task-protocol": 1,
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

    broker_url = attr.ib()
    result_backend = attr.ib()
    result_expires = attr.ib()
    worker_concurrency = attr.ib()
    worker_max_tasks_per_child = attr.ib()
    task_time_limit = attr.ib()
    task_soft_time_limit = attr.ib()
    beat_max_loop_interval = attr.ib()

    timezone = attr.ib(default=None)
    accept_content = attr.ib(default=["without-unicode"])
    imports = attr.ib(
        default=[
            "Products.Jobber.jobs",
            "Products.ZenCollector.configcache.task",
        ]
    )
    task_routes = attr.ib(
        default={"configcache.build_device_config": {"queue": "configcache"}}
    )
    result_serializer = attr.ib(default="without-unicode")
    worker_prefetch_multiplier = attr.ib(default=1)
    task_acks_late = attr.ib(default=True)
    task_ignore_result = attr.ib(default=False)
    task_store_errors_even_if_ignored = attr.ib(default=True)
    task_serializer = attr.ib(default="without-unicode")
    task_track_started = attr.ib(default=True)
    CELERYBEAT_REDIRECT_STDOUTS = attr.ib(default=True)
    CELERYBEAT_REDIRECT_STDOUTS_LEVEL = attr.ib(default="INFO")
    worker_send_task_events = attr.ib(default=True)
    task_send_sent_event = attr.ib(default=True)
    worker_log_color = attr.ib(default=False)
    task_protocol = attr.ib(default=1)

    @classmethod
    def from_config(cls, cfg={}):
        args = {
            "broker_url": buildBrokerUrl(cfg),
            "result_backend": cfg.get("redis-url"),
            "result_expires": cfg.get("zenjobs-job-expires"),
            "worker_concurrency": cfg.get("concurrent-jobs"),
            "worker_max_tasks_per_child": cfg.get("max-jobs-per-worker"),
            "task_time_limit": cfg.get("job-hard-time-limit"),
            "task_soft_time_limit": cfg.get("job-soft-time-limit"),
            "beat_max_loop_interval": cfg.get(
                "scheduler-max-loop-interval"
            ),
            "task_protocol": cfg.get("task-protocol", 1),
        }
        tz = os.environ.get("TZ")
        if tz:
            args["timezone"] = tz

        return cls(**args)
