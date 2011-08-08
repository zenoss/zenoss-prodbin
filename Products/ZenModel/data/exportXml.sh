#!/bin/bash
stty -echo
echo 'MySQL root password: \c'
read MYSQLPW
stty echo
echo
if [ -z "$MYSQLPW" ]; then
    PWOPT=""
else
    PWOPT="-p$MYSQLPW"
fi

. $ZENHOME/bin/zenfunctions

echo 'Running migrate...'
zenmigrate

echo 'Dumping Menus...\c'
zendmd >/dev/null 2>&1 <<EOF
fp = open('menus.xml', 'w')
fp.write('''<?xml version="1.0"?>
<objects>
<object id='/zport/dmd' module='Products.ZenModel.DataRoot' class='DataRoot'>
''')
dmd.zenMenus.exportXml(fp)
fp.write('</object></objects>\n')
fp.close()
EOF

echo 'Dumping Devices...\c'
zendump -R /zport/dmd/Devices --ignore devices -o devices.xml
echo 'Dumping Services...\c'
zendump -R /zport/dmd/Services --ignore instances -o services.xml
echo 'Dumping Event Classes...\c'
zendump -R /zport/dmd/Events -o events.xml
echo 'Dumping Manufacturers...\c'
zendump -R /zport/dmd/Manufacturers --ignore instances -o manufacturers.xml
replace "id='/zport/dmd'" "id='/zport/dmd/Manufacturers'" -- manufacturers.xml
echo "Dumping Collector Templates...\c"
zendump -R /zport/dmd/Monitors --ignore devices --ignore instances -o monitorTemplate.xml
echo "Dumping Zenoss OS Process definitions...\c"
zendump -R /zport/dmd/Processes/Zenoss --ignore instances -o osprocesses.xml
echo "Dumping SQL...\c"
mysqldump -u root $PWOPT zodb | gzip -c > zodb.sql.gz
echo done
