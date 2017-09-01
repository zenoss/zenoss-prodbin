#!/bin/bash

mysql -s --skip-column-names -B <<SQL
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
