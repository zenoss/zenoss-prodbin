##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


def initialize(registrar):
    from .RelationshipManager import (
        addRelationshipManager,
        manage_addRelationshipManager,
        RelationshipManager,
    )
    from .ToManyContRelationship import (
        addToManyContRelationship,
        manage_addToManyContRelationship,
        ToManyContRelationship,
    )
    from .ToManyRelationship import (
        addToManyRelationship,
        manage_addToManyRelationship,
        ToManyRelationship,
    )
    from .ToOneRelationship import (
        addToOneRelationship,
        manage_addToOneRelationship,
        ToOneRelationship,
    )

    registrar.registerClass(
        RelationshipManager,
        constructors=(addRelationshipManager, manage_addRelationshipManager),
    )
    registrar.registerClass(
        ToOneRelationship,
        constructors=(addToOneRelationship, manage_addToOneRelationship),
        icon="www/ToOneRelationship_icon.gif",
    )
    registrar.registerClass(
        ToManyRelationship,
        constructors=(addToManyRelationship, manage_addToManyRelationship),
        icon="www/ToManyRelationship_icon.gif",
    )
    registrar.registerClass(
        ToManyContRelationship,
        constructors=(
            addToManyContRelationship,
            manage_addToManyContRelationship,
        ),
        icon="www/ToManyContRelationship_icon.gif",
    )


def registerDescriptors(event):
    """
    IZopeApplicationOpenedEvent handler which registers property descriptors.
    """
    zport = getattr(event.app, "zport", None)
    # zport may not exist if we are using zenbuild to initialize the database
    if zport:
        from logging import getLogger
        from .ZenPropertyManager import setDescriptors

        log = getLogger("zen.{}".format(__name__.split(".")[-1].lower()))
        try:
            setDescriptors(zport.dmd)
        except Exception as e:
            args = (e.__class__.__name__, e)
            log.info("Unable to set property descriptors: %s: %s", *args)
