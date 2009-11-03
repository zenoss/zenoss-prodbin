from zope.interface import Interface
from zope.configuration.fields import GlobalObject
from zope.schema import TextLine

class IDirectRouter(Interface):
    """
    Registers a name and a javascript viewlet for a DirectRouter subclass.
    """
    name = TextLine(
        title=u"Name",
        description=u"The name of the requested view.")

    for_ = GlobalObject(
        title=u"For Interface",
        description=u"The interface the directive is used for.",
        required=False)

    class_ = GlobalObject(
        title=u"Class",
        description=u"The DirectRouter subclass"
    )

    namespace = TextLine(
        title=u"Namespace",
        description=unicode("The JavaScript namespace under which the"
                            " remote methods should be available"),
        required=False
    )

    layer = TextLine(
        title=u"Layer",
        description=u"The layer",
        required=False
    )
