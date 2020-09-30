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
from Products.ZenUtils.Utils import zenPath

__all__ = ("Celery", "ZenJobs")


_default_configs = {
    "logpath": "/opt/zenoss/log",
    "logseverity": "20",
    "maxlogsize": "10240",
    "maxbackuplogs": "3",
    "job-log-path": "/opt/zenoss/log/jobs",

    "scheduler-config-file": "/opt/zenoss/etc/zenjobs_schedule.yaml",
    "scheduler-max-loop-interval": 300,  # 5 minutes
    "scheduler-sync-interval": 180,  # 3 minutes

    "zodb-config-file": "/opt/zenoss/etc/zodb.conf",
    "zodb-max-retries": 5,
    "zodb-retry-interval-limit": 30,  # 30 seconds
    "max-jobs-per-worker": "100",
    "concurrent-jobs": "1",
    "job-expires": 604800,  # 7 days
    "job-hard-time-limit": 21600,  # 6 hours
    "job-soft-time-limit": 18000,  # 5 hours
}


class _ZenJobsConfig(Config):
    """Config preconfigured with defaults for ZenJobs."""

    def __init__(self, *args, **kwargs):
        """Initialize a ZenJobsConfig instance."""
        conf = dict(_default_configs)
        conf.update(args, **kwargs)
        super(_ZenJobsConfig, self).__init__(conf)


_zenjobs_conf_file = zenPath("etc", "zenjobs.conf")
_zenjobs_config_loader = ConfigLoader(_zenjobs_conf_file, _ZenJobsConfig)


def _getConfig():
    """Return a dict containing the configuration for zenjobs."""
    conf = getGlobalConfiguration()
    try:
        appconf = _zenjobs_config_loader()
    except IOError as ex:
        # Re-raise exception if the error is not "File not found"
        if ex.errno != 2:
            raise
        appconf = _default_configs
    conf.update(appconf)
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
    CELERY_IMPORTS = (
        "Products.Jobber.jobs",
    )

    # Result backend (redis)
    CELERY_RESULT_BACKEND = "redis://localhost/0"
    CELERY_RESULT_SERIALIZER = "without-unicode"
    CELERY_TASK_RESULT_EXPIRES = int(ZenJobs.get("job-expires"))

    # Worker configuration
    CELERYD_CONCURRENCY = int(ZenJobs.get("concurrent-jobs"))
    CELERYD_PREFETCH_MULTIPLIER = 1
    CELERYD_MAX_TASKS_PER_CHILD = int(ZenJobs.get("max-jobs-per-worker"))
    CELERYD_TASK_TIME_LIMIT = int(ZenJobs.get("job-hard-time-limit"))
    CELERYD_TASK_SOFT_TIME_LIMIT = int(ZenJobs.get("job-soft-time-limit"))

    # Task settings
    CELERY_ACKS_LATE = True
    CELERY_IGNORE_RESULT = False
    CELERY_STORE_ERRORS_EVEN_IF_IGNORED = True
    CELERY_TASK_SERIALIZER = "without-unicode"
    CELERY_TRACK_STARTED = True

    # Beat (scheduler) configuration
    CELERYBEAT_MAX_LOOP_INTERVAL = int(
        ZenJobs.get("scheduler-max-loop-interval"),
    )
    CELERYBEAT_SYNC_EVERY = int(ZenJobs.get("scheduler-sync-interval"))
    CELERYBEAT_LOG_FILE = os.path.join(
        ZenJobs.get("logpath"), "zenjobs-scheduler.log",
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
