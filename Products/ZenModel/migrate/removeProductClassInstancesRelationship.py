##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Migrate

from zope.event import notify

from Products.ZenModel.Manufacturer import Manufacturer
from Products.ZenRelations.ToOneRelationship import ToOneRelationship
from Products.ZenRelations.ToManyRelationship import ToManyRelationship
from Products.Zuul.catalog.events import IndexingEvent
from Products.Zuul.utils import safe_hasattr as hasattr


class RemoveProductClassInstancesRelationship(Migrate.Step):

    version = Migrate.Version(112, 0, 0)

    def cutover(self, dmd):
        for manufacturer in dmd.Manufacturers.values():
            if isinstance(manufacturer, Manufacturer) and hasattr(manufacturer, "products"):
                for product in manufacturer.products():
                    if product.get("instances") and isinstance(product.instances, ToManyRelationship):
                        instances = product.instances()
                        product._delOb("instances")
                        for instance in instances:
                            if instance.get("productClass") and isinstance(instance.productClass, ToOneRelationship):
                                instance._delOb("productClass")
                                instance.setProductClass(product)
                                # reindex the whole object bc OS and SW were not being indexed
                                notify(IndexingEvent(instance))

RemoveProductClassInstancesRelationship()