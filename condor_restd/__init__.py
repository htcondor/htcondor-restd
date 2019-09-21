# -*- coding=utf-8 -*-
"""*** condor_restd.py ***
REST-based API for HTCondor, based on the HTCondor Python bindings.

Allows read-only queries for jobs (in-queue and historical),
configuration, and machine status.
"""
from __future__ import absolute_import
import re
import json

try:
    from typing import Dict, List, Optional, Union

    Scalar = Union[None, bool, int, float, str]
except ImportError:
    pass

import classad
import htcondor
from htcondor import AdTypes, Collector, DaemonTypes, RemoteParam

from flask import Flask
from flask_restful import Resource, Api, abort, reqparse

from . import utils


NO_JOBS = "No matching jobs"
NO_CLASSADS = "No matching classads"
NO_ATTRIBUTE = "Undefined attribute"
BAD_ATTRIBUTE_OR_PROJECTION = "Invalid attribute or projection"
FAIL_QUERY = "Error querying %(service)s: %(err)s"


app = Flask(__name__)
api = Api(app)


def validate_attribute(attribute):
    """Return True if the given attribute is a valid classad attribute name"""
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", attribute))


def validate_projection(projection):
    """Return True if the given projection has a valid format, i.e.
    is a comma-separated list of valid attribute names.
    """
    return all(validate_attribute(x) for x in projection.split(","))


class JobsBaseResource(Resource):
    """Base class for endpoints for accessing current and historical job
    information. This class must be overridden to specify `executable`.

    """

    querytype = None

    def _query_common(self, constraint, projection):
        # type: (str, str) -> List[Dict]
        schedd = utils.get_schedd()
        projection_list = []
        if projection:
            if not validate_projection(projection):
                abort(400, message=BAD_ATTRIBUTE_OR_PROJECTION)
            # We always need to get clusterid and procid even if the user doesn't
            # ask for it, so we can construct jobid
            projection_list = list(set(["clusterid", "procid"] + projection.split(",")))

        if self.querytype == "history":
            method = schedd.history
            service = "history file"
        elif self.querytype == "xquery":
            method = schedd.xquery
            service = "schedd"
        else:
            assert False, "Invalid querytype %r" % self.querytype

        try:
            classads = method(requirements=constraint, projection=projection_list)
            return utils.classads_to_dicts(classads)
        except RuntimeError as err:
            abort(503, message=FAIL_QUERY % {"service": service, "err": err})

    def query_multi(self, clusterid=None, constraint="true", projection=None):
        # type: (int, str, str) -> List[Dict]
        if clusterid is not None:
            constraint += " && clusterid==%d" % clusterid
        ad_dicts = self._query_common(constraint, projection)

        projection_list = projection.split(",") if projection else None
        data = []
        for ad in ad_dicts:
            jobid = "%(clusterid)s.%(procid)s" % ad
            if projection_list:
                if "clusterid" not in projection_list:
                    del ad["clusterid"]
                if "procid" not in projection_list:
                    del ad["procid"]
            data.append(dict(classad=ad, jobid=jobid))

        return data

    def query_single(self, clusterid, procid, projection=None):
        # type: (int, int, str) -> Dict
        ad_dicts = self._query_common(
            "clusterid==%d && procid==%d" % (clusterid, procid), projection
        )
        if ad_dicts:
            ad = ad_dicts[0]
            jobid = "%(clusterid)s.%(procid)s" % ad
            projection_list = projection.split(",") if projection else None
            if projection_list:
                if "clusterid" not in projection_list:
                    del ad["clusterid"]
                if "procid" not in projection_list:
                    del ad["procid"]
            return dict(classad=ad, jobid=jobid)
        else:
            abort(404, message=NO_JOBS)

    def query_attribute(self, clusterid, procid, attribute):
        # type: (int, int, str) -> Scalar
        q = self.query_single(clusterid, procid, projection=attribute)
        if not q:
            abort(404, message=NO_JOBS)
        l_attribute = attribute.lower()
        if l_attribute in q["classad"]:
            return q["classad"][l_attribute]
        else:
            abort(404, message=NO_ATTRIBUTE)

    def get(self, clusterid=None, procid=None, attribute=None):
        parser = reqparse.RequestParser(trim=True)
        parser.add_argument("projection", default="")
        parser.add_argument("constraint", default="true")
        args = parser.parse_args()
        if attribute:
            return self.query_attribute(clusterid, procid, attribute)
        if procid is not None:
            return self.query_single(clusterid, procid, projection=args.projection)
        return self.query_multi(
            clusterid, constraint=args.constraint, projection=args.projection
        )


class V1JobsResource(JobsBaseResource):
    """Endpoints for accessing information about jobs in the queue

    This implements the following endpoint:

        GET /v1/jobs{/clusterid}{/procid}{/attribute}{?projection,constraint}

        If `clusterid`, `procid`, and `attribute` are specified, then it
        returns the value of that attribute, or null if the attribute is
        missing or undefined.

        If `attribute` is not specified, job object(s) will be returned,
        which have the form:

            {
              "jobid": "123.45",
              "classad": { (json-encoded classad object) }
            }

        If `clusterid` and `procid` are specified, then the result will be a
        single job.  If only `clusterid` is specified, then the result will
        be an array of all jobs within that cluster.  If none of these are
        specified, the result will be an of all jobs in the queue.

        `projection` is one or more comma-separated attributes; if specified,
        only those attributes, plus `clusterid` and `procid` will be in the
        `classad` object of each job.  `projection` is ignored if `attribute`
        is specified.

        `constraint` is a classad expression restricting which jobs to include
        in the result.  The constraint is always applied, even if `clusterid`
        and `procid` are specified.

    """

    querytype = "xquery"


class V1HistoryResource(JobsBaseResource):
    """Endpoints for accessing historical job information

    This implements the following endpoint:

        GET /v1/history{/clusterid}{/procid}{/attribute}{?projection,constraint}

        If `clusterid`, `procid`, and `attribute` are specified, then it
        returns the value of that attribute.  Otherwise it returns an array
        of one or more objects of the form:

            {
              "jobid": "123.45",
              "classad": { (classad object) }
            }

        If `clusterid` and `procid` are specified, then the array will contain
        a single job.

        If only `clusterid` is specified, then the array will
        contain all jobs within that cluster.  If none of these are specified,
        the array will contain all jobs in the history.

        `projection` is one or more comma-separated attributes; if specified,
        only those attributes, plus `clusterid` and `procid` will be in the
        `classad` object of each job.  `projection` is ignored if `attribute`
        is specified.

        `constraint` is a classad expression restricting which jobs to include
        in the result.  The constraint is always applied, even if `clusterid`
        and `procid` are specified.

    """

    querytype = "history"


class V1StatusResource(Resource):
    """Endpoints for accessing condor_status information

    This implements the following endpoint:

        GET /v1/status{?projection,constraint,query}

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

    """

    AD_TYPES_MAP = {
        "accounting": AdTypes.Accounting,
        "any": AdTypes.Any,
        "collector": AdTypes.Collector,
        "credd": AdTypes.Credd,
        "defrag": AdTypes.Defrag,
        "generic": AdTypes.Generic,
        "grid": AdTypes.Grid,
        "had": AdTypes.HAD,
        "license": AdTypes.License,
        "master": AdTypes.Master,
        "negotiator": AdTypes.Negotiator,
        "schedd": AdTypes.Schedd,
        "startd": AdTypes.Startd,
        "submitter": AdTypes.Submitter,
    }

    def get(self, name=None):
        """GET handler"""
        parser = reqparse.RequestParser(trim=True)
        parser.add_argument("projection", default="")
        parser.add_argument("constraint", default="")
        parser.add_argument(
            "query", choices=list(self.AD_TYPES_MAP.keys()), default="any"
        )
        args = parser.parse_args()

        collector = Collector()
        ad_type = self.AD_TYPES_MAP[args.query]
        projection = []

        if args.projection:
            if not validate_projection(args.projection):
                abort(400, message=BAD_ATTRIBUTE_OR_PROJECTION)
            projection = args.projection.split(",")

        constraint = args.constraint
        if name:
            constraint = '(name == "%s")' % name
            if args.constraint:
                constraint += " && (%s)" % args.constraint

        classads = []  # type: List[classad.ClassAd]
        try:
            classads = collector.query(
                ad_type, constraint=constraint, projection=projection
            )
        except RuntimeError as err:
            abort(503, message=FAIL_QUERY % {"service": "collector", "err": err})
        if not classads:
            abort(404, message=NO_CLASSADS)
        data = [
            {"name": ad["name"], "classad": ad}
            for ad in utils.classads_to_dicts(classads)
        ]

        return data


class V1ConfigResource(Resource):
    """Endpoints for accessing condor config

    This implements the following endpoint:

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

    """

    DAEMON_TYPES_MAP = {
        "collector": DaemonTypes.Collector,
        "master": DaemonTypes.Master,
        "negotiator": DaemonTypes.Negotiator,
        "schedd": DaemonTypes.Schedd,
        "startd": DaemonTypes.Startd,
    }

    def get(self, attribute=None):
        """GET handler"""
        parser = reqparse.RequestParser(trim=True)
        parser.add_argument("daemon", choices=list(self.DAEMON_TYPES_MAP.keys()))
        args = parser.parse_args()

        if args.daemon:
            daemon_ad = Collector().locate(self.DAEMON_TYPES_MAP[args.daemon])
            param = RemoteParam(daemon_ad)
        else:
            htcondor.reload_config()
            param = htcondor.param

        param_lower = utils.deep_lcasekeys(param)

        if attribute:
            if not validate_attribute(attribute):
                abort(400, message=BAD_ATTRIBUTE_OR_PROJECTION)

        if attribute:
            try:
                return param_lower[attribute.lower()]
            except KeyError:
                abort(404, message=NO_ATTRIBUTE)

        return param_lower


class RootResource(Resource):
    def get(self):
        return {}


api.add_resource(RootResource, "/")


api.add_resource(
    V1JobsResource,
    "/v1/jobs",
    "/v1/jobs/<int:clusterid>",
    "/v1/jobs/<int:clusterid>/<int:procid>",
    "/v1/jobs/<int:clusterid>/<int:procid>/<attribute>",
)
api.add_resource(
    V1HistoryResource,
    "/v1/history",
    "/v1/history/<int:clusterid>",
    "/v1/history/<int:clusterid>/<int:procid>",
    "/v1/history/<int:clusterid>/<int:procid>/<attribute>",
)
api.add_resource(V1StatusResource, "/v1/status", "/v1/status/<name>")
api.add_resource(V1ConfigResource, "/v1/config", "/v1/config/<attribute>")

PUBLIC_ENDPOINTS = [
    "V1JobsResource",
    "V1ConfigResource",
    "V1HistoryResource",
    "V1StatusResource",
]
