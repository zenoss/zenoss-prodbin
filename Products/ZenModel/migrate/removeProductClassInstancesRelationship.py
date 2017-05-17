##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Migrate

#from zope.event import notify
#from Products.Zuul.catalog.events import IndexingEvent

from Products.ZenRelations.ToOneRelationship import ToOneRelationship
from Products.ZenRelations.ToManyRelationship import ToManyRelationship

class RemoveProductClassInstancesRelationship(Migrate.Step):

    version = Migrate.Version(110, 0, 0)

    INSTANCES_ATTR = "instances"

    def cutover(self, dmd):
        for manufacturer in dmd.Manufacturers.values():
            if hasattr(manufacturer, "products"):
                for product in manufacturer.products():
                    if product.get("instances") and isinstance(product.instances, ToManyRelationship):
                        instances = product.instances()
                        product.instances.removeRelation()
                        product._delObject("instances")
                        for instance in instances:
                            if instance.get("productClass") and isinstance(instance.productClass, ToOneRelationship):
                                product.productClass.removeRelation()
                                instance._delObject("productClass")
                            instance.setProductClass(product) # this should raise the indexing event

RemoveProductClassInstancesRelationship()