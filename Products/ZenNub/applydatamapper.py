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


log = logging.getLogger("zen.applydatamapper")


class ApplyDataMapper(object):

    def __init__(self, mapper):
        self.mapper = mapper

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
            changed = self._update_properties(objmap, target)
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
            changed = self._update_properties(objmap, target)

            if objmap.compname == "hw":
                target["type"] = "Products.ZenModel.DeviceHW"
            if objmap.compname == "os":
                target["type"] = "Products.ZenModel.OperatingSystem"

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

            changed = self._update_properties(objmap, target)
            self.mapper.update({target_id: target})

            # Link from device to this component if it's new.
            device = self.mapper.get(base_id)
            if target_id not in device["links"][objmap.relname]:
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
            changed = self._update_properties(objmap, target)

            log.debug("ObjectMap [4] base_id=%s, compname=%s, relname=%s, target_id=%s",
                base_id, objmap.compname, objmap.relname, target_id)

            self.mapper.update({target_id: target})

            return changed

    def _update_properties(self, objmap, target):
        changed = False

        if objmap.modname is not None and objmap.modname != "" and target["type"] != objmap.modname:
            target["type"] = objmap.modname
            changed = True

        for k, v in objmap.iteritems():
            if k.startswith("set"):
                continue
            if k in ['parentId', 'relname', 'id', '_add', '_remove']:
                continue

            if k not in target["properties"] or target["properties"][k] != v:
                target["properties"][k] = v
                changed = True

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
            changed = changed or self.apply_objectmap(target_id, objmap)

        # Remove any existing objects that were't included in the relationshipmap
        for objid in current_objids:
            if objid not in new_objids:
                self.mapper.remove(objid)
                changed = True

        return changed



    def _traverse_compname(self, base_id, compname):
        if compname == '':
            return base_id

        path = compname.split("/")
        current_id = base_id

        while len(path):
            linkname = path.pop(0)
            try:
                next_id = path.pop(0)
            except Exception, e:
                next_id = None

            component = self.mapper.get(current_id)
            if component is None:
                log.error("While traversing %s:%s, object %s was not found",
                    base_id, compname, current_id)

                return None

            # A "to one" relationship, "os"
            if next_id is None:
                links = list(component["links"][linkname])
                if len(links) == 1:
                    return links[0]
                else:
                    log.error("While traversing %s:%s, no %s related objects were found" ,
                    base_id, compname, linkname)
                    return None

            # A "to many" relationship, "interfaces/interface1"
            if next_id not in component["links"][linkname]:
                log.error("While traversing %s:%s, object %s was not found in the %s links of %s",
                    base_id, compname, next_id, linkname, current_id)
                return None

            current_id = next_id

        return current_id



