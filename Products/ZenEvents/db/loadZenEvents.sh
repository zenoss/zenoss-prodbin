#!/bin/sh
mysql -u root --password=$1 < zenevents.sql
for f in *.dat
do
    mysql -u root --password=$1 < $f
done
