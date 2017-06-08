#!/bin/bash
#
# This file is needed by "Dockerfile-tasks".

case $SMTP_ENCRYPTION in
    none|NONE)
	process_emails="process_emails.py"
	;;
    ssl|SSL)
	process_emails="process_emails.py --ssl"
	;;
    starttls|STARTTLS)
	process_emails="process_emails.py --starttls"
	;;
    *)
	echo "ERROR: invalid SMTP_ENCRYPTION value."
	exit 1
	;;
esac

execute_turn="pypy /usr/local/bin/execute_turn.py --level=${MINOR_DIGITS-0}"

wait_for() {
    [[ -z $terminated ]] || return
    "$@" &
    pid=$!
    [[ -z $terminated ]] || kill $pid
    wait
    unset pid
}

terminate() {
    terminated=true
    [[ -z $pid ]] || kill $pid
}

counter=0
unset terminated
trap terminate SIGTERM SIGINT
while [[ -z $terminated ]]; do
    sleep 1
    ((counter += 1))
    ((counter % 60)) || wait_for $process_emails
    ((counter % 600)) || wait_for $execute_turn
done
