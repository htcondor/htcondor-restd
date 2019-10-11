import os
import re
import socket
import subprocess
import time

import htcondor
import pytest
import requests


URIBASE = "http://127.0.0.1:9680"


@pytest.fixture
def fixtures():
    # Check for already running condor and apid
    # Can't start them up myself b/c no root (for condor) and I can't kill
    # a flask process I start because it forks
    subprocess.check_call(["condor_ping", "DC_NOP"])
    subprocess.check_call(["curl", "-s", URIBASE])


def get(uri, params=None):
    return requests.get(URIBASE + "/" + uri, params=params)


def checked_get(uri, params=None):
    r = get(uri, params=params)
    assert 200 <= r.status_code < 400, "GET %s%s failed%s" % (
        uri,
        " with params %r" % params if params else "",
        " with message %r" % r.text if r.text else "",
    )
    return r


def checked_get_json(uri, params=None):
    return checked_get(uri, params=params).json()


def test_condor_version(fixtures):
    r = checked_get("v1/config/condor_version")
    assert re.search(r"\d+\.\d+\.\d+", r.text), "Unexpected condor_version"


def test_status(fixtures):
    j = checked_get_json("v1/status")
    assert j, "no classads returned"
    for attr in ["name", "classad"]:
        assert j[0].get(attr), "%s attr missing" % (attr)
    for daemon in ["collector", "master", "negotiator", "schedd", "startd"]:
        j = checked_get_json("v1/status?query=" + daemon)
        assert j, "%s: no classads returned" % (daemon)
        for attr in ["name", "classad", "type"]:
            assert j[0].get(attr), "%s: %s attr missing" % (daemon, attr)


def check_job_attrs(job):
    for attr in ["classad", "jobid"]:
        assert job.get(attr), "%s attr missing" % attr


def submit_sleep_job():
    """Submit a sleep job and return the cluster ID"""
    sub = htcondor.Submit({"Executable": "/usr/bin/sleep", "Arguments": "300"})
    schedd = htcondor.Schedd()
    with schedd.transaction() as txn:
        cluster_id = sub.queue(txn)
    return cluster_id


def rm_cluster(cluster_id):
    schedd = htcondor.Schedd()
    schedd.act(htcondor.JobAction.Remove, "ClusterId == %d" % cluster_id)


def _test_jobs_queries(cluster_id, endpoint):
    queries = [
        "v1/%s/DEFAULT" % endpoint,
        "v1/%s/DEFAULT/%d" % (endpoint, cluster_id),
        "v1/%s/DEFAULT/%d/0" % (endpoint, cluster_id),
    ]
    check_job_attrs(checked_get_json("v1/%s/DEFAULT" % endpoint)[0])
    check_job_attrs(checked_get_json("v1/%s/DEFAULT/%d" % (endpoint, cluster_id))[0])
    check_job_attrs(checked_get_json("v1/%s/DEFAULT/%d/0" % (endpoint, cluster_id)))
    j = checked_get_json("v1/%s/DEFAULT/%d/0/cmd" % (endpoint, cluster_id))
    assert j == "/usr/bin/sleep", "%s: cmd attribute does not match" % endpoint


def test_jobs(fixtures):
    cluster_id = submit_sleep_job()
    _test_jobs_queries(cluster_id, "jobs")
    rm_cluster(cluster_id)
    _test_jobs_queries(cluster_id, "history")


def test_config(fixtures):
    args = ["", "?daemon=master"]
    for arg in args:
        j = checked_get_json("v1/config%s" % arg)
        assert "full_hostname" in j, "full_hostname attr missing"
        assert j["full_hostname"] == socket.getfqdn()

        assert (
            checked_get("v1/config/full_hostname%s" % arg).content.strip().decode()
            == '"%s"' % socket.getfqdn()
        )
