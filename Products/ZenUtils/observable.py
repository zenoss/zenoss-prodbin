###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

"""
The observable module provides an interface and an optional mixin class that
provide an Observer pattern for attribute based change notifications of an 
object.

An object that is Observable (i.e. provides the IObservable interface) will
allow attribute observers, a.k.a. listeners, to be attached or detached for
specific attribute names. These observers will be notified whenever the 
specified attribute changes value.

Observers can be any Python object that is callable.

An example of using the observer pattern in your implementation is:


class MyObject(MyParentClass, ObservableMixin):
    def __init__(self):
        super(MyObject, self).__init__()
        self.name = "Super Duper Object"
        self.age = 42

    def doIt(self):
        self.name = "I changed my name!"
        self.age = 37

def ageListener(observable, attrName, oldValue, newValue):
    print "Age has been changed from %d to %d" % (oldValue, newValue)

foo = MyObject()
foo.attachAttributeObserver("age", ageListener)
foo.doIt()


This implementation will likely only work with new style classes that have been
properly implemented.
"""

import Globals
import zope.interface

class IObservable(zope.interface.Interface):
    """
    Classes that implement the IObservable interface agree to provide the
    Observer pattern for object attribute changes.
    """
    def attachAttributeObserver(self, name, observer):
        """
        Attaches an observer that will be notified when the specified attribute
        changes value.
        
        @param name the attribute name to observer
        @param observer the observer/listener to be notified
        @type observer callable
        """
        pass

    def detachAttributeObserver(self, name, observer):
        """
        Removes an observer from watching the specified attribute.

        @param name the attribute name to remove the observer from
        @param observer the observer/listener to be removed
        """
        pass

    def notifyAttributeChange(self, name, oldValue, newValue):
        """
        Notify all registered observers that an attribute has changed value.
        Register observers must be a Python callable and will receive the 
        following keyword arguments:
            observerable - a reference to the observed object
            attrName - the attribute name that has changed
            oldValue - the previous value
            newValue - the new value
            
        @param name the attribute name that has changed
        @param oldValue the old attribute value
        @param newValue the new attribute value
        """
        pass

class ObservableMixin(object):
    """
    A mixin class that provides an implementation of the IObservable interface
    for any new-style class to use. This implementation will provide
    notification for all attribute changes, except for the attributes used
    to track the registered observers themselves.
    """
    zope.interface.implements(IObservable)

    def __init__(self):
        super(ObservableMixin, self).__init__()
        self._observers = {}

    def attachAttributeObserver(self, name, observer):
        if not callable(observer):
            raise ValueError("observer must be callable")

        if not self._observers.has_key(name):
            self._observers[name] = []

        if observer not in self._observers[name]:
            self._observers[name].append(observer)

    def detachAttributeObserver(self, name, observer):
        try:
            self._observers[name].remove(observer)
        except KeyError, ValueError:
            pass

    def notifyAttributeChange(self, name, oldValue, newValue):
        # don't bother notifying if we don't have an _observers attribute
        # yet (during construction) 
        if hasattr(self, '_observers') and self._observers.has_key(name):
            for observer in self._observers[name]:
                observer(observable=self, 
                         attrName=name,
                         oldValue=oldValue,
                         newValue=newValue)

    def __setattr__(self, name, newValue):
        # override the __setattr__ method so that we can grab the previous
        # value and then notify all of the observers of the change
        oldValue = getattr(self, name, None)
        super(ObservableMixin, self).__setattr__(name, newValue)
        self.notifyAttributeChange(name, oldValue, newValue)
