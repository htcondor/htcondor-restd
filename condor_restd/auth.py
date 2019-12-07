from installed_clients.execution_engine2Client import execution_engine2
from flask_restful import Resource, reqparse, abort
import os

def allowed_access():
    """
    # TODO Make this method more concise, but lets keep it this way until auth is ironed out

    Check the request headers or session cookies to check if you are allowed to access the service.

    :return: {"is_admin" : True or False, "permission" : "r|w|None"
    """
    parser = reqparse.RequestParser(trim=True)
    parser.add_argument('Authentication', location='headers')
    parser.add_argument('Authorization', location='headers')
    parser.add_argument('kbase_session', location='cookies')
    parser.add_argument('kbase_session_backup', location='cookies')
    args = parser.parse_args()

    token = None
    for item in ("Authentication", "Authorization", "kbase_session", "kbase_session_backup"):
        if args.get(item) is not None:
            token = args.get(item)
            break

    if token is not None:

        url = os.environ.get('ee2_url', 'https://ci.kbase.us/services/ee2')
        ee2 = execution_engine2(url=url, token=token)
        try:
            if ee2.is_admin() is 1:
                permission = ee2.get_admin_permission().get("permission")
                if permission not in ['r', 'w']:
                    return {'is_admin': False,
                            'error': "Programming error. Somehow you are an admin, but don't have R|W",
                            'url': url, 'token': token,
                            'exception': f"{e}", 'permission': permission}

                return {'is_admin': True, 'permission': permission}
            else:
                return {'is_admin': False,
                        'msg': "Sorry, you are not an ee2 admin. Please request an auth role"}

        except Exception as e:
            return {'is_admin': False,
                    'error': "Couldn't check admin status", 'url': url, 'token': token,
                    'exception': f"{e}"}
    else:
        return {
            'is_admin': False,
            'msg': 'You must provide an authorization header or be logged in to KBase and have a session cookie',
            'Authentication': args.get("Authentication"),
            'Authorization': args.get("Authorization"),
            'kbase_session': args.get("kbase_session"),
            'kbase_session_backup': args.get("kbase_session_backup")
        }