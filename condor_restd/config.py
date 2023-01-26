from __future__ import absolute_import

from flask_restful import Resource, reqparse, abort
import six

from htcondor import DaemonTypes, Collector, RemoteParam

import htcondor

from .errors import BAD_ATTRIBUTE, FAIL_QUERY, NO_ATTRIBUTE
from . import utils
from .auth import authorized

class V1ConfigResource(Resource):
    """Endpoints for accessing condor config; implements the /v1/config
    endpoints.

    """

    DAEMON_TYPES_MAP = {
        "collector": DaemonTypes.Collector,
        "master": DaemonTypes.Master,
        "negotiator": DaemonTypes.Negotiator,
        "schedd": DaemonTypes.Schedd,
        "startd": DaemonTypes.Startd,
    }

    @authorized
    def get(self, attribute=None):
        """GET handler"""
        parser = reqparse.RequestParser(trim=True)
        parser.add_argument("daemon", choices=list(self.DAEMON_TYPES_MAP.keys()))
        args = parser.parse_args()

        param = None
        if args.daemon:
            daemon_ad = None
            try:
                daemon_ad = Collector().locate(self.DAEMON_TYPES_MAP[args.daemon])
            except (IOError, RuntimeError) as err:
                abort(503, message=FAIL_QUERY % {"service": "collector", "err": err})
            try:
                param = RemoteParam(daemon_ad)
            except (IOError, RuntimeError) as err:
                abort(503, message=FAIL_QUERY % {"service": args.daemon, "err": err})
        else:
            htcondor.reload_config()
            param = htcondor.param

        param_lower = utils.deep_lcasekeys(param)

        if attribute:
            if not utils.validate_attribute(attribute):
                abort(400, message="%s: %s" % (BAD_ATTRIBUTE, attribute))

        if attribute:
            try:
                return param_lower[six.ensure_str(attribute).lower()]
            except KeyError:
                abort(404, message="%s: %s" % (NO_ATTRIBUTE, attribute))

        return param_lower
