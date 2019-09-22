from __future__ import absolute_import

try:
    from typing import List
except ImportError:
    pass

from flask_restful import Resource, reqparse, abort

from htcondor import AdTypes, Collector
from classad import ClassAd

from .errors import BAD_ATTRIBUTE_OR_PROJECTION, FAIL_QUERY, NO_CLASSADS
from . import utils


class V1StatusResource(Resource):
    """Endpoints for accessing condor_status information; implements the
    /v1/status endpoints.

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
        projection_list = query_projection_list = []

        if args.projection:
            if not utils.validate_projection(args.projection):
                abort(400, message=BAD_ATTRIBUTE_OR_PROJECTION)
            projection_list = args.projection.lower().split(",")
            # We need 'name' and 'mytype' in the projection to extract it from the classad
            query_projection_list = list(set(["name", "mytype"] + projection_list))

        constraint = args.constraint
        if name:
            constraint = '(name == "%s")' % name
            if args.constraint:
                constraint += " && (%s)" % args.constraint

        classads = []  # type: List[ClassAd]
        try:
            classads = collector.query(
                ad_type, constraint=constraint, projection=query_projection_list
            )
        except SyntaxError as err:
            abort(400, message=str(err))
        except RuntimeError as err:
            abort(503, message=FAIL_QUERY % {"service": "collector", "err": err})

        if not classads:
            abort(404, message=NO_CLASSADS)

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
