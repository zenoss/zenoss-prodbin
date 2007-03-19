objnoprops = \
"""<object id='loc' module='Products.ZenRelations.tests.TestSchema' class='Location'>
</object>
"""


objwithprops = \
"""<object id='dev' module='Products.ZenRelations.tests.TestSchema' class='Device'>
<property setter="setPingStatus" type="int" id="pingStatus" mode="w" >
0
</property>
</object>
"""

objwithtoone = \
"""<object id='dev' module='Products.ZenRelations.tests.TestSchema' class='Device'>
<property setter="setPingStatus" type="int" id="pingStatus" mode="w" >
0
</property>
<toone id='location' objid='loc'/>
</object>
"""

objwithtomany = \
"""<object id='loc' module='Products.ZenRelations.tests.TestSchema' class='Location'>
<tomany id='devices'>
<link objid='dev'/>
</tomany>
</object>
"""

objwithtomanycont = \
"""<object id='dev' module='Products.ZenRelations.tests.TestSchema' class='Device'>
<property setter="setPingStatus" type="int" id="pingStatus" mode="w" >
0
</property>
<tomanycont id='interfaces'>
<object id='eth0' module='Products.ZenRelations.tests.TestSchema' class='IpInterface'>
<toone id='device' objid='dev'/>
</object>
</tomanycont>
</object>
"""
