FROM kbase/sdkpython:3.8.0

RUN apt-get update -y && apt-get install -y vim wget
RUN curl -fsSL https://get.htcondor.org |  /bin/bash -s -- --no-dry-run

RUN useradd -m restd
COPY --chown=restd:restd . /condor-rest-api
COPY --chown=restd:restd condor_config /etc/condor/condor_config

ENV WORKDIR="/condor-rest-api"
ENV FLASK_APP="condor_restd flask run -p 5000"
ENV _CONDOR_CONDOR_HOST="condor:9618"
ENV _CONDOR_RESTD_HIDE_JOB_ATTRS="condor:9618"

WORKDIR /condor-rest-api
RUN python -m venv venv && . venv/bin/activate && pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["/condor-rest-api/entrypoint.sh"]

