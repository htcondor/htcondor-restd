FROM kbase/sdkpython:3.8.0

RUN apt-get update -y && apt-get install -y vim wget
RUN curl -fsSL https://get.htcondor.org |  /bin/bash -s -- --no-dry-run


COPY . /condor_flask
WORKDIR /condor_flask
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd restd


USER restd
ENV FLASK_APP="condor_restd flask run -p 5000"
ENTRYPOINT ["gunicorn"]
CMD [ "-w", "4", "-b", "127.0.0.1:5000", "condor_restd:app" ]
