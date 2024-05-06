ARG BASE_IMAGE=htcondor/mini
FROM ${BASE_IMAGE}
LABEL org.opencontainers.image.title="HTCondor REST Daemon dev/test image"
LABEL org.opencontainers.image.vendor=""
RUN mkdir -p /usr/local/src
COPY . /usr/local/src/htcondor-restd/
# Check how the RESTD was installed into the minicondor image.
# If the RESTD has been installed in a virtualenv owned by the restd user, then
# we need to install the new version in the same virtualenv.
# Otherwise, we install the new version as root.
RUN if [ -e /home/restd/htcondor-restd/bin/activate ]; then \
        runuser restd bash -c " \
            . /home/restd/htcondor-restd/bin/activate && \
            # copy everything to a dir restd has write permissions to \
            cp -r /usr/local/src/htcondor-restd /var/tmp/htcondor-restd && \
            python3 -mpip install --upgrade /var/tmp/htcondor-restd  && \
            rm -rf /var/tmp/htcondor-restd \
        "; \
    else \
        $(command -v pip-3 || command -v pip3) install --upgrade /usr/local/src/htcondor-restd; \
    fi
