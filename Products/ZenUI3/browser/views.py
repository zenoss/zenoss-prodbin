##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.ZenUtils.guid.interfaces import IGUIDManager
from urllib import unquote


class FileUpload(BrowserView):
    """
    Renders a file upload in an iframe and asks the context to handle the results
    """

    template = ViewPageTemplateFile('./templates/formUpload.pt')

    def __call__(self, *args, **kwargs):
        """
        If we are in postback (submit is present) then we save the file.
        """
        if self.isPostBack:
            if self.request.upload.filename:
                self.context.handleUploadedFile(self.request)

        return self.template()

    @property
    def isPostBack(self):
        return self.request.get('submit')

class Robots(BrowserView):
    """
    Returns a robots.txt
    """

    def __call__(self, *args, **kwargs):
        """
        Return the robots.txt in the resource dir
        """
        import os.path
        with open(os.path.dirname(__file__) +'/resources/txt/robots.txt') as f:
            return f.read()


class GotoRedirect(BrowserView):
    """
    Given a guid in the url request redirect to the correct page
    """

    def __call__(self, *args, **kwargs):
        """
        Takes a guid in the request and redirects the browser to the
        object's url
        """
        manager = IGUIDManager(self.context)
        request = self.request
        response = self.request.response
        obj = None
        guid = request.get('guid', None)
        if not guid:
            return response.write("The guid paramater is required")

        # they passed in a uid instead of a guid
        try:
            if guid.startswith("/zport/dmd/"):
                obj = self.context.unrestrictedTraverse(unquote(guid))
            else:
                obj = manager.getObject(guid)
        except KeyError:
            pass

        if not obj:
            return response.write("Could not look up guid %s" % guid)

        path = obj.absolute_url_path()
        return response.redirect(path)
