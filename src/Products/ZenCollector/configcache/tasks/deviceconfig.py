##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from datetime import datetime
from time import time

from zope.component import createObject
from zope.dottedname.resolve import resolve

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl

from Products.Jobber.task import requires, DMD
from Products.Jobber.task.event import send_event
from Products.Jobber.zenjobs import app

from ..cache import DeviceKey, DeviceRecord, ConfigStatus
from ..constants import Constants
from ..utils import DeviceProperties


@app.task(
    bind=True,
    base=requires(DMD),
    name="configcache.build_device_config",
    summary="Create Device Configuration Task",
    description_template="Create the {2} configuration for device {1}.",
    ignore_result=True,
    dmd_read_only=True,
)
def build_device_config(
    self, monitorname, deviceid, configclassname, submitted=None
):
    """
    Create a configuration for the given device.

    @param monitorname: The name of the monitor/collector the device
        is a member of.
    @type monitorname: str
    @param deviceid: The ID of the device
    @type deviceid: str
    @param configclassname: The fully qualified name of the class that
        will create the device configuration.
    @type configclassname: str
    @param submitted: timestamp of when the job was submitted
    @type submitted: float
    """
    try:
        buildDeviceConfig(
            self.dmd,
            self.log,
            monitorname,
            deviceid,
            configclassname,
            submitted,
        )
    except Exception as exc:
        self.log.exception(
            "unexpected error building device config  "
            "monitor=%s device=%s configclass=%s",
            monitorname,
            deviceid,
            configclassname,
        )
        try:
            send_event(
                self,
                exc,
                self.request.id,
                (monitorname, deviceid, configclassname),
                {"submitted": submitted},
            )
        except Exception:
            self.log.exception(
                "error while sending event about previous error"
            )


# NOTE: the buildDeviceConfig function exists so that it can be tested
# without having to handle Celery details in the unit tests.


def buildDeviceConfig(
    dmd, log, monitorname, deviceid, configclassname, submitted
):
    svcname = configclassname.rsplit(".", 1)[0]
    key = DeviceKey(svcname, monitorname, deviceid)

    # Record when this build starts
    started = time()

    # Skip this job if the device is not found in ZODB
    device = dmd.Devices.findDeviceByIdExact(deviceid)
    if device is None:
        log.warn(
            "cannot build config because device was not found  "
            "device=%s collector=%s service=%s submitted=%f",
            key.device,
            key.monitor,
            key.service,
            submitted,
        )
        # Speculatively delete the config because this device may have been
        # re-identified under a new ID so the config keyed by the old ID
        # should be removed.
        _delete_config(key, _getStore(), log)
        return

    store = _getStore()

    original_status = store.get_status(key)  # this may return None

    # Change the configuration's status to 'building' to indicate that
    # a config is now building.
    store.set_building((key, time()))
    log.info(
        "building device configuration  device=%s collector=%s service=%s",
        deviceid,
        monitorname,
        svcname,
    )

    try:
        svcconfigclass = resolve(configclassname)
    except Exception:
        log.warn("could not load config service  service=%s", configclassname)
        _delete_config(key, store, log)
        return

    service = svcconfigclass(dmd, monitorname)
    method = getattr(service, "remote_getDeviceConfigs", None)
    if method is None:
        log.warn(
            "config service does not have required API  "
            "device=%s collector=%s service=%s submitted=%f",
            key.device,
            key.monitor,
            key.service,
            submitted,
        )
        # Services without a remote_getDeviceConfigs method can't create
        # device configs, so delete the config that may exist.
        _delete_config(key, store, log)
        return

    result = service.remote_getDeviceConfigs((deviceid,))
    config = result[0] if result else None

    # get a new store; the prior store's connection may have gone stale.
    store = _getStore()
    if config is None:
        log.info(
            "no configuration built  device=%s collector=%s service=%s",
            key.device,
            key.monitor,
            key.service,
        )
        _delete_config(key, store, log)
    else:
        uid = device.getPrimaryId()
        record = DeviceRecord.make(
            svcname, monitorname, deviceid, uid, time(), config
        )

        # Get the current status of the configuration.
        recent_status = store.get_status(key)

        # Determine whether the status should be updated
        update_status = _should_update_status(
            recent_status, started, deviceid, monitorname, svcname, log
        )

        if not update_status:
            store.put_config(record)
            log.info(
                "saved config without changing status  "
                "updated=%s device=%s collector=%s service=%s",
                datetime.fromtimestamp(record.updated).isoformat(),
                deviceid,
                monitorname,
                svcname,
            )
        else:
            verb = "replaced" if original_status is not None else "added"
            store.add(record)
            log.info(
                "%s config  updated=%s device=%s collector=%s service=%s",
                verb,
                datetime.fromtimestamp(record.updated).isoformat(),
                deviceid,
                monitorname,
                svcname,
            )


def _should_update_status(
    recent_status, started, deviceid, monitorname, svcname, log
):
    # Check for expected statuses.
    if isinstance(recent_status, ConfigStatus.Building):
        # The status is Building, so let's update the status.
        return True

    if isinstance(recent_status, ConfigStatus.Expired):
        update_status = bool(recent_status.expired < started)
        if not update_status:
            log.info(
                "config expired while building config  "
                "device=%s collector=%s service=%s",
                deviceid,
                monitorname,
                svcname,
            )
        else:
            log.warning(
                "config status has inconsistent state  status=Expired "
                "expired=%s device=%s collector=%s service=%s",
                datetime.fromtimestamp(recent_status.expired).isoformat(),
                deviceid,
                monitorname,
                svcname,
            )
        return update_status

    if isinstance(recent_status, ConfigStatus.Pending):
        update_status = bool(recent_status.submitted < started)
        if not update_status:
            log.info(
                "another job submitted while building config  "
                "device=%s collector=%s service=%s",
                deviceid,
                monitorname,
                svcname,
            )
        else:
            log.warning(
                "config status has inconsistent state  status=Pending "
                "submitted=%s device=%s collector=%s service=%s",
                datetime.fromtimestamp(recent_status.submitted).isoformat(),
                deviceid,
                monitorname,
                svcname,
            )
        return update_status

    log.warning(
        "Unexpected status change during config build  "
        "status=%s device=%s collector=%s service=%s",
        type(recent_status).__name__,
        deviceid,
        monitorname,
        svcname,
    )
    return True


def _delete_config(key, store, log):
    if key in store:
        store.remove(key)
        log.info(
            "removed previously built configuration  "
            "device=%s collector=%s service=%s",
            key.device,
            key.monitor,
            key.service,
        )
    # Ensure all statuses for this key are deleted.
    store.clear_status(key)


def _job_is_old(status, submitted, now, device, log):
    if submitted is None or status is None:
        # job is not old (default state)
        return False
    limit = DeviceProperties(device).pending_timeout
    if submitted < (now - limit):
        log.warn(
            "skipped this job because it's too old  "
            "device=%s collector=%s service=%s submitted=%f %s=%s",
            status.key.device,
            status.key.monitor,
            status.key.service,
            submitted,
            Constants.device_pending_timeout_id,
            limit,
        )
        return True
    return False


def _getStore():
    client = getRedisClient(url=getRedisUrl())
    return createObject("deviceconfigcache-store", client)
