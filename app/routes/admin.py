
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from psycopg import IntegrityError
from app.clock import local_today
from app.authz import roles_required
from app.models import administration, jobs as job_model
from app.services.administration import change_role, toggle_account_status
from app.services.jobs import POSTING_STATUSES
from app.forms import text_field

admin_bp = Blueprint("admin", __name__)


def catalog_table(kind):
    table = {"category": "job_categories", "skill": "skills"}.get(kind)
    if table is None:
        abort(404)
    return table


def catalog_fields(kind):
    return (text_field(request.form, "name", 100 if kind == "category" else 80, required=True),
            text_field(request.form, "detail", 255 if kind == "category" else 80))


@admin_bp.get("/dashboard")
@roles_required("admin")
def dashboard():
    stats = administration.dashboard_counts(local_today())
    category_stats = administration.category_counts()
    return render_template("admin/dashboard.html", stats=stats, category_stats=category_stats)


@admin_bp.get("/employments")
@roles_required("admin")
def employments():
    today = local_today()
    try:
        search = text_field(request.args, "q", 160) or ""
    except ValueError:
        flash("Enter a search term of at most 160 characters.", "warning")
        return redirect(url_for("admin.employments"))
    status = request.args.get("status", "current")
    if status not in {"current", "past"}:
        status = "all"
    employments = administration.search_employments(search, status, today)
    summary = administration.employment_summary(today)
    return render_template("admin/employments.html", employments=employments,
                           summary=summary, search=search, status=status, today=today)


@admin_bp.get("/database")
@roles_required("admin")
def database_browser():
    """Provide a safe, read-only view of the PostgreSQL public schema."""
    table_names = administration.list_table_names()
    selected_table = request.args.get("table")

    if selected_table not in table_names:
        selected_table = None

    table_counts = {}
    for table_name in table_names:
        table_counts[table_name] = administration.count_table_rows(table_name)

    columns = []
    rows = []

    if selected_table:
        columns = administration.list_table_columns(selected_table)
        rows = administration.list_table_rows(selected_table, columns)

    return render_template(
        "admin/database.html",
        table_names=table_names,
        table_counts=table_counts,
        selected_table=selected_table,
        columns=columns,
        rows=rows,
    )


@admin_bp.route("/users", methods=["GET", "POST"])
@roles_required("admin")
def users():
    if request.method == "POST":
        user_id = request.form.get("user_id", type=int)
        try:
            if not toggle_account_status(current_user.id, user_id):
                abort(404)
        except PermissionError:
            abort(403)
        except ValueError as exc:
            flash(str(exc), "warning")
        else:
            flash("User status updated.", "success")
        return redirect(url_for("admin.users"))
    users = administration.list_users()
    roles = administration.list_roles()
    return render_template("admin/users.html", users=users, roles=roles)


@admin_bp.post("/users/<int:user_id>/roles")
@roles_required("admin")
def user_roles(user_id):
    try:
        if not change_role(current_user.id, user_id, request.form.get("role_id", type=int), request.form.get("action")):
            abort(404)
    except PermissionError:
        abort(403)
    except ValueError as exc:
        flash(str(exc), "warning")
    else:
        flash("Roles updated.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.get("/companies")
@roles_required("admin")
def companies():
    companies = administration.list_companies()
    employee_counts = dict(administration.count_employees_by_company(local_today()))
    return render_template("admin/companies.html", companies=companies,
                           employee_counts=employee_counts)


@admin_bp.get("/companies/<int:company_id>")
@roles_required("admin")
def company_detail(company_id):
    params = {"id": company_id}
    company = administration.find_company_overview(params)
    if company is None:
        abort(404)
    employments = administration.company_employments(company_id, company.name)
    staff = administration.list_company_staff(params)
    today = local_today()
    current = [item for item in employments if not item.end_date or item.end_date >= today]
    past = [item for item in employments if item.end_date and item.end_date < today]
    return render_template("admin/company_detail.html", company=company, staff=staff,
                           current_employments=current, past_employments=past, today=today,
                           application_count=company.application_count)


@admin_bp.post("/companies/<int:company_id>/verify")
@roles_required("admin")
def verify_company(company_id):
    changed = administration.toggle_company_verified(company_id)
    if changed is None:
        abort(404)
    return redirect(url_for("admin.companies"))


@admin_bp.get("/jobs")
@roles_required("admin")
def jobs():
    jobs = administration.list_postings()
    return render_template("admin/jobs.html", jobs=jobs, statuses=POSTING_STATUSES)


@admin_bp.post("/jobs/<int:job_id>/moderate")
@roles_required("admin")
def moderate_job(job_id):
    status = request.form.get("status")
    if status not in POSTING_STATUSES:
        flash("Choose a valid posting status.", "danger")
        return redirect(url_for("admin.jobs"))
    changed = administration.update_posting_status(job_id, status, local_today())
    if changed is None:
        flash("The posting could not be updated. Opening a posting requires a verified company and a valid deadline.", "warning")
    else:
        flash("Posting status updated.", "success")
    return redirect(url_for("admin.jobs"))


@admin_bp.route("/catalog", methods=["GET", "POST"])
@roles_required("admin")
def catalog():
    if request.method == "POST":
        kind = request.form.get("kind")
        table = catalog_table(kind)
        try:
            name, detail = catalog_fields(kind)
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("admin.catalog"))

        duplicate = administration.catalog_name_exists(table, name)
        if duplicate:
            flash(f"'{name}' already exists in the catalog.", "warning")
            return redirect(url_for("admin.catalog"))

        try:
            administration.insert_catalog_item(table, name, detail)
            flash("Catalog item added.", "success")
        except IntegrityError:
            flash(f"'{name}' already exists in the catalog.", "warning")
        return redirect(url_for("admin.catalog"))
    return render_template(
        "admin/catalog.html",
        categories=administration.list_catalog_categories(),
        skills=job_model.skill_catalog(),
    )


@admin_bp.post("/catalog/<kind>/<int:item_id>/rename")
@roles_required("admin")
def rename_catalog_item(kind, item_id):
    table = catalog_table(kind)
    if administration.find_catalog_id(table, item_id) is None:
        abort(404)
    try:
        name, detail = catalog_fields(kind)
    except ValueError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("admin.catalog"))

    params = {"name": name, "id": item_id, "detail": detail, "set_detail": "detail" in request.form}
    duplicate = administration.catalog_name_used_by_another(table, params)
    if duplicate:
        flash(f"'{name}' already exists in the catalog.", "warning")
        return redirect(url_for("admin.catalog"))

    try:
        administration.update_catalog_name(table, params)
        flash("Catalog item renamed.", "success")
    except IntegrityError:
        flash(f"'{name}' already exists in the catalog.", "warning")

    return redirect(url_for("admin.catalog"))


@admin_bp.post("/catalog/<kind>/<int:item_id>/delete")
@roles_required("admin")
def delete_catalog_item(kind, item_id):
    table = catalog_table(kind)
    params = {"id": item_id}
    item_name = administration.find_catalog_name(table, params)
    if item_name is None:
        abort(404)

    if kind == "category" and administration.category_has_postings(params):
        flash(
            f"'{item_name}' cannot be deleted because it is used by job postings.",
            "warning",
        )
        return redirect(url_for("admin.catalog"))

    try:
        administration.remove_catalog_item(table, params)
        flash(f"'{item_name}' deleted.", "success")
    except IntegrityError:
        flash(f"'{item_name}' is in use and cannot be deleted.", "warning")

    return redirect(url_for("admin.catalog"))
