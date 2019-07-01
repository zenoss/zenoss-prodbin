##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from __future__ import absolute_import

from unittest import TestCase

from ..DataMaps import RelationshipMap, ObjectMap


class TestRelationshipMap(TestCase):

    def test_objectmaps_get_plugin_name_attr(t):
        om1 = ObjectMap({'id': 'eth0'})
        om2 = ObjectMap({'id': 'eth0'})
        om3 = ObjectMap({'id': 'eth0'})
        objmaps = [om1, om2, om3, ]

        relmap = RelationshipMap(
            relname="interfaces",
            modname="Products.ZenModel.IpInterface",
            plugin_name='test.plugin',
            objmaps=objmaps,
        )

        t.assertEqual(relmap.plugin_name, 'test.plugin')
        t.assertEqual(len(relmap.maps), 3)
        t.assertEqual(relmap.maps[0].plugin_name, 'test.plugin')
        t.assertEqual(relmap.maps[1].plugin_name, 'test.plugin')
        t.assertEqual(relmap.maps[2].plugin_name, 'test.plugin')

    def test_appended_objectmaps_get_plugin_name(t):
        om1 = ObjectMap({'id': 'eth0'})

        relmap = RelationshipMap(
            relname="interfaces",
            modname="Products.ZenModel.IpInterface",
            plugin_name='test.plugin',
        )
        relmap.append(om1)

        t.assertEqual(relmap.plugin_name, 'test.plugin')
        t.assertEqual(relmap.maps[0].plugin_name, 'test.plugin')
        t.assertEqual(om1.plugin_name, 'test.plugin')

    def test_extended_objectmaps_get_plugin_name(t):
        om1 = ObjectMap({'id': 'eth0'})
        om2 = ObjectMap({'id': 'eth0'})
        om3 = ObjectMap({'id': 'eth0'})
        objmaps = [om1, om2, om3, ]

        relmap = RelationshipMap(
            relname="interfaces",
            modname="Products.ZenModel.IpInterface",
            plugin_name='test.plugin',
        )
        relmap.extend(objmaps)

        t.assertEqual(relmap.plugin_name, 'test.plugin')
        t.assertEqual(len(relmap.maps), 3)
        t.assertEqual(relmap.maps[0].plugin_name, 'test.plugin')
        t.assertEqual(om1.plugin_name, 'test.plugin')
        t.assertEqual(relmap.maps[1].plugin_name, 'test.plugin')
        t.assertEqual(om2.plugin_name, 'test.plugin')
        t.assertEqual(relmap.maps[2].plugin_name, 'test.plugin')
        t.assertEqual(om3.plugin_name, 'test.plugin')
