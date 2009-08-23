import zope.interface
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from Products.Five.viewlet import viewlet

from interfaces import INavigationItem
from manager import SecondaryNavigationManager

class PrimaryNavigationMenuItem(viewlet.ViewletBase):
    zope.interface.implements(INavigationItem)

    template = ViewPageTemplateFile('nav_item.pt')

    url = ''
    active_class = 'active'
    inactive_class = 'inactive'

    @property
    def title(self):
        return self.__name__

    @property
    def selected(self):
        requestURL = self.request.getURL()
        if requestURL.endswith(self.url):
            return True
        sec = SecondaryNavigationManager(self.context, self.request,
                                         self.__parent__)
        if sec:
            for v in sec.getViewletsByParentName(self.__name__):
                if requestURL.endswith(v.url):
                    return True
        return False

    @property
    def css(self):
        if self.selected:
            return self.active_class
        else:
            return self.inactive_class

    def render(self):
        """
        Render the menu item into html
        """
        return self.template()


class SecondaryNavigationMenuItem(PrimaryNavigationMenuItem):
    zope.interface.implements(INavigationItem)

    parentItem = ""

    @property
    def selected(self):
        requestURL = self.request.getURL()
        if requestURL.endswith(self.url):
            return True
        return False


