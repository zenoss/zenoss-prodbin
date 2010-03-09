from Products.Zuul import getFacade
from Products.ZenUI3.browser.javascript import JavaScriptSrcViewlet

class IncludeSearchBox(JavaScriptSrcViewlet):
    
    path = "++resource++search/zenoss-search.js"

    def render(self):
        if not getFacade('search').noProvidersPresent():
            return super(IncludeSearchBox,self).render()
        else:
            return ''