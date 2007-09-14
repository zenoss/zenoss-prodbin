#! /usr/bin/env python

import sys
import base64
import urllib2
from HTMLParser import HTMLParser
from urlparse import urlparse, urlunparse
import mimetypes
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.MIMEImage import MIMEImage

def sibling(url, path):
    parts = list(urlparse(url))
    parts[2] = '/'.join(parts[2].split('/')[:-1] + [path])
    return urlunparse(parts[0:3] + ['', '',''])

class Page(HTMLParser):
    def __init__(self, user, passwd):
        HTMLParser.__init__(self)
        self.user = user
        self.passwd = passwd
        self.html = []
        self.id = 0
        self.images = {}
        self.contentPane = 0

    def fetchImage(self, url):
        return self.slurp(url).read()

    def absolute(self, url):
        url = url.strip()
        if url.startswith('http:'):
            return url
        if url.startswith('/'):
            base = list(urlparse(self.base))
            base[2] = url
            return urlunparse(base[0:3] + ['', '',''])
        return sibling(self.base, url)

    def alter(self, attrs, name, function):
        result = []
        for a, v in attrs:
            if a.lower() == name:
                v = function(v)
            result.append( (a, v) )
        return result
        
    def updateSrc(self, attrs):
        def cache(v):
            if v not in self.images:
                self.id += 1
                v = self.absolute(v)
                self.images[v] = ('img%d.gif' % self.id, self.fetchImage(v))
            v, _ = self.images[v]
            return 'cid:%s' % v
        return self.alter(attrs, 'src', cache)
    
    def updateHref(self, attrs):
        return self.alter(attrs, 'href', self.absolute)

    def handle_starttag(self, tag, attrs):
        tag = tag.upper()
        if tag == 'IMG':
            attrs = self.updateSrc(attrs)
        if tag == 'A':
            attrs = self.updateHref(attrs)
        if tag == 'DIV':
            if ('id','contentPane') in attrs:
                self.contentPane = 1
            elif self.contentPane:
                self.contentPane += 1
        if self.contentPane:
            attrs = ' '.join([("%s=%s" % (a, repr(v))) for a, v in attrs])
            if attrs: attrs = ' ' + attrs
            self.html.append('<%s%s>' % (tag, attrs))

    def handle_endtag(self, tag):
        tag = tag.upper()
        if self.contentPane:
            self.html.append('</%s>' % tag.upper())
        if tag == 'DIV':
            if self.contentPane:
                self.contentPane -= 1

    def handle_data(self, data):
        if self.contentPane:
            self.html.append(data)

    def slurp(self, url):
        self.base = url.strip()
        req = urllib2.Request(url)
        encoded = base64.encodestring('%s:%s' % (self.user, self.passwd))[:-1]
        req.add_header("Authorization", "Basic %s" % encoded)
        return urllib2.urlopen(req)

    def fetch(self, url):
        self.feed(self.slurp(url).read())

    def mail(self):
        msg = MIMEMultipart('related')
        msg.preamble = 'This is a multi-part message in MIME format'
        txt = MIMEText(''.join(self.html), 'html')
        msg.attach(txt)
        for url, (name, img) in self.images.items():
            ctype, encoding = mimetypes.guess_type(url)
            if ctype == None:
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)
            img = MIMEImage(img, subtype)
            fname = url.rsplit('/', 1)[1]
            img.add_header('Content-ID', '<%s>' % name)
            # img.add_header('Content-Disposition', 'inline; filename="%s"' % fname)
            msg.attach(img)
        return msg

def main():
    url, user, passwd, smtpPasswd = sys.argv[1:5]
    page = Page(user, passwd)
    page.fetch(url)
    msg = page.mail()
    msg['Subject'] = 'This is a test'
    msg['From'] = 'ecn@swcomplete.com'
    msg['To'] = 'eric.newton@gmail.com'
    import smtplib
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login('eric.newton', smtpPasswd)
    server.sendmail('eric.newton@gmail.com', 'ecn@swcomplete.com', msg.as_string())
    server.quit()
    f = file('/home/ecn/Desktop/test.eml','wb')
    f.write(msg.as_string())
    f.close()

if __name__ == '__main__':
    main()
    sys.exit(0)

