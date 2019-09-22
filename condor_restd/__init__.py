# -*- coding=utf-8 -*-
"""*** condor_restd.py ***
REST-based API for HTCondor, based on the HTCondor Python bindings.

Allows read-only queries for jobs (in-queue and historical),
configuration, and machine status.
"""
from __future__ import absolute_import


try:
    from typing import Dict, List, Optional, Union

    Scalar = Union[None, bool, int, float, str]
except ImportError:
    pass

from flask import Flask
from flask_restful import Resource, Api

from .config import V1ConfigResource
from .jobs import V1JobsResource, V1HistoryResource
from .status import V1StatusResource


app = Flask(__name__)
api = Api(app)


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
