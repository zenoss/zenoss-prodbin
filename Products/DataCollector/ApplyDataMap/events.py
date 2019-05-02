from zope.interface import implements
from zope.component.interfaces import Interface, Attribute


class IDatamapEvent(Interface):
    dmd = Attribute('a handle for dmd')  # pragma: no mutate
    objectmap = Attribute("an ObjectMap")  # pragma: no mutate
    target = Attribute(
        "The device or component the ObjectMap modifies"  # pragma: no mutate
    )


class IDatamapAddEvent(IDatamapEvent):
    pass


class IDatamapUpdateEvent(IDatamapEvent):
    pass


class DatamapAddEvent(object):
    implements(IDatamapAddEvent)

    def __init__(self, dmd, objectmap, target):
        self.dmd = dmd
        self.objectmap = objectmap
        self.target = target


class DatamapUpdateEvent(object):
    implements(IDatamapUpdateEvent)

    def __init__(self, dmd, objectmap, target):
        self.dmd = dmd
        self.objectmap = objectmap
        self.target = target
