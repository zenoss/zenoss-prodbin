#!/usr/bin/env bash
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


function help()
{
    echo "Usage: $0 {status|pause|resume|help}" >&2
}


function die
{
    echo "ERROR: ${*}" >&2
    exit 1
}


function getConfValue
{
    local conf="$1"
    local key="$2"
    local prepend="$3"
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
    local cmd="mysql $MY_MYSQL_CONNECTION -e \"$statement \G\" $database"
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

    local fxn="IS_FREE_LOCK('$lockname')"
    local cmd="SELECT $fxn"
    local output=$(run_mysql_cmd "$database" "$cmd" | tail -1)
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

    $0 hold-lock &
    disown
    for numtries in $(eval echo {1..$timeout}); do
        echo "#######======= checking lock status (try: $numtries/$timeout):"
        local output=$($0 status)
        echo $output
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
    # Needs these env vars provided from zenfunctions:
    #   CFGDIR=$ZENHOME/etc
    source $ZENHOME/bin/zenfunctions

    main "$@"
    exit $?
fi

