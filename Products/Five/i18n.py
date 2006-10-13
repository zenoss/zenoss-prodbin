##############################################################################
#
# Copyright (c) 2005 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Mimick Zope3 i18n machinery for Zope 2

$Id: i18n.py 61063 2005-10-31 17:15:42Z philikon $
"""
from Acquisition import aq_acquire
from zope.interface import implements
from zope.i18n import interpolate
from zope.i18n.interfaces import ITranslationDomain, IUserPreferredLanguages
from zope.i18nmessageid import MessageID
from zope.app import zapi
from zope.publisher.browser import BrowserLanguages

from Products.PageTemplates import GlobalTranslationService as GTS

class FiveTranslationService:
    """Translation service that delegates to ``zope.i18n`` machinery.
    """
    # this is mostly a copy of zope.i18n.translate, with modifications
    # regarding fallback and Zope 2 compatability
    def translate(self, domain, msgid, mapping=None,
                  context=None, target_language=None, default=None):
        if isinstance(msgid, MessageID):
            domain = msgid.domain
            default = msgid.default
            mapping = msgid.mapping

        util = zapi.queryUtility(ITranslationDomain, domain)

        if util is None:
            # fallback to translation service that was registered,
            # DummyTranslationService the worst
            ts = _fallback_translation_service
            return ts.translate(domain, msgid, mapping=mapping, context=context,
                                target_language=target_language, default=default)

        # in Zope3, context is adapted to IUserPreferredLanguages,
        # which means context should be the request in this case.
        if context is not None:
            context = aq_acquire(context, 'REQUEST', None)
        return util.translate(msgid, mapping=mapping, context=context,
                              target_language=target_language, default=default)

class LocalizerLanguages(object):
    """Languages adapter that chooses languages according to Localizer
    settings."""
    implements(IUserPreferredLanguages)

    def __init__(self, context):
        self.context = context

    def getPreferredLanguages(self):
        accept_language = self.context.AcceptLanguage
        langs = []
        for lang, node in accept_language.children.items():
            langs.append((node.get_quality(), lang))
            langs.extend([(n.get_quality(), l) for l, n
                          in node.children.items()])
        langs.sort()
        langs.reverse()
        langs = [l for q, l in langs]
        if '' in langs:
            langs.remove('')
        return langs

class PTSLanguages(object):
    """Languages adapter that chooses languages like
    PlacelessTranslationService."""
    implements(IUserPreferredLanguages)

    def __init__(self, context):
        self.context = context

    def getPreferredLanguages(self):
        from Products.PlacelessTranslationService.Negotiator import getLangPrefs
        return getLangPrefs(self.context)

# these are needed for the monkey
_fallback_translation_service = GTS.DummyTranslationService()
fiveTranslationService = FiveTranslationService()

def getGlobalTranslationService():
    return fiveTranslationService

def setGlobalTranslationService(newservice):
    global _fallback_translation_service
    oldservice, _fallback_translation_service = \
        _fallback_translation_service, newservice
    return oldservice

def monkey():
    # get the services that has been registered so far and plug in our
    # new one
    global _fallback_translation_service
    _fallback_translation_service = \
        GTS.setGlobalTranslationService(fiveTranslationService)

    # now override the getter/setter so that noone else can mangle
    # with it anymore
    GTS.getGlobalTranslationService = getGlobalTranslationService
    GTS.setGlobalTranslationService = setGlobalTranslationService
