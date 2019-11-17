#!/usr/bin/env bash
set -x
docker build . -t condor_flask
id=`docker ps | grep condor_flask | cut -f1 -d' '`
docker kill $id
# Run Interactive Mode
#docker run -it -u 0 -v `pwd`/condor_configs/password:/etc/condor/password -p 9680:9680 condor_flask:latest bash
docker run -d -u 0 -v `pwd`/condor_configs/password:/etc/condor/password -p 9680:9680 condor_flask:latest /condor_flask/rungunicorn

# Run Server

