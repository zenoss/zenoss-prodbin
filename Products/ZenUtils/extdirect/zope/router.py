from Products.ZenUtils.extdirect.router import DirectRouter

class ZopeDirectRouter(DirectRouter):
    def __call__(self):
        try:
            # Zope 3
            body = self.request.bodyStream.getCacheStream().getvalue()
        except AttributeError:
            # Zope 2
            body = self.request.get('BODY')
        self.request.response.setHeader('Content-Type', 'application/json')
        return super(ZopeDirectRouter, self).__call__(body)
