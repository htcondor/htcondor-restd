import os
from functools import wraps

import requests
from flask import request
from flask_restful import abort


# Checks whether you have the correct EE2 admin role and permissions to use this API
# A certain chat robot helped me write this decorator
# TODO: Might be nice to cache auth lookups, but this is an api with a low volume of requests
def authorized(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'kbase_session' in request.cookies:
            token = request.cookies.get("kbase_session")
            ret = requests.get(
                os.environ.get("AUTH_URL", "http://auth2:8080") + "/api/V2/me", headers={"Authorization": token}
            )
            ret.raise_for_status()  # this is a no-op if all is well
            user_info = ret.json()
            roles = user_info.get("customroles", [])
            if 'EE2_ADMIN_RO' not in roles and 'EE2_ADMIN' not in roles:
                abort(403, message="You do not have the EE2_ADMIN or EE2_ADMIN_RO auth role or are not logged in")
            # Go back to the get request
            return func(*args, **kwargs)
        else:
            abort(403, message="This api requires you to be logged in and have a kbase_session cookie")
    return wrapper
