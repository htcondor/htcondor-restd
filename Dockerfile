FROM python:3

COPY . /condor_flask
WORKDIR /condor_flask
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update -y && apt-get install -y vim wget 
RUN apt-get install --yes htcondor
RUN useradd restd


USER restd
ENV FLASK_APP=condor_restd flask run -p 5000
CMD [ "gunicorn -w4 -b127.0.0.1:5000 condor_restd:app ]
