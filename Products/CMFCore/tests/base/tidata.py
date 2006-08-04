ManageProperties = 'Manage properties'
ModifyPortalContent = 'Modify portal content'
View = 'View'

FTIDATA_ACTIONS = (
      { 'id' : 'Action Tests'
      , 'meta_type' : 'Dummy'
      , 'actions' : (
            { 'id':'view',
              'title': 'View',
              'action':'string:',
              'permissions':('View',),
              'category':'object',
              'visible':1 }
          , { 'name':'Edit',                    # Note: No ID passed
              'action':'string:${object_url}/foo_edit',
              'permissions':('Modify',),
              'category':'object',
              'visible':1 }
          , { 'name':'Object Properties',       # Note: No ID passed
              'action':'string:foo_properties',
              'permissions':('Modify',),
              'category':'object',
              'visible':1 }
          , { 'id':'slot',
              'action':'string:foo_slot',
              'category':'object',
              'visible':0 }
          )
      }
    ,
    )

FTIDATA_DUMMY = (
      { 'id' : 'Dummy Content'
      , 'title' : 'Dummy Content Title'
      , 'meta_type' : 'Dummy'
      , 'product' : 'FooProduct'
      , 'factory' : 'addFoo'
      , 'actions' : (
            { 'id': 'view',
              'title': 'View',
              'action':'string:view',
              'permissions':('View',) }
          , { 'id': 'view2',
              'title': 'View2',
              'action':'string:view2',
              'permissions':('View',) }
          , { 'id': 'edit',
              'title': 'Edit',
              'action':'string:edit',
              'permissions':('forbidden permission',) }
          )
      }
    ,
    )

FTIDATA_CMF13 = (
      { 'id' : 'Dummy Content 13'
      , 'meta_type' : 'Dummy'
      , 'description' : (
           'Dummy Content.')
      , 'icon' : 'dummy_icon.gif'
      , 'product' : 'FooProduct'
      , 'factory' : 'addFoo'
      , 'immediate_view' : 'metadata_edit_form'
      , 'actions' : (
            { 'id':'view',
              'name':'View',
              'action':'dummy_view',
              'permissions':(View,) }
          , { 'id':'edit',
              'name':'Edit',
              'action':'dummy_edit_form',
              'permissions':(ModifyPortalContent,) }
          , { 'id':'metadata',
              'name':'Metadata',
              'action':'metadata_edit_form',
              'permissions':(ModifyPortalContent,) }
          )
      }
    ,
    )

FTIDATA_CMF13_FOLDER = (
      { 'id' : 'Dummy Folder 13'
      , 'meta_type' : 'Dummy Folder'
      , 'description' : (
           'Dummy Folder.')
      , 'icon' : 'dummy_icon.gif'
      , 'product' : 'FooProduct'
      , 'factory' : 'addFoo'
      , 'filter_content_types' : 0
      , 'immediate_view' : 'dummy_edit_form'
      , 'actions' : (
            { 'id':'view',
              'name':'View',
              'action':'',
              'permissions':(View,),
              'category':'folder' }
          , { 'id':'edit',
              'name':'Edit',
              'action':'dummy_edit_form',
              'permissions':(ManageProperties,),
              'category':'folder' }
          , { 'id':'localroles',
              'name':'Local Roles',
              'action':'folder_localrole_form',
              'permissions':(ManageProperties,),
              'category':'folder' }
          )
      }
    ,
    )

FTIDATA_CMF14 = (
      { 'id' : 'Dummy Content 14'
      , 'meta_type' : 'Dummy'
      , 'description' : (
           'Dummy Content.')
      , 'icon' : 'dummy_icon.gif'
      , 'product' : 'FooProduct'
      , 'factory' : 'addFoo'
      , 'immediate_view' : 'metadata_edit_form'
      , 'actions' : (
            { 'id':'view',
              'name':'View',
              'action':'string:${object_url}/dummy_view',
              'permissions':(View,) }
          , { 'id':'edit',
              'name':'Edit',
              'action':'string:${object_url}/dummy_edit_form',
              'permissions':(ModifyPortalContent,) }
          , { 'id':'metadata',
              'name':'Metadata',
              'action':'string:${object_url}/metadata_edit_form',
              'permissions':(ModifyPortalContent,) }
          )
      }
    ,
    )

FTIDATA_CMF14_FOLDER = (
      { 'id' : 'Dummy Folder 14'
      , 'meta_type' : 'Dummy Folder'
      , 'description' : (
           'Dummy Folder.')
      , 'icon' : 'dummy_icon.gif'
      , 'product' : 'FooProduct'
      , 'factory' : 'addFoo'
      , 'filter_content_types' : 0
      , 'immediate_view' : 'dummy_edit_form'
      , 'actions' : (
            { 'id':'view',
              'name':'View',
              'action':'string:${object_url}',
              'permissions':(View,),
              'category':'folder' }
          , { 'id':'edit',
              'name':'Edit',
              'action':'string:${object_url}/dummy_edit_form',
              'permissions':(ManageProperties,),
              'category':'folder' }
          , { 'id':'localroles',
              'name':'Local Roles',
              'action':'string:${object_url}/folder_localrole_form',
              'permissions':(ManageProperties,),
              'category':'folder' }
          )
      }
    ,
    )

FTIDATA_CMF14_SPECIAL = (
      { 'id' : 'Dummy Content 14'
      , 'meta_type' : 'Dummy'
      , 'description' : (
           'Dummy Content.')
      , 'icon' : 'dummy_icon.gif'
      , 'product' : 'FooProduct'
      , 'factory' : 'addFoo'
      , 'immediate_view' : 'metadata_edit_form'
      , 'actions' : (
            { 'id':'download',
              'name':'Download',
              'action':'string:${object_url}/',   # Note: special default view
              'permissions':(View,) }
          , { 'id':'edit',
              'name':'Edit',
              'action':'string:${object_url}/dummy_edit_form',
              'permissions':(ModifyPortalContent,) }
          , { 'id':'view',                  # Note: not first with 'View' perm
              'name':'View',
              'action':'string:${object_url}/dummy_view',
              'permissions':(View,) }
          , { 'id':'metadata',
              'name':'Metadata',
              'action':'string:${object_url}/metadata_edit_form',
              'permissions':(ModifyPortalContent,) }
          , { 'id':'mkdir',
              'name':'MKDIR handler',
              'action':'string:dummy_mkdir',
              'category':'folder',
              'visible':0 }
          )
      }
    ,
    )

FTIDATA_CMF14_SPECIAL2 = (
      { 'id' : 'Dummy Content 14'
      , 'meta_type' : 'Dummy'
      , 'description' : (
           'Dummy Content.')
      , 'icon' : 'dummy_icon.gif'
      , 'product' : 'FooProduct'
      , 'factory' : 'addFoo'
      , 'immediate_view' : 'metadata_edit_form'
      , 'actions' : (
            { 'id': 'top',
              'name': 'View Mail Archive',
              'category': 'object',
              'action':'python:object.getArchive().absolute_url()',
              'permissions':(View,) }
          , { 'id':'view',
              'name':'View',
              'action':"python:object.someMethod() + '/some_template.html'",
              'permissions':(View,) }
          , { 'id':'edit',
              'name':'Edit',
              'action':'string:${object_url}/dummy_edit_form',
              'permissions':(ModifyPortalContent,) }
          , { 'id':'metadata',
              'name':'Metadata',
              'action':'string:${object_url}/metadata_edit_form',
              'permissions':(ModifyPortalContent,) }
          , { 'id':'mkdir',
              'name':'MKDIR handler',
              'action':'python:object.getMKDIR().absolute_url()',
              'category':'folder',
              'visible':0 }
          )
      }
    ,
    )

FTIDATA_CMF15 = (
      { 'id' : 'Dummy Content 15'
      , 'meta_type' : 'Dummy'
      , 'description' : (
           'Dummy Content.')
      , 'icon' : 'dummy_icon.gif'
      , 'product' : 'FooProduct'
      , 'factory' : 'addFoo'
      , 'immediate_view' : 'metadata.html'
      , 'aliases' : {
           '(Default)':'dummy_view',
           'view':'dummy_view',
           'view.html':'dummy_view',
           'edit.html':'dummy_edit_form',
           'metadata.html':'metadata_edit_form',
           'gethtml':'source_html'}
      , 'actions' : (
            { 'id':'view',
              'title': 'View',
              'action':'string:${object_url}/view.html',
              'permissions':(View,) }
          , { 'id':'edit',
              'title': 'Edit',
              'action':'string:${object_url}/edit.html',
              'permissions':(ModifyPortalContent,) }
          , { 'id':'metadata',
              'title': 'Metadata',
              'action':'string:${object_url}/metadata.html',
              'permissions':(ModifyPortalContent,) }
          )
      }
    ,
    )


STI_SCRIPT = """\
## Script (Python) "addBaz"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=folder, id
##title=
##
product = folder.manage_addProduct['FooProduct']
product.addFoo(id)
item = getattr(folder, id)
return item
"""
