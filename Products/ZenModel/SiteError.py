#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""SiteError

SiteError consolidates code used to handle and report site errors.

$Id:$
"""

__version__ = "$Revision: $"[11:-2]

import smtplib

class SiteError:

    SMTP_HOST = 'mail.zenoss.com'
    ERRORS_ADDRESS = 'errors@zenoss.com'

    def cleanUrl(cls, errorUrl):
        ''' Strip protocol and domain from the url
        '''
        stripDomain = False
        if errorUrl.startswith('http://'):
            errorUrl = errorUrl[len('http://'):]
            stripDomain = True
        elif errorUrl.startswith('https://'):
            errorUrl = errorUrl[len('https://'):]
            stripDomain = True
        if stripDomain and '/' in errorUrl:
            errorUrl = errorUrl[errorUrl.find('/'):]
        return errorUrl
    cleanUrl = classmethod(cleanUrl)


    def createEmailHeader(cls, fromAddress, toAddress, subject):
        ''' Create the smnp header for an error email
        '''
        header = 'To: %s\nFrom: %s\nSubject: %s\n' % (
                    toAddress, fromAddress, subject)
        return header
    createEmailHeader = classmethod(createEmailHeader)

        
    def createReport(cls, errorType, errorValue, errorTrace, errorUrl, 
                        inHtml=True, contactName=None, contactEmail=None, 
                        comments=None):
        ''' Produce a summary of the given error details suitable for use
        in an error email (inHtml=false) or on a page (inHtml=true)
        '''
        # If not inHtml then strip html tags from the errorTrace
        if inHtml:
            linebreak = '<br />\n'
        else:
            linebreak = '\n'
            import re
            errorTrace = re.sub('<[^>]*>', '', errorTrace)
            errorTrace = re.sub('\r\n\r\n', '\r\n', errorTrace)
        msg = linebreak.join(['Type: %s' % errorType,
                                'Value: %s' % errorValue,
                                'URL: %s' % cls.cleanUrl(errorUrl),
                                '%s' % errorTrace,
                                'Contact name: %s' % (contactName or ''),
                                'Email address: %s' % (contactEmail or ''),
                                'Comments: %s' % (comments or '')])
        return msg
    createReport = classmethod(createReport)


    def sendErrorEmail(cls, errorType, errorValue, errorTrace, errorUrl,
                        contactName=None, contactEmail=None, comments=None):
        ''' Attempt to send an email to the zenoss errors email address
        with details of this error.
        Returns true if mail was sent, false otherwise.
        '''
        import socket
        fqdn = socket.getfqdn()
        fromAddress = 'errors@%s' % fqdn
        cleanUrl = cls.cleanUrl(errorUrl)
        subject = '%s: %s (%s)' % (errorType, errorValue, cleanUrl)
        header = cls.createEmailHeader(
                    fromAddress, cls.ERRORS_ADDRESS, subject)
        body = cls.createReport(errorType, errorValue, errorTrace, cleanUrl,
                                0, contactName, contactEmail, comments)
        mailSent = False
        server = smtplib.SMTP(cls.SMTP_HOST)
        try:
            server.sendmail(fromAddress, cls.ERRORS_ADDRESS, 
                            '%s\n\n%s' % (header, body))
            mailSent = True
        finally:
            server.quit()
        return mailSent
    sendErrorEmail = classmethod(sendErrorEmail)
    