#!/usr/bin/env bash

if [ "$CONDOR_JWT_TOKEN" ] ; then
     mkdir -p /home/restd/.condor/tokens.d
     echo "$CONDOR_JWT_TOKEN" > /home/restd/.condor/tokens.d/JWT
     chown restd /home/restd/.condor/tokens.d/JWT
     chmod 600 /home/restd/.condor/tokens.d/JWT
fi

gunicorn -w 4 -b 127.0.0.1:5000 condor_restd:app --access-logfile -
