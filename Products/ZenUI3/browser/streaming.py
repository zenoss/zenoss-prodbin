from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.ZenUtils.Utils import is_browser_connection_open

LINE = """
<div class="streaming-line %(lineclass)s">
%(data)s
</div>
"""

class StreamClosed(Exception):
    """
    The browser has closed the connection.
    """


class StreamingView(BrowserView):

    tpl = ViewPageTemplateFile('streaming.pt')

    def __init__(self, context, request):
        super(StreamingView, self).__init__(context, request)
        self._stream = self.request.response
        self._lineno = 0

    def __call__(self):
        header, footer = str(self.tpl()).split('*****CONTENT_TOKEN*****')
        self._stream.write(header)
        try:
            try:
                self.stream()
            except StreamClosed:
                return
        finally:
            self._stream.write(footer)

    def write(self, data=''):
        if not is_browser_connection_open(self.request):
            raise StreamClosed('The browser has closed the connection.')
        html = LINE % {
            'lineclass': self._lineno % 2 and 'odd' or 'even',
            'data': data
        }
        self._stream.write(html)
        self._lineno += 1


class TestStream(StreamingView):
    def stream(self):
        import time
        for i in range(100):
            self.write(i)
            time.sleep(0.5)

