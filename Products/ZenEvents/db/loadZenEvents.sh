#!/bin/sh
mysql -u root < zenevents.sql
for f in *.dat
do
    mysql -u root < $f
done
