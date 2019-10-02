import re

import classad
import htcondor
import json

try:
    from typing import Dict, Any, Union, List
except ImportError:
    pass


def get_schedd(pool=None, schedd_name=None):
    if schedd_name:
        collector = htcondor.Collector(pool)
        return htcondor.Schedd(
            collector.locate(htcondor.DaemonTypes.Schedd, schedd_name)
        )
    else:
        return htcondor.Schedd()


def deep_lcasekeys(in_value):
    """Return a copy of a complex data structure where all keys
    in dictionaries are lowercased.

    """
    if isinstance(in_value, dict):
        out_value = dict()
        for k, v in in_value.items():
            k = k.lower()
            v = deep_lcasekeys(v)
            out_value[k] = v
        return out_value
    elif isinstance(in_value, (list, tuple)):
        return [deep_lcasekeys(x) for x in in_value]
    else:
        return in_value


def classads_to_dicts(classads):
    # type: (List[classad.ClassAd]) -> List[Dict]
    """Return a copy of a list of classads as a list of dicts, with all the keys lowercased, recursively."""
    return [deep_lcasekeys(json.loads(ad.printJson())) for ad in classads]


def validate_attribute(attribute):
    """Return True if the given attribute is a valid classad attribute name"""
    return bool(re.match(r"[A-Za-z_][A-Za-z0-9_]*$", attribute))


def validate_projection(projection):
    """Return True if the given projection has a valid format, i.e.
    is a comma-separated list of valid attribute names.
    """
    return all(validate_attribute(x) for x in projection.split(","))
