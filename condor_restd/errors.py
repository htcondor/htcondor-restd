NO_JOBS = "No matching jobs"
NO_CLASSADS = "No matching classads"
NO_ATTRIBUTE = "Undefined attribute"
BAD_ATTRIBUTE_OR_PROJECTION = "Invalid attribute or projection"
FAIL_QUERY = "Error querying %(service)s: %(err)s"


class DaemonNotFound(Exception):
    pass


class ScheddNotFound(DaemonNotFound):
    pass
