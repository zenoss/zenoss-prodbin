#! /usr/bin/env python

import mimetypes
from webob import Request, Response
from wsgiref import simple_server

from modules import directstore

class TestApp(object):

    directRouters = dict(directstore=directstore.CrudService())

    def __call__(self, environ, startResponse):
        self.request = Request(environ)
        self.response = Response()
        if self.request.method.lower() == 'get':
            self.doGet()
        elif self.request.method.lower() == 'post':
            self.doPost()
        return self.response(environ, startResponse)
        
    def doGet(self):
        filename = self.request.path.lstrip('/')
        type, encoding = mimetypes.guess_type(filename)
        self.response.content_type = type or 'application/octet-stream'
        file = open(filename)
        try:
            self.response.body = file.read()
        finally:
            file.close()
            
    def doPost(self):
        self.response.content_type = 'application/json'
        directRouter = self.directRouters[self.request.path_info_peek()]
        self.response.body = directRouter(self.request.body)

def createServer(port=7999):
    print "Listening on %s" % port
    return simple_server.make_server('127.0.0.1', port, TestApp())
    
def main():
    server = createServer()
    server.serve_forever()

if __name__ == '__main__':
    main()
