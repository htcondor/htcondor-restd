NO_JOBS = "No matching jobs"
NO_CLASSADS = "No matching classads"
NO_ATTRIBUTE = "Undefined attribute"
BAD_ATTRIBUTE = "Invalid attribute"
BAD_PROJECTION = "Invalid attribute(s) in projection"
BAD_GROUPBY = "Invalid attribute for grouping"
FAIL_QUERY = "Error querying %(service)s: %(err)s"


class DaemonNotFound(Exception):
    pass


class ScheddNotFound(DaemonNotFound):
    pass
