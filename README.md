condor_restd
============
REST-based API for HTCondor, using the Python bindings.

Currently allows read-only queries for jobs (in-queue and historical),
configuration, and machine status.

NOTE: The API has not stabilized yet and queries are subject to change.
Do not use in production.


KBase Specific Configuration Information
-----------
* To specify the auth url set `AUTH_URL`
* To specify the jwt token used to connect to condor specify `CONDOR_JWT_TOKEN`
* To specify which condor collector, schedd, and which variables are redacted (e.g. `environment`), modify the condor_config either here, or mount it in via a ConfigMap
* This api is protected via AUTH Roles, and checks to see if you have the proper EE2 Role to allow you access to this api
* For information about where python and its dependencies are installed, see the `Dockerfile` and `entrypoint.sh`

Installation
------------
Installation requires the following Python modules:

- `htcondor >= 8.9.2`
- `flask`
- `flask-restful`

Install them via `pip` or your OS's package manager.

Create a virtualenv then `pip install -e .`.  To run using the
built-in Flask server (not for production), run

    FLASK_APP=condor_restd flask run -p 9680

For additional scalability, run using a WSGI server such as gunicorn:

    gunicorn -w4 -b127.0.0.1:9680 condor_restd:app


These commands will run the server on port 9680.

NOTE: Running the htcondor-restd as root is not recommended.  This
readme assumes that you are running the restd as the unprivileged user
`restd`.

Configuration
-------------
The RESTD is configured using HTCondor configuration; see
[the configuration section of the HTCondor manual](https://htcondor.readthedocs.io/en/latest/admin-manual/introduction-to-configuration.html)
for general configuration information.  Note that RESTD-specific
parameters are not listed in the manual yet.

If you do not have permission to edit global HTCondor configuration,
you may configure the RESTD in one of two ways, as described in the
[Ordered Evaluation to Set the Configuration](https://htcondor.readthedocs.io/en/latest/admin-manual/introduction-to-configuration.html#ordered-evaluation-to-set-the-configuration)
section of the HTCondor manual:

1. Adding the options to the user configuration file for the user
running the restd, in `$HOME/.config/user_config` (or the location
defined by `USER_CONFIG_FILE`).  This is recommended for non-container
installs.

2. Using the `_CONDOR_*` environment variables. For example, set
the value for `RESTD_MAX_JOBS` by setting the environment variable
`_CONDOR_RESTD_MAX_JOBS`.  This is recommended for container installs.

The following HTCondor configuration values apply:

- `CONDOR_HOST`: The hostname of the HTCondor central manager.
- `RESTD_HIDE_JOB_ATTRS`: A comma or space-separated list of job
  attributes to redact from queries.  Attributes in this list will
  show the value `<REDACTED>` in the jobs and history endpoints.
- `RESTD_MAX_JOBS`: The maximum number of jobs returned for jobs,
  grouped_jobs, history, and grouped_history queries.


Queries
-------
The following queries are implemented.  Arguments in brackets `{}` are optional:


### jobs and history

Access job information (similar to `condor_q` and `condor_history`).
`jobs` and `history` behave exactly the same, except `jobs` queries jobs in the queue,
and `history` queries jobs that have left the queue.

    GET /v1/jobs/{schedd}{/clusterid}{?projection,constraint}
    GET /v1/history/{schedd}{/clusterid}{?projection,constraint}

Returns a list of job objects.  A job object looks like

    {
      "jobid": "123.45",
      "classad": { <classad> }
    }

Returns an empty list if no jobs match.

`schedd` is the name of the schedd to query, or `DEFAULT` to use
the default schedd (if there is one). Raises `404` if the schedd
does not exist.

`clusterid` limits the results to jobs with the given cluster ID.

`projection` is one or more comma-separated attributes; if specified,
only those attributes will be in the `classad` object of each job.

`constraint` is a classad expression restricting which jobs to include
in the result.

    GET /v1/jobs/{schedd}/{clusterid}/{procid}{?projection}
    GET /v1/history/{schedd}/{clusterid}/{procid}{?projection}

Returns a single job object with cluster ID given by `clusterid` and
the proc ID given by `procid`.
Raises `404` if no such job exists.

`schedd` is the name of the schedd to query, or `DEFAULT` to use
the default schedd (if there is one). Raises `404` if the schedd
does not exist.

`projection` is one or more comma-separated attributes; if specified,
only those attributes will be in the `classad` object of the job.

    GET /v1/jobs/{schedd}/{clusterid}/{procid}/{attribute}
    GET /v1/history/{schedd}/{clusterid}/{procid}/{attribute}

Returns a single attribute of a job with cluster ID given by `clusterid`,
proc ID given by `procid`, and attribute name given by `attribute`.

`schedd` is the name of the schedd to query, or `DEFAULT` to use
the default schedd (if there is one). Raises `404` if the schedd
does not exist.

Raises `404` if no such job exists, or if the attribute is undefined.


### grouped_jobs and grouped_history

Like `jobs` and `history`, accesses job information.  However, they
group the returned jobs by an attribute.

`grouped_jobs` and `grouped_history` behave exactly the same, except
`grouped_jobs` queries jobs in the queue, and `grouped_history`
queries jobs that have left the queue.

    GET /v1/grouped_jobs/{schedd}/{groupby}{/clusterid}{?projection,constraint}
    GET /v1/grouped_history/{schedd}/{groupby}{/clusterid}{?projection,constraint}

Returns an object of lists of job objects, keyed by the value of the
attribute given in `groupby`.  A job object looks like:

    {
      "jobid": "123.45",
      "classad": { <classad> }
    }

The returned object looks like:

    {
      "value1": [ <job objects> ],
      "value2": [ <job objects> ]
    }

Returns an empty object if no jobs match.  Jobs that do not have the
attribute given in `groupby` are omitted from the result.  (This is
because null is not a valid key.)

`schedd` is the name of the schedd to query, or `DEFAULT` to use
the default schedd (if there is one). Raises `404` if the schedd
does not exist.

`clusterid` limits the results to jobs with the given cluster ID.

`projection` is one or more comma-separated attributes; if specified,
only those attributes, plus the `groupby` attribute, will be in the
`classad` object of each job.

`constraint` is a classad expression restricting which jobs to include
in the result.


### config

Access config information (similar to `condor_config_val`).

    GET /v1/config{/attribute}{?daemon}

If `attribute` is specified, returns the value of the specific
attribute in the condor config.  If not specified, returns an object
of the form:

    {
      "attribute1": "value1",
      "attribute2": "value2",
      ...
    }

If `daemon` is specified, query the given running daemon; otherwise,
query the static config files.

Returns 404 if `attribute` is specified but the attribute is undefined.


### status

Access machine and daemon information (similar to `condor_status`).

    GET /v1/status{/name}{?projection,constraint,query}

This returns an array of objects of the following form:

    {
      "name": "<name classad attribute>",
      "type": "<ad type>",
      "classad": { <classad object> }
    }

`name` is a specific host or slot to query.  If not specified, all
matching ads are returned.

`query` is the type of ad to query; see the "Query options" in the
condor_status(1) manpage.  "any" is the default.

`projection` is one or more comma-separated attributes; if specified,
only those attributes will be in the `classad` object of each job.

`constraint` is a classad expression restricting which ads to include
in the result.


### grouped_status

Like `status`, accesses machine and daemon information.  However, it
groups the returned objects by a classad attribute.

    GET /v1/grouped_status/{groupby}{/name}{?projection,constraint,query}

Returns an object of lists of status objects, keyed by the value of
the attribute given in `groupby`.  A status object looks like:

    {
      "name": "<name classad attribute>",
      "type": "<ad type>",
      "classad": { <classad object> }
    }

The returned object looks like:

    {
      "value1": [ <status objects> ],
      "value2": [ <status objects> ]
    }

Returns an empty object if nothing matches.  Status objects that do
not have the classad attribute given in `groupby` are omitted from
the result.  (This is because null is not a valid key.)

`name` is a specific host or slot to query.  If not specified, all
matching ads are returned.

`query` is the type of ad to query; see the "Query options" in the
condor_status(1) manpage.  "any" is the default.

`projection` is one or more comma-separated attributes; if specified,
only those attributes, plus the `groupby` attribute, will be in the
`classad` object of each job.

`constraint` is a classad expression restricting which ads to include
in the result.
