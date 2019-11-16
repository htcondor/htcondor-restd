docker build . -t condor_flask

# Run Interactive Mode
#docker run -it -u 0 -v `pwd`/condor_configs/password:/etc/condor/password -p 9680:9680 condor_flask:latest bash

docker run -d -u 0 -v `pwd`/condor_configs/password:/etc/condor/password -p 9680:9680 condor_flask:latest /condor_flask/rungunicorn

# Run Server

