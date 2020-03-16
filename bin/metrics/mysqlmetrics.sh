#!/bin/bash

if [ $1 = "mariadb-model" ]
  then
     DB="zodb"
  else
    DB="zep"
fi

/usr/bin/python /opt/zenoss/Products/ZenUtils/ZenDB.py --usedb $DB --execsql=<<SQL
USE information_schema;

SELECT
    table_schema "Database",
    sum(data_length + index_length) "Bytes",
    sum(data_free) "Free"
FROM
    TABLES
GROUP BY
    1
;
SQL
