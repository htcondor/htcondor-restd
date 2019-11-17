from __future__ import absolute_import

try:
    from typing import Dict, List, Union

    Scalar = Union[None, bool, int, float, str]
except ImportError:
    pass

import six

from flask_restful import Resource, abort, reqparse
import logging
logging.basicConfig(level=logging.INFO)

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
        except (IOError, RuntimeError) as err:
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

    
    def allowed_access(self):
        """
        Check the request headers or session cookies to check if you are allowed to access the service
        :return:
        """
        parser = reqparse.RequestParser(trim=True)
        parser.add_argument('Authentication', location='headers')
        parser.add_argument('Authorization', location='headers')
        parser.add_argument('kbase_session', location='cookies')
        parser.add_argument('kbase_session_backup', location='cookies')
        args = parser.parse_args()

        token = None
        for item in ("Authentication", "Authorization", "kbase_session", "kbase_session_backup"):
            if args.get(item) is not None:
                token = args.get(item)
                break

        if token is not None:
            from installed_clients.execution_engine2Client import execution_engine2
            import os
            url = os.environ.get('ee2_url', 'https://ci.kbase.us/services/ee2')
            ee2 = execution_engine2(url=url, token=token)
            try:
                if ee2.is_admin() is 1:
                    return {'is_admin': True}
                else:
                    return {'is_admin': False,
                            'msg': "Sorry, you are not an ee2 admin. Please request an auth role"}

            except Exception as e:
                return {'is_admin': False,
                        'error': "Couldn't check admin status", 'url': url, 'token': token,
                        'tt': type(token), 'exception': f"{e}"}
        else:
            return {
                'is_admin' : False,
                'msg': 'You must provide an authorization header or be logged in to KBase and have a session cookie',
                'Authentication': args.get("Authentication"),
                'Authorization': args.get("Authorization"),
                'kbase_session': args.get("kbase_session"),
                'kbase_session_backup': args.get("kbase_session_backup")
            }

    def filter_classads(self, classads):
        """
        Remove attributes that you do not want the service to expose

        :param classads: The classads to filter
        :return: The filtered classads
        """
        # redacted = ['environment','env']
        for i, item in enumerate(classads):
            classads[i]['classad']['environment'] = 'redacted'
            classads[i]['classad']['env'] = 'redacted'
        return classads



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

        aa = self.allowed_access()
        is_admin = aa['is_admin']
        if is_admin is not True:
            return aa

        if attribute:
            try:
                attribute = six.ensure_str(attribute)
            except UnicodeError as err:
                abort(400, message=str(err))
            qa = self.query_attribute(clusterid, procid, attribute)
            return self.filter_classads(qa)
        if procid is not None:
            qs = self.query_single(clusterid, procid, projection=projection)
            return self.filter_classads(qs)

        qm = self.query_multi(
            clusterid, constraint=constraint, projection=projection
        )
        return self.filter_classads(qm)



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
