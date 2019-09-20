# stubs for classad
# TODO These should be moved to the Python bindings for HTCondor itself

from typing import Any

class ClassAd(dict):
    def printJson(self) -> str: ...
