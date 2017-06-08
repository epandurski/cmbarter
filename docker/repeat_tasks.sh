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

counter=0
trap "terminate=true" SIGTERM
while [[ $terminate != true ]]; do
    sleep 1
    ((counter += 1))
    ((counter % 60)) || $process_emails
    ((counter % 600)) || $execute_turn
done
