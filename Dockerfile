FROM ubuntu:18.04

# Install commonly used utilties
RUN apt-get update -y && apt-get install -y vim wget curl 

# Install Python3 and Libraries (source /root/miniconda/bin/activate)
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh \
&& bash ~/miniconda.sh -b -p /miniconda3.7
ENV PATH=/miniconda3.7/bin:$PATH

# If you don't volume mount your password, you can copy it in
#COPY password /etc/condor/password

# Install condor flask dependencies
WORKDIR /condor_flask
COPY requirements.txt /condor_flask
RUN pip install --no-cache-dir -r requirements.txt

# Copy over the main app and your customized condor config

COPY . /condor_flask
COPY condor_configs/condor_config /etc/condor/condor_config

CMD [ "/condor_flask/rungunicorn" ]

LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.vcs-url="https://github.com/kbase/htcondor-restd" \
      org.label-schema.vcs-ref=$COMMIT \
      org.label-schema.schema-version="1.0.0-rc1" \
      us.kbase.vcs-branch=$BRANCH  \
      maintainer="Steve Chan sychan@lbl.gov"
