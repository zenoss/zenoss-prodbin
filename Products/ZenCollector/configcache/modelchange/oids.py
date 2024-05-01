##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging

from zenoss.modelindex.model_index import CursorSearchParams
from zExceptions import NotFound
from zope.interface import implementer

from Products.ZenHub.interfaces import IInvalidationOid
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenRelations.RelationshipBase import IRelationship
from Products.Zuul.catalog.interfaces import IModelCatalogTool

log = logging.getLogger("zen.configcache.modelchange")


class BaseTransform(object):
    def __init__(self, entity):
        self._entity = entity


@implementer(IInvalidationOid)
class IdentityOidTransform(BaseTransform):
    """Identity transformation returns the OID that was given."""

    def transformOid(self, oid):
        log.debug(
            "[IdentityOidTransform]   entity=%s oid=%r", self._entity, oid
        )
        return oid


@implementer(IInvalidationOid)
class ComponentOidTransform(BaseTransform):
    """
    If the object has a relationship with a device, return the device's OID.
    """

    def transformOid(self, oid):
        funcs = (
            lambda: self._getdevice(self._entity),
            self._from_os,
            self._from_hw,
        )
        for fn in funcs:
            device = fn()
            if device:
                log.debug(
                    "[ComponentOidTransform] transformed oid to device  "
                    "entity=%s oid=%r device=%s",
                    self._entity,
                    oid,
                    device,
                )
                return device._p_oid
        log.debug(
            "[ComponentOidTransform] oid not transformed  entity=%s oid=%r",
            self._entity,
            oid,
        )
        return oid

    def _from_os(self):
        return self._getdevice(getattr(self._entity, "os", None))

    def _from_hw(self):
        return self._getdevice(getattr(self._entity, "hw", None))

    def _getdevice(self, entity):
        if entity is None:
            return
        if isinstance(entity, IRelationship):
            entity = entity()
        return getattr(entity, "device", lambda: None)()


@implementer(IInvalidationOid)
class DataPointToDevice(BaseTransform):
    """Return the device OIDs associated with an RRDDataPoint."""

    def transformOid(self, oid):
        ds = _getDataSource(self._entity)
        if not ds:
            return ()
        template = _getTemplate(ds.primaryAq())
        if not template:
            return ()
        dc = _getDeviceClass(template)
        if not dc:
            return ()
        log.debug(
            "[DataPointToDevice] return OIDs of devices associated "
            "with DataPoint  entity=%s ",
            self._entity,
        )
        return _getDevicesFromDeviceClass(dc)


@implementer(IInvalidationOid)
class DataSourceToDevice(BaseTransform):
    """Return the device OIDs associated with an RRDDataSource."""

    def transformOid(self, oid):
        template = _getTemplate(self._entity)
        if not template:
            return ()
        dc = _getDeviceClass(template)
        if not dc:
            return ()
        log.debug(
            "[DataSourceToDevice] return OIDs of devices associated "
            "with DataSource  entity=%s",
            self._entity,
        )
        return _getDevicesFromDeviceClass(dc)


@implementer(IInvalidationOid)
class TemplateToDevice(BaseTransform):
    """Return the device OIDs associated with an RRDTemplate."""

    def transformOid(self, oid):
        dc = _getDeviceClass(self._entity)
        if not dc:
            return ()
        log.debug(
            "[TemplateToDevice] return OIDs of devices associated "
            "with RRDTemplate  entity=%s ",
            self._entity,
        )
        return _getDevicesFromDeviceClass(dc)


@implementer(IInvalidationOid)
class DeviceClassToDevice(BaseTransform):
    """Return the device OIDs in the DeviceClass hierarchy."""

    def transformOid(self, oid):
        log.debug(
            "[DeviceClassToDevice] return OIDs of devices associated "
            "with DeviceClass  entity=%s ",
            self._entity,
        )
        return _getDevicesFromDeviceClass(self._entity)


@implementer(IInvalidationOid)
class ThresholdToDevice(BaseTransform):
    """Return the device OIDs in the DeviceClass hierarchy."""

    def transformOid(self, oid):
        log.debug(
            "[ThresholdToDevice] return OIDs of devices associated "
            "with Threshold  entity=%s ",
            self._entity,
        )
        obj = self._entity
        while not isinstance(obj, DeviceClass):
            try:
                obj = obj.getParentNode()
            except Exception:
                log.exception("unable to find device class  entity=%r", obj)
                return None
        return _getDevicesFromDeviceClass(obj)


def _getDataSource(dp):
    ds = dp.datasource()
    if ds is None:
        if log.isEnabledFor(logging.DEBUG):
            log.warn("no datasource relationship  datapoint=%s", dp)
        return None
    return ds.primaryAq()


def _getTemplate(ds):
    template = ds.rrdTemplate()
    if template is None:
        if log.isEnabledFor(logging.DEBUG):
            log.warn("no template relationship  datasource=%s", ds)
        return None
    return template.primaryAq()


def _getDeviceClass(template):
    dc = template.deviceClass()
    if dc is None:
        if log.isEnabledFor(logging.DEBUG):
            log.warn("no device class relationship  template=%s", template)
        return None
    return dc.primaryAq()


def _getDevicesFromDeviceClass(dc):
    tool = IModelCatalogTool(dc.dmd.Devices)
    query, _ = tool._build_query(
        types=("Products.ZenModel.Device.Device",),
        paths=("{}*".format("/".join(dc.getPhysicalPath())),),
    )
    params = CursorSearchParams(query)
    result = tool.model_catalog_client.cursor_search(params, dc.dmd)
    for brain in result.results:
        try:
            ob = brain.getObject()
            if ob:
                yield ob._p_oid
        except (NotFound, KeyError, AttributeError):
            pass
