from __future__ import absolute_import

from collections import defaultdict

try:
    from typing import Dict, List, Optional, Union

    Scalar = Union[None, bool, int, float, str]
except ImportError:
    pass

import six

from flask_restful import Resource, abort, reqparse
import classad
import htcondor

from .errors import (
    BAD_ATTRIBUTE,
    BAD_PROJECTION,
    BAD_GROUPBY,
    FAIL_QUERY,
    NO_JOBS,
    NO_ATTRIBUTE,
    ScheddNotFound,
)
from . import utils
from .auth import authorized


def _query_common(querytype, schedd_name, constraint, projection, limit=None):
    # type: (str, Optional[str], str, Optional[str], Optional[int]) -> List[Dict]
    """Return the result of a schedd or history file query with a
    constraint (classad expression) and a projection (comma-separated
    attributes), as a list of dicts.

    Handles getting the schedd, validating args, calling the query, and
    transforming the classads into plain dicts (which can be serialized).

    Aborts with a 400 if the args are bad, and a 503 if the query failed.

    """
    try:
        schedd = utils.get_schedd(schedd_name=schedd_name)
    except ScheddNotFound:
        abort(400, message="Schedd not found: %s" % schedd_name)
        raise  # quiet warning
    except IOError as err:
        abort(503, message=FAIL_QUERY % {"service": "collector", "err": err})
        raise  # quiet warning

    projection_list = []  # type: List[str]
    if projection:
        valid, badattrs = utils.validate_projection(projection)
        if not valid:
            abort(400, message="%s: %s" % (BAD_PROJECTION, ", ".join(badattrs)))
        # We always need to get clusterid and procid even if the user doesn't
        # ask for it, so we can construct jobid
        projection_list = list(
            set(["clusterid", "procid"] + projection.lower().split(","))
        )

    restd_max_jobs = htcondor.param.get("RESTD_MAX_JOBS", None)
    max_limit = -1
    try:
        if restd_max_jobs is not None:
            max_limit = max(int(restd_max_jobs), -1)
    except TypeError:
        abort(503, message="Bad value for RESTD_MAX_JOBS: %s" % restd_max_jobs)

    if limit is None:
        limit = max_limit
    else:
        try:
            limit = int(limit)
        except TypeError:
            abort(400, message="Bad value for limit: %s" % limit)
        if limit < 0:
            limit = max_limit
        elif max_limit > -1 and limit > max_limit:
            limit = max_limit

    restd_hide_job_attrs = htcondor.param.get("RESTD_HIDE_JOB_ATTRS", "")
    restd_hide_job_attrs_list = utils.str_to_list(str(restd_hide_job_attrs).lower())

    service = ""
    try:
        # history query uses "match", jobs query uses "limit"
        if querytype == "history":
            service = "history file"
            classads = schedd.history(
                requirements=constraint, projection=projection_list, match=limit
            )  # type: List[classad.ClassAd]
        elif querytype == "xquery":
            service = "schedd"
            classads = schedd.xquery(
                requirements=constraint, projection=projection_list, limit=limit
            )  # type: List[classad.ClassAd]
        else:
            assert False, "Invalid querytype %r" % querytype
        classad_dicts = utils.classads_to_dicts(classads)
        for ad in classad_dicts:
            for attr in restd_hide_job_attrs_list:
                if attr in ad:
                    ad[attr] = "<REDACTED>"
        return classad_dicts
    except SyntaxError as err:
        abort(400, message=str(err))
    except (IOError, RuntimeError) as err:
        abort(503, message=FAIL_QUERY % {"service": service, "err": err})


class JobsBaseResource(Resource):
    """Base class for endpoints for accessing current and historical job
    information. This class must be overridden to specify `querytype`.

    """

    querytype = ""

    def query_multi(self, schedd, clusterid=None, constraint="true", projection=None):
        # type: (Optional[str], int, str, str) -> List[Dict]
        """Return multiple jobs, optionally constraining by `clusterid` in
        addition to `constraint`.

        """
        if clusterid is not None:
            constraint += " && clusterid==%d" % clusterid
        ad_dicts = _query_common(
            self.querytype,
            schedd_name=schedd,
            constraint=constraint,
            projection=projection,
            limit=None,
        )

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

    def query_single(self, schedd, clusterid, procid, projection=None):
        # type: (Optional[str], int, int, str) -> Dict
        """Return a single job."""
        ad_dicts = _query_common(
            self.querytype,
            schedd,
            "clusterid==%d && procid==%d" % (clusterid, procid),
            projection,
            limit=1,
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

    def query_attribute(self, schedd, clusterid, procid, attribute):
        # type: (Optional[str], int, int, str) -> Scalar
        """Return a single attribute."""
        q = self.query_single(schedd, clusterid, procid, projection=attribute)
        if not q:
            abort(404, message=NO_JOBS)
        l_attribute = attribute.lower()
        if l_attribute in q["classad"]:
            return q["classad"][l_attribute]
        else:
            abort(404, message=NO_ATTRIBUTE)

    @authorized
    def get(self, schedd, clusterid=None, procid=None, attribute=None):
        parser = reqparse.RequestParser(trim=True)
        parser.add_argument("projection", default="")
        parser.add_argument("constraint", default="true")
        args = parser.parse_args()
        try:
            schedd = six.ensure_str(schedd, errors="replace")
            projection = six.ensure_str(args.projection, errors="replace")
            constraint = six.ensure_str(args.constraint, errors="replace")
        except UnicodeError as err:
            abort(400, message=str(err))
            return  # quiet warning
        if schedd == "DEFAULT":
            schedd = None
        if attribute:
            try:
                attribute = six.ensure_str(attribute, errors="replace")
            except UnicodeError as err:
                abort(400, message=str(err))
            return self.query_attribute(schedd, clusterid, procid, attribute)
        if procid is not None:
            return self.query_single(schedd, clusterid, procid, projection=projection)
        return self.query_multi(
            schedd, clusterid, constraint=constraint, projection=projection
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


class GroupedJobsBaseResource(Resource):
    """Base class for endpoints for accessing current and historical job
    information, grouped by an attribute. This class must be overridden
    to specify `querytype`.

    """

    querytype = ""

    def grouped_query_multi(
        self, schedd, groupby, clusterid=None, constraint="true", projection=None
    ):
        # type: (Optional[str], str, int, str, str) -> Dict[str, List[Dict]]
        """Return multiple jobs grouped by `groupby`, optionally constraining
        by `clusterid` in addition to `constraint`.

        Jobs where the `groupby` attribute is undefined are omitted from
        the result.

        """
        if not utils.validate_attribute(groupby):
            abort(400, message=BAD_GROUPBY)
        if clusterid is not None:
            constraint += " && clusterid==%d" % clusterid
        if projection:
            projection += "," + groupby
        ad_dicts = _query_common(
            self.querytype,
            schedd_name=schedd,
            constraint=constraint,
            projection=projection,
            limit=None,
        )

        projection_list = projection.lower().split(",") if projection else None
        grouped_data = defaultdict(list)
        groupby = groupby.lower()
        for ad in ad_dicts:
            jobid = "%(clusterid)s.%(procid)s" % ad
            if projection_list:
                for key in "clusterid", "procid":
                    if key not in projection_list and key != groupby:
                        del ad[key]

            key = ad.get(groupby, None)
            if key is not None:
                grouped_data[key].append(dict(classad=ad, jobid=jobid))

        return grouped_data

    @authorized
    def get(self, schedd, groupby, clusterid=None):
        parser = reqparse.RequestParser(trim=True)
        parser.add_argument("projection", default="")
        parser.add_argument("constraint", default="true")
        args = parser.parse_args()
        try:
            schedd = six.ensure_str(schedd, errors="replace")
            groupby = six.ensure_str(groupby, errors="replace")
            projection = six.ensure_str(args.projection, errors="replace")
            constraint = six.ensure_str(args.constraint, errors="replace")
        except UnicodeError as err:
            abort(400, message=str(err))
            return  # quiet warning
        if schedd == "DEFAULT":
            schedd = None
        return self.grouped_query_multi(
            schedd, groupby, clusterid, constraint=constraint, projection=projection
        )


class V1GroupedJobsResource(GroupedJobsBaseResource):
    """Endpoints for accessing grouped information about jobs in the queue; implements
    the /v1/grouped_jobs endpoints.

    """

    querytype = "xquery"


class V1GroupedHistoryResource(GroupedJobsBaseResource):
    """Endpoints for accessing grouped_historical job information; implements the
    /v1/grouped_history endpoints.

    """

    querytype = "history"
