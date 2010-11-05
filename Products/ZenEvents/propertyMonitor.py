class PropertyMonitor(type):
    """Utility metaclass for defining monitored properties in a Python object.
       Target class must define a class attribute 'fields' containing the names 
       of the properties to be monitored as a space-delimited list.  This 
       metaclass will:
        - augment the __init__ method to define backup 'xxx_' attributes for 
          each 'xxx' field name, and add an internal _changed dict for tracking 
          and reporting changes
        - add set/get property functions for each 'xxx' attribute
        - add 'changed' property, a boolean flag indicating if any monitored 
          property has been changed
        - add 'get_changes' method to report list of property-value tuples
          of changes
        - add 'mark' method to reset change tracking, so that an object can be 
          initialized using various startup methods, and then the log of 
          property changes can be cleared prior to starting change-monitoring 
          portion of the program
    """
    def __init__(cls, name, bases, attrs):
        if "fields" in attrs:
            fields = attrs['fields'].split()
            cls.add_monitor_attribute_properties(fields)
        else:
            fields = []
        if "readonly_fields" in attrs:
            readonly_attrs = attrs['readonly_fields'].split()
            cls.add_readonly_properties(readonly_attrs)
        else:
            readonly_attrs = []

        if "compatibility_map" in attrs:
            compatmap = cls.compatibility_map
            rw_aliases = [(v,k) for k,v in compatmap.items() if v in fields]
            if rw_aliases:
                cls.add_monitor_attribute_properties(*zip(*rw_aliases))
            ro_aliases = [(v,k) for k,v in compatmap.items() if v in readonly_attrs]
            if ro_aliases:
                cls.add_readonly_properties(*zip(*ro_aliases))
            
        cls.add_monitor_admin_functions()
        cls.wrap_init(fields + readonly_attrs)
        super(PropertyMonitor, cls).__init__(name, bases, attrs)

    def wrap_init(cls, attribs):
        # wrap __init__ with additional initialization code:
        # - define 'xxx_' attributes for each 'xxx' field, and initialize to None
        # - initialize any attributes given in **kwargs
        # - add '_changed' dict for tracking changes
        setattr(cls, '__orig__init__', getattr(cls, '__init__', None))
        def __new_init__(self, *args, **kwargs):
            if self.__orig__init__ is not None:
                self.__orig__init__(*args)
            # initialize all attributes
            self.__dict__.update(dict((f+'_', None) for f in attribs))
            
            # copy supplied attribute values from named args passed to __init__
            self.__dict__.update(dict((k+'_', v) for k,v in kwargs.items() 
                                                if k in attribs))
            # initialize change status logging attributes
            self._changed = {}
            self._frozen = False
        setattr(cls, '__init__', __new_init__)

    def add_monitor_attribute_properties(cls, attrlist, aliases=None):
        # utility method for defining properties
        # - getter for attribute 'xxx' returns value of 'xxx_'
        # - setter for attribute 'xxx' sets value of 'xxx_' and records change
        #    to _changed
        if not aliases:
            aliases = attrlist
        def makePropertyFor(attr, doc=""):
            def propget(self):
                #~ print "get value for", attr
                return getattr(self,attr+'_')
            def propset(self,v):
                if getattr(self,attr+'_') != v:
                    #~ print "set",attr,"to",str(v)
                    self._changed[attr] = v
                    setattr(self,attr+'_',v)
            return property(propget, propset,doc=doc)
        
        # define get/set properties for each attribute in fields
        for (f,a) in zip(attrlist,aliases):
            #~ print "define readwrite property for", f, ("aliased by " + a if a != f else "")
            if a != f:
                doc = "Deprecated: use L{%s}" % f
            else:
                doc = ""
            setattr(cls, a, makePropertyFor(f, doc))

    def add_readonly_properties(cls, attrlist, aliases=None):
        # utility method for defining properties
        # - getter for attribute 'xxx' returns value of 'xxx_'
        if not aliases:
            aliases = attrlist
        def makePropertyFor(attr, doc=""):
            def propget(self):
                #~ print "get value for", attr
                return getattr(self,attr+'_')
            def propset(self,v):
                if not self._frozen:
                    setattr(self,attr+'_',v)
            return property(propget,propset,doc=doc)
        
        # define get/set properties for each attribute in fields
        for (f,a) in zip(attrlist,aliases):
            #~ print "define readonly property for", f, ("aliased by " + a if a != f else "")
            if a != f:
                doc = "Deprecated: use L{%s}" % f
            else:
                doc = ""
            setattr(cls, a, makePropertyFor(f, doc))

    def add_monitor_admin_functions(cls):
        # add boolean function that reports if any monitored attributes have changed
        def changed_fn(self):
            return bool(self._changed)
        setattr(cls, 'changed', property(changed_fn, doc="Returns True if any monitored attributes have changed"))
        
        # add function to extract the recorded changes as a list of attribute-value tuples
        def get_changes_fn(self):
            "Get list of changed attributes and their new values"
            return self._changed
        setattr(cls, 'get_changes', get_changes_fn)

        # add function to reset any recorded changes - call this after initializing
        # the object
        def mark_fn(self):
            "Reset change monitor"
            self._changed = {}
        setattr(cls, 'mark', mark_fn)

        # add function to freeze all readonly attributes
        # (or unfreeze if freezeflag is False)
        def freeze_fn(self, freezeflag=True):
            "Freeze all readonly attributes"
            self._frozen = freezeflag
        setattr(cls, 'freeze', freeze_fn)

        def updateFromDict_fn(self, dd):
            for k,v in dd.items():
                setattr(self, k, v)
        setattr(cls, 'updateFromDict', updateFromDict_fn)



