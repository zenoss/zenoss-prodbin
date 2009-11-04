from Products.Five.browser import BrowserView

class MainPageRedirect(BrowserView):
    def __call__(self):
        self.request.response.redirect('/zport/dmd/dashboard')
