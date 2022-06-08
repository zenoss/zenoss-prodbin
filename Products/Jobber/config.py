##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os

from Products.ZenUtils.config import Config, ConfigLoader
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils.RedisUtils import DEFAULT_REDIS_URL, getRedisUrl
from Products.ZenUtils.Utils import zenPath

__all__ = ("Celery", "ZenJobs")


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


def _getConfig():
    """Return a dict containing the configuration for zenjobs."""
    conf = _default_configs.copy()
    conf.update(getGlobalConfiguration())

    app_conf_file = zenPath("etc", "zenjobs.conf")
    app_config_loader = ConfigLoader(app_conf_file, Config)
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

    return conf


ZenJobs = _getConfig()


# Broker settings
def _buildBrokerUrl():
    usr = ZenJobs.get("amqpuser")
    pwd = ZenJobs.get("amqppassword")
    host = ZenJobs.get("amqphost")
    port = ZenJobs.get("amqpport")
    vhost = ZenJobs.get("amqpvhost")
    return "amqp://{usr}:{pwd}@{host}:{port}/{vhost}".format(**locals())


class Celery(object):
    """Celery configuration."""

    BROKER_URL = _buildBrokerUrl()
    CELERY_ACCEPT_CONTENT = ["without-unicode"]

    # List of modules to import when the Celery worker starts
    CELERY_IMPORTS = ("Products.Jobber.jobs",)

    # Result backend (redis)
    CELERY_RESULT_BACKEND = ZenJobs.get("redis-url")
    CELERY_RESULT_SERIALIZER = "without-unicode"
    CELERY_TASK_RESULT_EXPIRES = ZenJobs.get("zenjobs-job-expires")

    # Worker configuration
    CELERYD_CONCURRENCY = ZenJobs.get("concurrent-jobs")
    CELERYD_PREFETCH_MULTIPLIER = 1
    CELERYD_MAX_TASKS_PER_CHILD = ZenJobs.get("max-jobs-per-worker")
    CELERYD_TASK_TIME_LIMIT = ZenJobs.get("job-hard-time-limit")
    CELERYD_TASK_SOFT_TIME_LIMIT = ZenJobs.get("job-soft-time-limit")

    # Task settings
    CELERY_ACKS_LATE = True
    CELERY_IGNORE_RESULT = False
    CELERY_STORE_ERRORS_EVEN_IF_IGNORED = True
    CELERY_TASK_SERIALIZER = "without-unicode"
    CELERY_TRACK_STARTED = True

    # Beat (scheduler) configuration
    CELERYBEAT_MAX_LOOP_INTERVAL = ZenJobs.get("scheduler-max-loop-interval")
    CELERYBEAT_LOG_FILE = os.path.join(
        ZenJobs.get("logpath"), "zenjobs-scheduler.log"
    )
    CELERYBEAT_REDIRECT_STDOUTS = True
    CELERYBEAT_REDIRECT_STDOUTS_LEVEL = "INFO"

    # Event settings
    CELERY_SEND_EVENTS = True
    CELERY_SEND_TASK_SENT_EVENT = True

    # Log settings
    CELERYD_LOG_COLOR = False


# Timezone
_tz = os.environ.get("TZ")
if _tz:
    Celery.CELERY_TIMEZONE = _tz
