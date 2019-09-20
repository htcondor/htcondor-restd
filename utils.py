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


def deep_lcasekeys(dictish):
    # type: (Union[Dict[str, Any],htcondor.RemoteParam, htcondor._Param]) -> Dict
    """Return a copy of a dictionary with all the keys lowercased, recursively."""
    transformed_dict = dict()
    for k, v in dictish.items():
        k = k.lower()
        if isinstance(v, dict):
            v = deep_lcasekeys(v)
        transformed_dict[k] = v
    return transformed_dict


def classads_to_dicts(classads):
    # type: (List[classad.ClassAd]) -> List[Dict]
    """Return a copy of a list of classads as a list of dicts, with all the keys lowercased, recursively."""
    return [deep_lcasekeys(json.loads(ad.printJson())) for ad in classads]
