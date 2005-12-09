objnoprops = \
"""<object id='loc' module='Products.ZenRelations.tests.TestSchema' class='Location'>
<property type='string' id='title' mode='wd' >

</property>
</object>
"""


objwithprops = \
"""<object id='dev' module='Products.ZenRelations.tests.TestSchema' class='Device'>
<property setter='setPingStatus' type='int' id='pingStatus' mode='w' >
0
</property>
<property type='lines' id='communities' mode='w' >
()
</property>
</object>
"""

objwithtoone = \
"""<object id='dev' module='Products.ZenRelations.tests.TestSchema' class='Device'>
<property setter='setPingStatus' type='int' id='pingStatus' mode='w' >
0
</property>
<property type='lines' id='communities' mode='w' >
()
</property>
<toone id='location'>loc
</toone>
</object>
"""

objwithtomany = \
"""<object id='loc' module='Products.ZenRelations.tests.TestSchema' class='Location'>
<property type='string' id='title' mode='wd' >

</property>
<tomany id='devices'>
<link objid='dev'/>
</tomany>
</object>
"""

objwithtomanycont = \
"""<object id='dev' module='Products.ZenRelations.tests.TestSchema' class='Device'>
<property setter='setPingStatus' type='int' id='pingStatus' mode='w' >
0
</property>
<property type='lines' id='communities' mode='w' >
()
</property>
<tomanycont id='interfaces'>
<object id='eth0' module='Products.ZenRelations.tests.TestSchema' class='IpInterface'>
<property type='string' id='title' mode='wd' >

</property>
<toone id='device' objid="dev"/>
</object>
</tomanycont>
</object>
"""
