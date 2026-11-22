from app.database import write_transaction
from app.models import administration as model


def _check_admin(actor_id):
    actor = model.administrator_account(actor_id)
    if actor is None or not actor.is_active_account or not actor.is_admin:
        raise PermissionError("An active administrator is required.")


def toggle_account_status(actor_id, user_id):
    with write_transaction():
        model.lock_admin_changes()
        _check_admin(actor_id)
        target = model.administrator_account(user_id)
        if target is None:
            return False
        if user_id == actor_id:
            raise ValueError("You cannot disable your own administrator account.")
        if target.is_admin and target.is_active_account and model.count_active_admins() <= 1:
            raise ValueError("At least one active administrator must remain.")
        model.toggle_user_active(user_id)
    return True


def change_role(actor_id, user_id, role_id, action):
    if action not in {"add", "remove"}:
        raise ValueError("Choose a valid role action.")
    params = {"user_id": user_id, "role_id": role_id}
    with write_transaction():
        model.lock_admin_changes()
        _check_admin(actor_id)
        role = model.find_role_assignment(params)
        if role is None:
            return False
        if action == "add":
            model.insert_role_assignment(params)
        elif role.assigned:
            if role.role_count == 1:
                raise ValueError("Every user must have at least one role.")
            target = model.administrator_account(user_id)
            if role.name == "admin" and target.is_active_account and model.count_active_admins() <= 1:
                raise ValueError("At least one active administrator must remain.")
            if user_id == actor_id and role.name == "admin":
                raise ValueError("You cannot remove your own administrator role.")
            model.remove_role_assignment(params)
    return True
