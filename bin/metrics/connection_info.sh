#!/bin/sh
mysql -s --skip-column-names -B <<SQL

USE zodb;
SELECT info
FROM connection_info
WHERE ts >= (NOW() - INTERVAL 5 MINUTE)
ORDER BY ts;

SQL

