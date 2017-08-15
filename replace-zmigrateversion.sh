#!/bin/bash
#
# Replace SCHEMA_* values in service migration scripts with the actual values
#

if [ -z "$SCHEMA_MAJOR" ]; then
    echo "ERROR: Missing required argument SCHEMA_MAJOR"
    exit 1
elif [ -z "$SCHEMA_MINOR" ]; then
    echo "ERROR: Missing required argument SCHEMA_MINOR"
    exit 1
elif [ -z "$SCHEMA_REVISION" ]; then
    echo "ERROR: Missing required argument SCHEMA_REVISION"
    exit 1
fi

echo Replacing SCHEMA_MAJOR with $SCHEMA_MAJOR, and
echo Replacing SCHEMA_MINOR with $SCHEMA_MINOR, and
echo Replacing SCHEMA_REVISION with $SCHEMA_REVISION

set -e

SED_REGEX="s/SCHEMA_MAJOR/$SCHEMA_MAJOR/g; \
 s/SCHEMA_MINOR/$SCHEMA_MINOR/g; \
 s/SCHEMA_REVISION/$SCHEMA_REVISION/g; "

TMP_FILE=replace-zmigrateVersion.tmp
cd Products/ZenModel/migrate
for file in `grep -l ZMigrateVersion *.py`
do
	echo "Updating $file ..."
	grep -v ZMigrateVersion $file | sed -e "$SED_REGEX" >$TMP_FILE
	mv $TMP_FILE $file
done
rm -f $TMP_FILE
