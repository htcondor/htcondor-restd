FROM kbase/sdkpython:3.8.0

RUN apt-get update -y && apt-get install -y vim wget
RUN curl -fsSL https://get.htcondor.org |  /bin/bash -s -- --no-dry-run
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd restd
RUN chown restd entrypoint.sh

USER restd
ENV FLASK_APP="condor_restd flask run -p 5000"
ENV _CONDOR_CONDOR_HOST="condor:9618"
ENV _CONDOR_RESTD_HIDE_JOB_ATTRS="condor:9618"


ENTRYPOINT ["entrypoint.sh"]

