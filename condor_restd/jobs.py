from __future__ import absolute_import

try:
    from typing import Dict, List, Union

    Scalar = Union[None, bool, int, float, str]
except ImportError:
    pass

import six

from flask_restful import Resource, abort, reqparse

from .errors import BAD_ATTRIBUTE_OR_PROJECTION, FAIL_QUERY, NO_JOBS, NO_ATTRIBUTE
from . import utils


class JobsBaseResource(Resource):
    """Base class for endpoints for accessing current and historical job
    information. This class must be overridden to specify `querytype`.

    """

    querytype = None

    def _query_common(self, constraint, projection):
        # type: (str, str) -> List[Dict]
        """Return the result of a schedd or history file query with a
        constraint (classad expression) and a projection (comma-separated
        attributes), as a list of dicts.

        Handles getting the schedd, validating args, calling the query, and
        transforming the classads into plain dicts (which can be serialized).

        Aborts with a 400 if the args are bad, and a 503 if the query failed.

        """
        schedd = utils.get_schedd()
        projection_list = []
        if projection:
            if not utils.validate_projection(projection):
                abort(400, message=BAD_ATTRIBUTE_OR_PROJECTION)
            # We always need to get clusterid and procid even if the user doesn't
            # ask for it, so we can construct jobid
            projection_list = list(
                set(["clusterid", "procid"] + projection.lower().split(","))
            )

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
        except SyntaxError as err:
            abort(400, message=str(err))
        except RuntimeError as err:
            abort(503, message=FAIL_QUERY % {"service": service, "err": err})

    def query_multi(self, clusterid=None, constraint="true", projection=None):
        # type: (int, str, str) -> List[Dict]
        """Return multiple jobs, optionally constraining by `clusterid` in
        addition to `constraint`.

        """
        if clusterid is not None:
            constraint += " && clusterid==%d" % clusterid
        ad_dicts = self._query_common(constraint, projection)

        projection_list = projection.lower().split(",") if projection else None
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
        """Return a single job."""
        ad_dicts = self._query_common(
            "clusterid==%d && procid==%d" % (clusterid, procid), projection
        )
        if ad_dicts:
            ad = ad_dicts[0]
            jobid = "%(clusterid)s.%(procid)s" % ad
            projection_list = projection.lower().split(",") if projection else None
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
        """Return a single attribute."""
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
        try:
            projection = six.ensure_str(args.projection)
            constraint = six.ensure_str(args.constraint)
        except UnicodeError as err:
            abort(400, message=str(err))
            return  # quiet warning
        if attribute:
            try:
                attribute = six.ensure_str(attribute)
            except UnicodeError as err:
                abort(400, message=str(err))
            return self.query_attribute(clusterid, procid, attribute)
        if procid is not None:
            return self.query_single(clusterid, procid, projection=projection)
        return self.query_multi(
            clusterid, constraint=constraint, projection=projection
        )


class V1JobsResource(JobsBaseResource):
    """Endpoints for accessing information about jobs in the queue; implements
    the /v1/jobs endpoints.

    """

    querytype = "xquery"


class V1HistoryResource(JobsBaseResource):
    """Endpoints for accessing historical job information; implements the
    /v1/history endpoints.

    """

    querytype = "history"
