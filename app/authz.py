from functools import wraps
from flask import abort
from flask_login import current_user, login_required
from app.models import companies


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if not any(current_user.has_role(role) for role in roles):
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def company_membership(company_id, manage=False):
    return companies.find_membership(company_id, current_user.id, manage)
