#!/usr/bin/env bash
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


function help()
{
    cat <<CAT_EOF >&2
Usage: $0 {status|pause|resume|help}

    MYSQL_LOCK_TIMEOUT env var may be overridden from default of 60 seconds
        used in call to mysql GET_LOCK()

CAT_EOF
}


function datetimestamp()
{
    TZ=UTC date +"%Y-%m-%dT%Hh%Mm%SsZ"
}


function die
{
    echo "$(datetimestamp): ERROR: ${*}" >&2
    exit 1
}


function logError
{
    echo "$(datetimestamp): ERROR: ${*}" >&2
}


function logInfo
{
    echo "$(datetimestamp): INFO: ${*}" >&2
}


function getConfValue
{
    local conf="$1"     # configuration file to use (full path)
    local key="$2"      # config value to check for
    local prepend="$3"  # optional: prepend this to value if value is set
    value=$(awk -v key="$key" '$1 == key {print $2; exit(0);}' "$conf")
    if [[ -n $prepend ]]; then
        if [[ -n $value ]]; then
            echo "$prepend'$value'"
        fi
    else
        echo $value
    fi
}


function run_mysql_cmd()
{
    local database=$1
    shift
    local statement="$@"
    local cmd="mysql -A $MY_MYSQL_CONNECTION -e \"$statement\" $database"
    eval $cmd
    local rc=$?

    return $rc
}


function do_status()
{
    # $ zends -uroot -e "SELECT IS_FREE_LOCK('zodb.quiesce') \G" zodb
    # *************************** 1. row ***************************
    # IS_FREE_LOCK('zodb.quiesce'): 1

    local database=$1
    local lockname=$2

    logInfo "status database:$database lockname:$lockname"

    local fxn="IS_FREE_LOCK('$lockname')"
    local cmd="SELECT $fxn"
    local output=$(run_mysql_cmd "$database" "$cmd \G" | tail -1)
    case "$output" in
        "$fxn: 0")
            echo "IS_LOCKED: $database database with $lockname lockname"
            return 0
            ;;
        "$fxn: 1")
            echo "IS_NOT_LOCKED: $database database with $lockname lockname"
            return 0
            ;;
        *)
            echo "WARNING: UNABLE to discern status of lock with mysql statement: $cmd"
            return 1
            ;;
    esac

    return 1   # 1: error
}


function do_hold_lock()
{
    local database=$1
    local lockname=$2
    local timeout=$3

    # purposely not executing: FLUSH TABLES WITH READ LOCK
    #   http://www.mysqlperformanceblog.com/2012/03/23/how-flush-tables-with-read-lock-works-with-innodb-tables/
    # despite:
    #   http://www.mysqlperformanceblog.com/2006/08/21/using-lvm-for-mysql-backup-and-replication-setup/
    # ZEP is locked by locking ZODB since it attempts a ZODB lock before writes
    {
        echo "SELECT GET_LOCK('$lockname', $timeout) \G;"
        while true; do sleep 1; done
    } | eval mysql $MY_MYSQL_CONNECTION $database

    return $?
}


function do_pause()
{
    local database=$1
    local lockname=$2
    local timeout=$3

    logInfo "pause database:$database lockname:$lockname timeout:$timeout"

    $0 hold-lock &
    disown
    for numtries in $(eval echo {1..$timeout}); do
        logInfo "Checking lock status (try: $numtries/$timeout):"
        local output=$($0 status)
        logInfo $output
        if [[ $output =~ "IS_LOCKED:" ]]; then
            return 0
        fi
        sleep 1
    done
    return 1
}


function do_resume()
{
    local database=$1
    local lockname=$2

    logInfo "resume database:$database lockname:$lockname"

    pkill -f "$0 hold-lock"
    sleep 1
    do_status $database $lockname
}


function main()
{
    [[ -n "$CFGDIR" ]] || die "CFGDIR env var is not set"
    [[ -d "$CFGDIR" ]] || die "CFGDIR=$CFGDIR is not a directory"

    export MY_MYSQL_CONNECTION=
    MY_MYSQL_CONNECTION+=" "$(getConfValue "$CFGDIR/global.conf" "zodb-admin-user" "--user=")
    MY_MYSQL_CONNECTION+=" "$(getConfValue "$CFGDIR/global.conf" "zodb-admin-password" "--password=")
    MY_MYSQL_CONNECTION+=" "$(getConfValue "$CFGDIR/global.conf" "zodb-host" "--host=")
    MY_MYSQL_CONNECTION+=" "$(getConfValue "$CFGDIR/global.conf" "zodb-port" "--port=")
    [[ $MY_MYSQL_CONNECTION =~ "--user=" ]] || die "required zodb-admin-user not found in $CFGDIR/global.conf"

    local database=$(getConfValue "$CFGDIR/global.conf" "zodb-db")
    local lockname="$database.quiesce"
    local timeout=${MYSQL_LOCK_TIMEOUT:-60}
    case "$CMD" in
        status)
            do_status $database $lockname
	    ;;

        pause)
            do_pause $database $lockname $timeout
	    ;;

        resume)
            do_resume $database $lockname
	    ;;

        hold-lock)
            # do not advertise via help that private method 'hold-lock' is a valid run command
            do_hold_lock $database $lockname $timeout
        ;;

        help)
	        help
	    ;;

        *)
	        help
	        exit 1
    esac
}


if [[ "$(basename $0)" == "quiesce-mysql.sh" ]]; then
    [[ -n "$ZENHOME" ]] || die "ZENHOME env var is not set"

    # Needs these env vars provided from zenfunctions:
    #   CFGDIR=$ZENHOME/etc
    source $ZENHOME/bin/zenfunctions

    main "$@"
    exit $?
fi

