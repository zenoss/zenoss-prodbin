from zope.interface import Interface, Attribute

class IInfo(Interface):
    id = Attribute("Identifier of the represented object (usually path)")
    name = Attribute("Name of the represented object")

