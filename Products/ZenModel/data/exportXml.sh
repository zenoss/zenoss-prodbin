#! /bin/sh

echo 'Dumping...\c'
echo 'menus...\c'
zendmd >/dev/null 2>&1  <<EOF
fp = open('menus.xml', 'w')
dmd.zenMenus.exportXml(fp)
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
