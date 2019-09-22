from __future__ import absolute_import

try:
    from typing import Dict, List, Union

    Scalar = Union[None, bool, int, float, str]
except ImportError:
    pass

from flask_restful import Resource, abort, reqparse

from .errors import BAD_ATTRIBUTE_OR_PROJECTION, FAIL_QUERY, NO_JOBS, NO_ATTRIBUTE
from . import utils


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
    """Endpoints for accessing information about jobs in the queue;

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
