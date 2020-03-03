import re
import socket
import subprocess

import htcondor
import pytest
import requests

try:
    from typing import *
except ImportError:
    pass


# TODO Use the webapp factory model so we can test the app directly.
#  This described at https://flask.palletsprojects.com/en/1.1.x/tutorial/factory/#the-application-factory.
#  The factory should reload the condor config (htcondor.reload_config()) when run.
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


def test_grouped_status(fixtures):
    j = checked_get_json("v1/grouped_status/MyType")  # type: Dict
    assert j, "no grouped classads returned"

    assert "DaemonMaster" in j, "no master ads in result"
    assert j["DaemonMaster"], "list of startd master ads empty"
    assert j["DaemonMaster"][0].get("type"), "type missing"
    assert j["DaemonMaster"][0]["type"] == "DaemonMaster", (
        "unexpected type. Expected: 'DaemonMaster'. Got: '%s'"
        % j["DaemonMaster"][0]["type"]
    )


def test_grouped_status_with_projection(fixtures):
    j = checked_get_json("v1/grouped_status/MyType?projection=name")  # type: Dict
    assert j, "no grouped classads returned"

    assert "DaemonMaster" in j, "no master ads in result"
    assert j["DaemonMaster"], "list of startd master ads empty"
    assert j["DaemonMaster"][0].get("name"), "name missing"


def check_job_attrs(job):
    for attr in ["classad", "jobid"]:
        assert job.get(attr), "%s attr missing" % attr


def queue(sub, *args, **kwargs):
    schedd = htcondor.Schedd()
    with schedd.transaction() as txn:
        cluster_id = sub.queue(txn, *args, **kwargs)
    return cluster_id


def submit_job(executable, arguments=""):
    """Submit a job and return the cluster ID"""
    sub = htcondor.Submit({"Executable": executable, "Arguments": arguments})
    return queue(sub)


def submit_sleep_job():
    """Submit a sleep job and return the cluster ID"""
    return submit_job("/usr/bin/sleep", "300")


def rm_cluster(cluster_id):
    schedd = htcondor.Schedd()
    schedd.act(htcondor.JobAction.Remove, "ClusterId == %d" % cluster_id)


def _test_jobs_queries(cluster_id, endpoint):
    check_job_attrs(checked_get_json("v1/%s/DEFAULT" % endpoint)[0])
    check_job_attrs(checked_get_json("v1/%s/DEFAULT/%d" % (endpoint, cluster_id))[0])
    check_job_attrs(checked_get_json("v1/%s/DEFAULT/%d/0" % (endpoint, cluster_id)))
    j1 = checked_get_json("v1/%s/DEFAULT/%d/0/cmd" % (endpoint, cluster_id))
    j2 = checked_get_json("v1/%s/DEFAULT/%d/0/CMD" % (endpoint, cluster_id))
    assert j1 == "/usr/bin/sleep", "%s: cmd attribute does not match" % endpoint
    assert (
        j2 == "/usr/bin/sleep"
    ), "%s: cmd attribute when querying for 'CMD' does not match (case not handled?)"


def test_jobs(fixtures):
    cluster_id = submit_sleep_job()
    _test_jobs_queries(cluster_id, "jobs")
    rm_cluster(cluster_id)
    _test_jobs_queries(cluster_id, "history")


def _test_grouped_jobs_queries(cluster_id, cmd, endpoint, projection=None):
    for full_endpoint in (
        "v1/%s/DEFAULT/cmd" % endpoint,
        "v1/%s/DEFAULT/cmd/%d" % (endpoint, cluster_id),
    ):
        full_query = full_endpoint + (
            "?projection=%s" % projection if projection else ""
        )
        j = checked_get_json(full_query)
        assert cmd in j, "%s: expected cmd %s does not exist" % (full_query, cmd)
        assert isinstance(
            j[cmd], list
        ), "%s: cmd group for %s does not have expected type" % (full_query, cmd)
        assert j[cmd], "%s: cmd group for %s is empty" % (full_query, cmd)
        check_job_attrs(j[cmd][0])
        assert j[cmd][0]["classad"]["cmd"] == cmd, (
            "%s: cmd attribute does not match" % full_query
        )


def test_grouped_jobs(fixtures):
    cluster_id = submit_sleep_job()
    cluster_id_2 = submit_job("/usr/bin/env", "")
    _test_grouped_jobs_queries(cluster_id, "/usr/bin/sleep", "grouped_jobs")
    _test_grouped_jobs_queries(cluster_id_2, "/usr/bin/env", "grouped_jobs")
    rm_cluster(cluster_id)
    rm_cluster(cluster_id_2)
    _test_grouped_jobs_queries(cluster_id, "/usr/bin/sleep", "grouped_history")
    _test_grouped_jobs_queries(cluster_id_2, "/usr/bin/env", "grouped_history")


def test_grouped_jobs_with_projection(fixtures):
    cluster_id = submit_sleep_job()
    cluster_id_2 = submit_job("/usr/bin/env", "")
    _test_grouped_jobs_queries(
        cluster_id, "/usr/bin/sleep", "grouped_jobs", projection="owner"
    )
    _test_grouped_jobs_queries(
        cluster_id_2, "/usr/bin/env", "grouped_jobs", projection="owner"
    )
    rm_cluster(cluster_id)
    rm_cluster(cluster_id_2)
    _test_grouped_jobs_queries(
        cluster_id, "/usr/bin/sleep", "grouped_history", projection="owner"
    )
    _test_grouped_jobs_queries(
        cluster_id_2, "/usr/bin/env", "grouped_history", projection="owner"
    )


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
