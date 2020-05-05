##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

# Provides a version of ApplyDataMap that can be run on a collector, and
# operates against a Mapper instance rather than ZODB.


import logging
from Products.DataCollector.plugins.DataMaps import RelationshipMap, ObjectMap

from Products.ZenNub.adapters import METHOD_MAP, ZDevice, ZDeviceComponent

log = logging.getLogger("zen.applydatamapper")


class ApplyDataMapper(object):

    def __init__(self, mapper, deviceModel):
        self.mapper = mapper
        self.deviceModel = deviceModel

    def applyDataMap(self, base_id, datamap):
        changed = False

        if isinstance(datamap, RelationshipMap):
            changed = self.apply_relationshipmap(base_id, datamap)

        if isinstance(datamap, ObjectMap):
            changed = self.apply_objectmap(base_id, datamap)

        log.debug("applyDataMap complete.  changed=%s", changed)
        return changed

    def apply_objectmap(self, base_id, objmap):
        fields = ("compname", "relname", "modname", "id",)
        om = set([f for f in fields if hasattr(objmap, f) and getattr(objmap, f, "") != ""])
        _add = getattr(objmap, "_add", True)
        _remove = getattr(objmap, "_remove", False)

        # An ObjectMap with no compname or relname will be
        # applied to the device.
        #   ObjectMap({'rackSlot': 'near-the-top'}),
        if "compname" not in om and "relname" not in om:
            target = self.mapper.get(base_id)
            changed = self._update_properties(objmap, target, base_id)
            log.debug("ObjectMap [1] base_id=%s, compname=, relname=, target_id=%s",
                      base_id, base_id)
            self.mapper.update({base_id: target})

            return changed

        # An ObjectMap with a compname, but no relname will be
        # applied to a static object that's always a child of the
        # device. For example: hw and os.
        #   ObjectMap({
        #       'compname': 'hw',
        #       'totalMemory': 45097156608}),
        if "compname" in om and "relname" not in om:
            target_id = objmap.compname

            target = self.mapper.get(target_id, create_if_missing=_add)
            if target is None:
                # if _add=False, we don't create the object if it's not there.
                log.debug("ObjectMap [2] not creating target_id=%s (_add=False)", target_id)
                return None
            changed = self._update_properties(objmap, target, target_id)

            if objmap.compname in ("hw", "os"):
                obj_type = self.mapper.get_object_type(base_id)
                target["type"] = obj_type.get_link_type(objmap.compname).remote_class

            if not target["type"]:
                # temporary workaround- we'll have to fix this later.
                target["type"] = "unknown type"

            log.debug("ObjectMap [2] base_id=%s, compname=%s, relname=, target_id=%s",
                      base_id, objmap.compname, target_id)
            self.mapper.update({target_id: target})

            # Create link to target component if it's not already known
            device = self.mapper.get(base_id)
            if objmap.compname not in device["links"]:
                device["links"][objmap.compname].add(target_id)
                self.mapper.update({base_id: device})
                log.debug("  Added new component (%s) under %s (%s)", target_id, base_id, objmap.compname)

            return changed

        # A special _remove key can a be added to an ObjectMap's data
        # to cause the identified component to be deleted. If a
        # matching component is not found, nothing will happen. The
        # default value for the _remove key is False. There's no
        # reason to set anything other than relname, optionally
        # compname, and id within data when setting _remove to True.
        # Matching is performed by joining compname/relname/id to
        # create a relative path to the component to be removed.
        # ObjectMap({
        #     'id': 'widgetbag-x7',
        #     'relname': 'widgetbags',
        #     'modname': 'ZenPacks.example.PackName.WidgetBag',
        #     '_remove': True,
        #     }),
        if _remove:
            # NOTE: Since the ID is required anyway, we're going to ignore
            # compname/relname as described above and just delete it by ID
            # instead.
            if "id" in om:
                log.debug("remove id=%s", objmap.id)
                self.mapper.remove(objmap.id)
                return True
            else:
                log.error("Unable to process _remove directive without id")
                return False

        # An ObjectMap with an id, relname, and modname will be
        # applied to a component of the device. The component's
        # properties will be updated if the component already exists,
        # and the the component will be created if it doesn't already
        # exist.
        #   ObjectMap({
        #       'id': 'widgetbag-x7',
        #       'relname': 'widgetbags',
        #       'modname': 'ZenPacks.example.PackName.WidgetBag',
        #       'shape': 'squiggle',
        #   }),
        if "id" in om and "relname" in om and "modname" in om:
            target_id = objmap.id
            target = self.mapper.get(target_id, create_if_missing=_add)
            if target is None:
                # if _add=False, we don't create the object if it's not there.
                log.debug("ObjectMap [3] not creating target_id=%s (_add=False)", target_id)
                return False

            log.debug("ObjectMap [3] base_id=%s, compname=%s, relname=%s, target_id=%s",
                      base_id, objmap.compname, objmap.relname, target_id)

            changed = self._update_properties(objmap, target, target_id)
            self.mapper.update({target_id: target})

            # Link from device to this component if it's new.
            device = self.mapper.get(base_id)
            if target_id not in device["links"][objmap.relname]:
                log.debug("  Added new component (%s) under %s (%s)", target_id, base_id, objmap.relname)
                device["links"][objmap.relname].add(target_id)
                self.mapper.update({base_id: device})

            return changed

        # Components nested beneath other components can be updated
        # by using both compname to identify the relative path to the
        # parent component from its device, and relname to identify
        # the relationship on the parent component.
        #    ObjectMap({
        #       'id': 'widget-z9',
        #       'compname': 'widgetbags/widgetbag-x7',
        #       'relname': 'widgets',
        #       'modname': 'ZenPacks.example.PackName.Widget',
        #       'color': 'magenta',
        #       })
        if "compname" in om and "relname" in om:
            target_id = self._traverse_compname(base_id, objmap.compname)
            # note: technically this is just the last element of compname,
            # but actually traversing it will allow us to detect if it's not
            # valid.
            if target_id is None:
                log.error("Unable to locate compname %s on %s", objmap.compname, base_id)
                return None

            target = self.mapper.get(target_id, create_if_missing=_add)
            changed = self._update_properties(objmap, target, target_id)

            log.debug("ObjectMap [4] base_id=%s, compname=%s, relname=%s, target_id=%s",
                      base_id, objmap.compname, objmap.relname, target_id)

            self.mapper.update({target_id: target})

            return changed

    def _update_properties(self, objmap, target, target_id):
        changed = False

        if objmap.modname is not None and objmap.modname != "" and target["type"] != objmap.modname:
            target["type"] = objmap.modname
            changed = True

        if hasattr(objmap, "title"):
            target["title"] = objmap.title

        for k, v in objmap.iteritems():
            if k.startswith("set"):
                continue
            if k in ['parentId', 'relname', 'id', '_add', '_remove', 'title']:
                continue

            if k not in target["properties"] or target["properties"][k] != v:
                target["properties"][k] = v
                changed = True

        if target["type"] in METHOD_MAP:
            setters_to_call = set()
            for k, v in objmap.iteritems():
                if k.startswith("set") and k in METHOD_MAP[target["type"]]["method"]:
                    # If the setter has been allowed by METHOD_MAP, invoke it.
                    setters_to_call.add(k)

            isDevice = self.mapper.get_object_type(target_id).device
            if isDevice:
                adapted = ZDevice(self.deviceModel, target_id, target)
            else:
                adapted = ZDeviceComponent(self.deviceModel, target_id, target)

            for k, v in objmap.iteritems():
                if k in setters_to_call:
                    log.debug("Invoking setter %s on %s", k, target_id)
                    getattr(adapted, k)(v)


        return changed

    def apply_relationshipmap(self, base_id, relmap):
        target_id = base_id

        # A RelationshipMap is used to update all of the components
        # in the specified relationship. A RelationshipMap must
        # supply an ObjectMap for each component in the relationship.
        #   RelationshipMap(
        #        relname='widgetbags',
        #        modname='ZenPacks.zenoss.PackName.WidgetBag',
        #        objmaps=[
        #            ObjectMap({'id': 'widgetbag-x7', 'shape': 'square'}),
        #            ObjectMap({'id': 'widgetbag-y8', 'shape': 'hole'}),
        #            ]),

        # As with ObjectMaps, compname can be used to update
        # relationships on components rather than relationships on
        # the device. These are often referred to as nested
        # components, or nested relationships.
        #   RelationshipMap(
        #       compname='widgetbags/widgetbag-x7',
        #       relname='widgets',
        #       modname='ZenPacks.zenoss.PackName.Widget',
        #       objmaps=[
        #           ObjectMap({'id': 'widget-z9', 'color': 'magenta'}),
        #           ObjectMap({'id': 'widget-aa10', 'color': 'cyan'}),
        #           ]),

        # (this doesn't appear to be documented in the pythoncollector docs,
        # but i see it in the ADM code- looks like you can specify a parentId
        # directly, rather than using compname)
        parentId = getattr(relmap, "parentId", None)
        if parentId is not None:
            target_id = parentId

        compname = getattr(relmap, "compname", None)
        if compname is not None:
            target_id = self._traverse_compname(base_id, relmap.compname)

        # Any existing components that don't have a matching (by id)
        # ObjectMap within the RelationshipMap will be removed when
        # the RelationshipMap is applied.
        #
        # All of the components in a relationship will be removed if
        # a RelationshipMap with an empty list of ObjectMaps
        # (objmaps) is supplied.

        target = self.mapper.get(target_id)
        if target is None:
            log.error("When applying relationship map (compname=%s), target was not found.", compname)
            return False

        log.debug("RelationshipMap [1] base_id=%s, compname=%s, relname=%s, target_id=%s",
                  base_id, compname, relmap.relname, target_id)

        current_objids = target["links"][relmap.relname]
        new_objids = set([om.id for om in relmap])

        rmodname = getattr(relmap, "modname", None)
        changed = False
        for objmap in relmap:
            # objmaps inherit the modname from the relmap if they haven't
            # specified one.
            omodname = getattr(objmap, "modname", None)
            if rmodname is not None and omodname is None:
                objmap.modname = relmap.modname

            objmap.relname = relmap.relname

            if self.apply_objectmap(target_id, objmap):
                changed = True

        # Remove any existing objects that were't included in the relationshipmap
        for objid in current_objids:
            if objid not in new_objids:
                self.mapper.remove(objid)
                changed = True

        return changed

    def _traverse_compname(self, base_id, base_compname, current_id=None, compname=None):
        if current_id is None:
            current_id = base_id
            compname = base_compname

        if compname == '':
            return current_id

        current_component = self.mapper.get(current_id)
        if current_component is None:
            log.error("While traversing %s:%s, object %s was not found",
                      current_id, compname, current_id)

            return None

        if '/' in compname:
            next_element, compname = compname.split('/', 1)
        else:
            next_element, compname = compname, ''

        object_type = self.mapper.get_object_type(current_id)
        if object_type.device and next_element in ('hw', 'os', ):
            # Directly contained object
            next_id = next_element
            self._autovivify_direct(current_id, next_element, next_element)

        elif next_element in current_component['links']:
            linkname = next_element
            # Normal containment- relationship name, then id
            if '/' in compname:
                next_id, compname = compname.split('/', 1)
            else:
                next_id, compname = compname, ''

            if linkname not in current_component['links']:
                log.error("While traversing %s:%s at %s no %s related objects were found",
                          base_id, base_compname, current_id, linkname)
                return None

            if next_id not in current_component['links'][linkname]:
                if compname == '':
                    # If this is the last element in the compname, it's ok if it
                    # doesn't exist.
                    return next_id

                log.error("While traversing %s:%s at %s, object %s was not found in the %s links",
                          base_id, base_compname, current_id, next_id, linkname)
                return None

        return self._traverse_compname(base_id, base_compname, next_id, compname)

    def _autovivify_direct(self, parent_id, relname, new_id):
        # For directly contained objects (os, hw), it is sometimes necessary
        # to create them implicitly.

        parent = self.mapper.get(parent_id)
        if new_id in parent['links'].get(relname, set()):
            # already exists
            return None

        obj_type = self.mapper.get_object_type(parent_id)
        link_type = obj_type.get_link_type(relname)

        datum = self.mapper.get(new_id, create_if_missing=True)
        datum['type'] = link_type.remote_class
        self.mapper.update({new_id: datum})

        parent["links"][relname].add(new_id)
        self.mapper.update({parent_id: parent})

        log.info("Auto-created %s (%s) component", new_id, datum['type'])
