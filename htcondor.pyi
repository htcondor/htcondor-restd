# stubs for htcondor
# TODO These should be moved to the Python bindings for HTCondor itself

import classad

from typing import Any, List, Optional, Union, Iterable, Tuple

class AdTypes:
    Generic: Any
    Accounting: Any
    Any: Any
    Collector: Any
    Credd: Any
    Defrag: Any
    Generic: Any
    Grid: Any
    HAD: Any
    License: Any
    Master: Any
    Negotiator: Any
    Schedd: Any
    Startd: Any
    Submitter: Any

class Collector:
    def __init__(self, pool: Union[str, List[str], None] = ...): ...
    def locate(self, daemon_type: DaemonTypes, name: str = ...): ...
    def query(
        self,
        ad_type: AdTypes = ...,
        constraint: str = ...,
        projection: List[str] = ...,
        statistics: List[str] = ...,
    ) -> List[classad.ClassAd]: ...

class DaemonTypes:
    Any: Any
    Master: Any
    Schedd: Any
    Startd: Any
    Collector: Any
    Negotiator: Any
    HAD: Any
    Generic: Any
    Credd: Any

class JobAction:
    Hold: Any
    Release: Any
    Suspend: Any
    Continue: Any
    Remove: Any
    RemoveX: Any
    Vacate: Any
    VacateFast: Any

class _Param: ...

class RemoteParam:
    def __init__(self, ad: classad.ClassAd): ...
    def __getitem__(self, key: str) -> Any: ...
    def get(self, key: str, default: Any = ...) -> Any: ...
    def setdefault(self, key: str, default: Any = ...) -> None: ...
    def update(self, E: Any, **F: Any) -> None: ...
    def keys(self) -> Iterable[str]: ...
    def items(self) -> Iterable[Tuple[str, Any]]: ...
    def values(self) -> Iterable[Any]: ...
    def refresh(self) -> None: ...

class Schedd:
    def __init__(self, location_ad: Optional[classad.ClassAd] = ...): ...
    def act(
        self, action: JobAction, job_spec: Union[List[str], str], reason: str = ...
    ) -> classad.ClassAd: ...
    def transaction(self) -> Transaction: ...

class Submit(dict):
    def queue(self, txn: Transaction) -> int: ...

class Transaction: ...

param: _Param

def reload_config() -> None: ...
