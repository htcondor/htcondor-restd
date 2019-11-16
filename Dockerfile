FROM python:3
COPY . /condor_flask
WORKDIR /condor_flask
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update -y && apt-get install -y vim wget 
RUN apt-get install --yes htcondor
CMD [ "/condor_flask/rungunicorn" ]
