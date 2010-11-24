from zope.interface import Interface
from zope.configuration.fields import GlobalObject

class IEventPluginDirective(Interface):
    """
    Registers an event plugin as a named utility.
    """
    plugin = GlobalObject(
        title=u"Plugin",
        description=u"The class of the plugin to register"
    )
