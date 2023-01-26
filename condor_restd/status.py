from __future__ import absolute_import

from collections import defaultdict

try:
    from typing import Dict, List, Optional
except ImportError:
    pass

from flask_restful import Resource, reqparse, abort
import six

from htcondor import AdTypes, Collector
from classad import ClassAd

from .errors import BAD_GROUPBY, BAD_PROJECTION, FAIL_QUERY, NO_CLASSADS
from . import utils
from .auth import authorized


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


class V1StatusResource(Resource):
    """Endpoints for accessing condor_status information; implements the
    /v1/status endpoints.

    """
    @authorized
    def get(self, name=None):
        """GET handler"""
        parser = reqparse.RequestParser(trim=True)
        parser.add_argument("projection", default="")
        parser.add_argument("constraint", default="")
        parser.add_argument("query", choices=list(AD_TYPES_MAP.keys()), default="any")
        args = parser.parse_args()
        try:
            projection = six.ensure_str(args.projection, errors="replace")
            constraint = six.ensure_str(args.constraint, errors="replace")
            if name is not None:
                name = six.ensure_str(name, errors="replace")
        except UnicodeError as err:
            abort(400, message=str(err))
            return  # quiet warning

        collector = Collector()
        ad_type = AD_TYPES_MAP[args.query]
        projection_list = query_projection_list = []

        if projection:
            valid, badattrs = utils.validate_projection(projection)
            if not valid:
                abort(400, message="%s: %s" % (BAD_PROJECTION, ", ".join(badattrs)))
            projection_list = projection.lower().split(",")
            # We need 'name' and 'mytype' in the projection to extract it from the classad
            query_projection_list = list(set(["name", "mytype"] + projection_list))

        constraint = constraint or "true"
        if name:
            constraint += ' && (name == "%s")' % name

        classads = []  # type: List[ClassAd]
        try:
            classads = collector.query(
                ad_type, constraint=constraint, projection=query_projection_list
            )
        except SyntaxError as err:
            abort(400, message=str(err))
        except (IOError, RuntimeError) as err:
            abort(503, message=FAIL_QUERY % {"service": "collector", "err": err})
        if not classads:
            return []
        data = []
        ad_dicts = utils.classads_to_dicts(classads)
        for ad in ad_dicts:
            name = ad["name"]
            type_ = ad["mytype"]
            if projection_list:
                if "name" not in projection_list:
                    del ad["name"]
                if "mytype" not in projection_list:
                    del ad["mytype"]
            data.append(dict(classad=ad, name=name, type=type_))

        return data


class V1GroupedStatusResource(Resource):
    """Endpoints for accessing condor_status information, grouped by
    an attribute; implements the /v1/grouped_status endpoints.

    """

    @authorized
    def get(self, groupby, name=None):
        # type: (str, Optional[str]) -> Dict[str, List[Dict]]
        """GET handler

        Return multiple resources grouped by `groupby`.
        """
        parser = reqparse.RequestParser(trim=True)
        parser.add_argument("projection", default="")
        parser.add_argument("constraint", default="")
        parser.add_argument("query", choices=list(AD_TYPES_MAP.keys()), default="any")
        args = parser.parse_args()
        projection = None
        constraint = None
        try:
            projection = six.ensure_str(args.projection, errors="replace")
            constraint = six.ensure_str(args.constraint, errors="replace")
            groupby = six.ensure_str(groupby, errors="replace")
            if name is not None:
                name = six.ensure_str(name, errors="replace")
        except UnicodeError as err:
            abort(400, message=str(err))

        if not utils.validate_attribute(groupby):
            abort(400, message=BAD_GROUPBY)

        collector = Collector()
        ad_type = AD_TYPES_MAP[args.query]
        projection_list = query_projection_list = []

        if projection:
            valid, badattrs = utils.validate_projection(projection)
            if not valid:
                abort(400, message="%s: %s" % (BAD_PROJECTION, ", ".join(badattrs)))
            projection_list = projection.lower().split(",")
            # We need 'name' and 'mytype' in the projection to extract it from the classad
            query_projection_list = list(
                set(["name", "mytype", groupby] + projection_list)
            )

        constraint = constraint or "true"
        if name:
            constraint += ' && (name == "%s")' % name

        classads = []  # type: List[ClassAd]
        try:
            classads = collector.query(
                ad_type, constraint=constraint, projection=query_projection_list
            )
        except SyntaxError as err:
            abort(400, message=str(err))
        except (IOError, RuntimeError) as err:
            abort(503, message=FAIL_QUERY % {"service": "collector", "err": err})
        if not classads:
            return {}
        grouped_data = defaultdict(list)
        ad_dicts = utils.classads_to_dicts(classads)
        groupby = groupby.lower()
        for ad in ad_dicts:
            name = ad["name"]
            type_ = ad["mytype"]
            if projection_list:
                for key in ["name", "mytype"]:
                    if key not in projection_list and key != groupby:
                        del ad[key]

            # I can't make the JSON encoder use `null` as a key so there's no
            # good way to include the resources where groupby is undefined.
            # Skip them.
            try:
                key = ad[groupby]
                grouped_data[key].append(dict(classad=ad, name=name, type=type_))
            except KeyError:
                pass

        return grouped_data
