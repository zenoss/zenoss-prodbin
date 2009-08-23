import zope.interface
from Products.Five.viewlet.viewlet import ViewletBase
from Products.Five.viewlet.manager import ViewletManagerBase

from interfaces import IJavaScriptSnippetManager, IJavaScriptSnippet

SCRIPT_TAG_TEMPLATE = """
<script type="text/javascript">
%s
</script>
"""

class JavaScriptSnippetManager(ViewletManagerBase):

    zope.interface.implements(IJavaScriptSnippetManager)

    def render(self):
        raw_js = '\n'.join([v.render() for v in self.viewlets])
        return SCRIPT_TAG_TEMPLATE % raw_js


class JavaScriptSnippet(ViewletBase):

    zope.interface.implements(IJavaScriptSnippet)

    def snippet(self):
        raise NotImplementedError("Subclasses must implement their own "
                                  "snippet method.")
    def render(self):
        return self.snippet()
