condor_restd
============
REST-based API for HTCondor, using the Python bindings.

Currently allows read-only queries for jobs (in-queue and historical),
configuration, and machine status.


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


Queries
-------
The following queries are implemented.  Arguments in brackets `{}` are optional:


### jobs and history

Access job information (similar to `condor_q` and `condor_history`).
`jobs` and `history` behave exactly the same, except `jobs` queries jobs in the queue,
and `history` queries jobs that have left the queue.

    GET /v1/jobs{/clusterid}{?projection,constraint}
    GET /v1/history{/clusterid}{?projection,constraint}

Returns a list of job objects.  A job object looks like

    {
      "jobid": "123.45",
      "classad": { <classad> }
    }

Returns an empty list if no jobs match.

`clusterid` limits the results to jobs with the given cluster ID.

`projection` is one or more comma-separated attributes; if specified,
only those attributes will be in the `classad` object of each job.

`constraint` is a classad expression restricting which jobs to include
in the result.

    GET /v1/jobs/clusterid/procid{?projection}
    GET /v1/history/clusterid/procid{?projection}

Returns a single job object with cluster ID given by `clusterid` and
the proc ID given by `procid`.
Raises `404` if no such job exists.

`projection` is one or more comma-separated attributes; if specified,
only those attributes will be in the `classad` object of the job.

    GET /v1/jobs/clusterid/procid/attribute
    GET /v1/history/clusterid/procid/attribute

Returns a single attribute of a job with cluster ID given by `clusterid`,
proc ID given by `procid`, and attribute name given by `attribute`.

Raises `404` if no such job exists, or if the attribute is undefined.


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
