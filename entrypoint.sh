#!/usr/bin/env bash

#Setup tokens in restd home directory
if [ "$CONDOR_JWT_TOKEN" ] ; then
     mkdir -p /home/restd/.condor/tokens.d
     echo "$CONDOR_JWT_TOKEN" > /home/restd/.condor/tokens.d/JWT
     chown restd:restd /home/restd/.condor/tokens.d/JWT
     chmod 600 -R /home/restd/.condor/tokens.d/JWT
fi

# Set the number of gevent workers to number of cores * 2 + 1
# See: http://docs.gunicorn.org/en/stable/design.html#how-many-workers
calc_workers="$(($(nproc) * 2 + 1))"
# Use the WORKERS environment variable, if present
workers=${WORKERS:-$calc_workers}

. ./venv/bin/activate

exec gunicorn \
  --user restd \
  --access-logfile - \
  --error-logfile - \
  --timeout 1800 \
  --workers $workers \
  --bind :5000 \
  ${DEVELOPMENT:+"--reload"} \
  condor_restd:app
