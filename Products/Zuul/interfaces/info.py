from zope.interface import Attribute
from Products.Zuul.interfaces import IMarshallable

class IInfo(IMarshallable):
    id = Attribute("Identifier of the represented object (usually path)")
    name = Attribute("Name of the represented object")

