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

BROKER_HOST = 'BROKER_HOST'
BROKER_PORT = 'BROKER_PORT'
BROKER_USER = 'BROKER_USER'
BROKER_PASSWORD = 'BROKER_PASSWORD'
BROKER_VHOST = 'BROKER_VHOST'
BROKER_USE_SSL = 'BROKER_USE_SSL'
RESULT_BACKEND = 'CELERY_RESULT_BACKEND'
MAX_TASKS_PER_PROCESS = 'CELERY_MAX_TASKS_PER_CHILD'
NUM_WORKERS = 'CELERYD_CONCURRENCY'
USE_CELERY_LOGGING = 'CELERYD_HIJACK_ROOT_LOGGER'
LOG_FORMAT = 'CELERYD_LOG_FORMAT'
TASK_LOG_FORMAT = 'CELERYD_TASK_LOG_FORMAT'
STDOUT_LOG_LEVEL = 'CELERY_REDIRECT_STDOUTS_LEVEL'
ACK_LATE = "CELERY_ACKS_LATE"
