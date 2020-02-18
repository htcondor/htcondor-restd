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
from .jobs import (
    V1GroupedJobsResource,
    V1GroupedHistoryResource,
    V1JobsResource,
    V1HistoryResource,
)
from .status import V1StatusResource, V1GroupedStatusResource


app = Flask(__name__)
api = Api(app)


class RootResource(Resource):
    def get(self):
        return {}


api.add_resource(RootResource, "/")


api.add_resource(
    V1JobsResource,
    "/v1/jobs/<schedd>",
    "/v1/jobs/<schedd>/<int:clusterid>",
    "/v1/jobs/<schedd>/<int:clusterid>/<int:procid>",
    "/v1/jobs/<schedd>/<int:clusterid>/<int:procid>/<attribute>",
)
api.add_resource(
    V1HistoryResource,
    "/v1/history/<schedd>",
    "/v1/history/<schedd>/<int:clusterid>",
    "/v1/history/<schedd>/<int:clusterid>/<int:procid>",
    "/v1/history/<schedd>/<int:clusterid>/<int:procid>/<attribute>",
)
api.add_resource(
    V1GroupedJobsResource,
    "/v1/grouped_jobs/<schedd>/<groupby>",
    "/v1/grouped_jobs/<schedd>/<groupby>/<int:clusterid>",
)
api.add_resource(
    V1GroupedHistoryResource,
    "/v1/grouped_history/<schedd>/<groupby>",
    "/v1/grouped_history/<schedd>/<groupby>/<int:clusterid>",
)
api.add_resource(V1StatusResource, "/v1/status", "/v1/status/<name>")
api.add_resource(
    V1GroupedStatusResource,
    "/v1/grouped_status/<groupby>",
    "/v1/grouped_status/<groupby>/<name>",
)
api.add_resource(V1ConfigResource, "/v1/config", "/v1/config/<attribute>")
