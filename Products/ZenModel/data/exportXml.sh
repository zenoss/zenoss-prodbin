#! /bin/sh

echo 'Running migrate'
zenmigrate run -v 10

echo 'Dumping...\c'
echo 'menus...\c'
zendmd <<EOF
fp = open('menus.xml', 'w')
fp.write('''<?xml version="1.0"?>
<objects>
<object id='/zport/dmd' module='Products.ZenModel.DataRoot' class='DataRoot'>
''')
dmd.zenMenus.exportXml(fp)
fp.write('</object></objects>\n')
fp.close()
EOF

echo 'devices...\c'
zendump -R /zport/dmd/Devices --ignore devices -o devices.xml
echo 'services...\c'
zendump -R /zport/dmd/Services --ignore instances -o services.xml
echo 'events...\c'
zendump -R /zport/dmd/Events -o events.xml
echo 'manufacturers...\c'
zendump -R /zport/dmd/Manufacturers --ignore instances -o manufacturers.xml
echo done
