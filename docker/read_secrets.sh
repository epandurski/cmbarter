#!/bin/bash
#
# This file is used by "Dockerfile.web".

if [[ -z $CMBARTER_SECRET_KEY ]]; then
    if [[ -s /run/secrets/CMBARTER_SECRET_KEY ]]; then
	export CMBARTER_SECRET_KEY=$(cat /run/secrets/CMBARTER_SECRET_KEY)
    else
	echo 'CMBARTER_SECRET_KEY is not set, /run/secrets/CMBARTER_SECRET_KEY is not present.'
	exit 1;
    fi
fi

if [[ -z $CMBARTER_REGISTRATION_SECRET ]]; then
    if [[ -s /run/secrets/CMBARTER_REGISTRATION_SECRET ]]; then
	export CMBARTER_REGISTRATION_SECRET=$(cat /run/secrets/CMBARTER_REGISTRATION_SECRET)
    fi
fi

exec "$@"
