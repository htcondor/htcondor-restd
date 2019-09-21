condor_restd.py
===============
REST-based API for HTCondor, based on the Python bindings.

Currently allows read-only queries for jobs (in-queue and historical),
configuration, and machine status.


Installation
------------
Create a virtualenv then `pip install -e .`.  To run using the
built-in Flask server (not for production), run

    FLASK_APP=condor_restd flask run -p 9680

For additional scalability, run using a WSGI server such as gunicorn:

    gunicorn -w4 -b127.0.0.1:9680 condor_restd:app


These commands run on port 9680.


Queries
-------
The following queries are implemented.  Arguments in brackets `{}` are optional:


### jobs and history

Access job information (similar to `condor_q` and `condor_history`).
`jobs` and `history` behave exactly the same, except `jobs` queries jobs in the queue,
and `history` queries jobs that have left the queue.

    GET /v1/jobs{/clusterid}{/procid}{/attribute}{?projection,constraint}
    GET /v1/history{/clusterid}{/procid}{/attribute}{?projection,constraint}

If `clusterid`, `procid`, and `attribute` are specified, then it
returns the value of that attribute.  Otherwise it returns an array
of one or more objects of the form:

    {
      "jobid": "123.45",
      "classad": { (json-encoded classad object) }
    }

If `clusterid` and `procid` are specified, then the array will contain
a single job.  If only `clusterid` is specified, then the array will
contain all jobs within that cluster.  If none of these are specified,
the array will contain all jobs in the queue.

`projection` is one or more comma-separated attributes; if specified,
only those attributes, plus `clusterid` and `procid` will be in the
`classad` object of each job.  `projection` is ignored if `attribute`
is specified.

`constraint` is a classad expression restricting which jobs to include
in the result.  The constraint is always applied, even if `clusterid`
and `procid` are specified.

Returns 404 if no matching jobs are found.  This includes zero jobs
matching the constraint.


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
      "classad": { <classad object> }
    }

`name` is a specific host or slot to query.  If not specified, all
matching ads are returned.

`query` is the type of ad to query; see the "Query options" in the
condor_status(1) manpage.  "startd" is the default.

`projection` is one or more comma-separated attributes; if specified,
only those attributes, plus `name` and `procid` will be in the
`classad` object of each job.

`constraint` is a classad expression restricting which ads to include
in the result.

Returns 404 if no matching ads are found.  This includes zero ads
matching the constraint.
