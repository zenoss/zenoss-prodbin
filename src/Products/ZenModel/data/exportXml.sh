#!/usr/bin/env bash

. $ZENHOME/bin/zenfunctions

dbtype=`zenglobalconf -p zodb-db-type`
# if [ "$dbtype" = "mysql" ]; then
#     innodb_format=`$ZENHOME/Products/ZenUtils/ZenDB.py --usedb=zodb --execsql='SELECT lower(@@innodb_file_format)'`
#     if [ "$innodb_format" != "barracuda" ]; then
#         echo "Error, your mysql innodb file format is not (at least) Barracuda"
#         exit 1
#     fi
#     object_state_format=`$ZENHOME/Products/ZenUtils/ZenDB.py --useadmin --usedb=zodb --execsql='select lower(row_format) from information_schema.tables where table_schema=database() and lower(table_name) = "object_state";'`
#     if [ "$object_state_format" != "compressed" ]; then
#         echo "Error object_state table is not compressed."
#         exit 1
#     fi
# fi

echo 'Loading reports...'
reportloader -f
echo $?
if [ $? -ne 0 ]; then
    echo "An error running reportloader."
    exit 1
fi

echo 'Running migrate...'
zenmigrate
if [ $? -ne 0 ]; then
    echo "An error running zenmigrate."
    exit 1
fi

echo 'Dumping Menus...'
zendmd >/dev/null 2>&1 <<EOF
fp = open('menus.xml', 'w')
fp.write('''<?xml version="1.0"?>\
<objects>\
<object id='/zport/dmd' module='Products.ZenModel.DataRoot' class='DataRoot'>\
''')
dmd.zenMenus.exportXml(fp)
fp.write('</object></objects>\n')
fp.close()
EOF
if [ $? -ne 0 ]; then
   echo "An error dumping menus."
   exit 1
fi

echo 'Dumping Devices...'
zendump -R /zport/dmd/Devices --ignore devices -o devices.xml
if [ $? -ne 0 ]; then
   echo "An error dumping devices."
   exit 1
fi

echo 'Dumping Services...'
zendump -R /zport/dmd/Services --ignore instances -o services.xml
if [ $? -ne 0 ]; then
    echo "An error dumping services."
    exit 1
fi

echo 'Dumping Event Classes...'
zendump -R /zport/dmd/Events -o events.xml
if [ $? -ne 0 ]; then
    echo "An error dumping classes."
    exit 1
fi

echo 'Dumping Manufacturers...'
zendump -R /zport/dmd/Manufacturers --ignore instances -o manufacturers.xml
if [ $? -ne 0 ]; then
    echo "An error dumping manufacturers."
    exit 1
fi

sed -i -e "s/id='\/zport\/dmd'/id='\/zport\/dmd\/Manufacturers'/g" manufacturers.xml
if [ $? -ne 0 ]; then
   echo "SED replacement failed."
   exit 1
fi

echo "Dumping Collector Templates..."
zendump -R /zport/dmd/Monitors --ignore devices --ignore instances -o monitorTemplate.xml
if [ $? -ne 0 ]; then
    echo "An error dumping templates."
    exit 1
fi

echo "Dumping Zenoss OS Process definitions..."
zendump -R /zport/dmd/Processes/Zenoss --ignore instances -o osprocesses.xml
if [ $? -ne 0 ]; then
    echo "An error dumping os processes."
    exit 1
fi

echo "Dumping SQL..."
$ZENHOME/Products/ZenUtils/ZenDB.py --usedb=zodb --dump --dumpfile=zodb.sql 
if [ $? -ne 0 ]; then
    echo "An error dumping database."
    rm -rf zodb.sql
    exit 1
fi

gzip --force zodb.sql
if [ $? -ne 0 ]; then
    echo "An error ziping database dump."
    rm -rf zodb.sql
    exit 1
fi


