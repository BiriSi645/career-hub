from io import BytesIO, SEEK_END
from pathlib import Path
from re import fullmatch
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

from flask import Response, abort, current_app, send_file, send_from_directory
from vercel.blob import BlobError, BlobNotFoundError, sync as blob
from werkzeug.utils import secure_filename


LOCAL_FILE_PREFIX = "local:"
BLOB_FILE_PREFIX = "blob:resumes/"
STORED_NAME = r"[0-9a-f]{32}\.(pdf|doc|docx)"
RESUME_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def save_resume_file(upload):
    """Validate and persist a resume upload, returning its internal file URL."""
    if not upload or not upload.filename:
        raise ValueError("Choose a CV file to upload.")

    original_name = secure_filename(upload.filename)
    extension = Path(original_name).suffix.lower()
    if extension not in RESUME_TYPES:
        raise ValueError("CV must be a PDF, DOC, or DOCX file.")

    size = upload.stream.seek(0, SEEK_END)
    limit = current_app.config["RESUME_MAX_BYTES"]
    if size > limit:
        raise ValueError(f"CV files must be {limit // (1024 * 1024)} MiB or smaller.")
    upload.stream.seek(0)
    header = upload.stream.read(8)
    upload.stream.seek(0)
    valid = (extension == ".pdf" and header.startswith(b"%PDF-")) or (
        extension == ".doc" and header == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    )
    if extension == ".pdf" and valid:
        upload.stream.seek(max(0, size - 1024))
        valid = upload.stream.read().rstrip().endswith(b"%%EOF")
        upload.stream.seek(0)
    if extension == ".docx":
        try:
            with ZipFile(upload.stream) as document:
                valid = {"[Content_Types].xml", "word/document.xml"} <= set(document.namelist())
        except (BadZipFile, OSError):
            valid = False
        finally:
            upload.stream.seek(0)
    if not valid:
        raise ValueError("The CV file does not match its document format.")

    stored_name = f"{uuid4().hex}{extension}"
    if current_app.config["RESUME_STORAGE"] == "blob":
        try:
            blob.put_blob(f"resumes/{stored_name}", upload.stream, access="private",
                          content_length=size, content_type=RESUME_TYPES[extension])
        except BlobError:
            raise OSError("Private CV storage is unavailable.") from None
        return f"{BLOB_FILE_PREFIX}{stored_name}"

    upload_dir = Path(current_app.config["RESUME_UPLOAD_DIR"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    path = upload_dir / stored_name
    try:
        upload.save(path)
    except OSError:
        path.unlink(missing_ok=True)
        raise
    return f"{LOCAL_FILE_PREFIX}{stored_name}"


def delete_resume_file(file_url):
    if file_url.startswith(BLOB_FILE_PREFIX):
        stored_name = file_url.removeprefix(BLOB_FILE_PREFIX)
        if fullmatch(STORED_NAME, stored_name):
            try:
                blob.delete_blob(f"resumes/{stored_name}")
            except BlobError:
                raise OSError("Private CV storage is unavailable.") from None
        return
    if not file_url.startswith(LOCAL_FILE_PREFIX):
        return
    stored_name = file_url.removeprefix(LOCAL_FILE_PREFIX)
    if not fullmatch(STORED_NAME, stored_name):
        return
    path = Path(current_app.config["RESUME_UPLOAD_DIR"]) / stored_name
    path.unlink(missing_ok=True)


def resume_file_response(resume):
    """Download an uploaded document or the built-in demo CV."""
    if resume.file_url == "demo:cv" or fullmatch(r"https://example\.test/resumes/[0-9]+\.pdf", resume.file_url):
        return _private_download(Response(
            "Career Hub sample CV\n\nProfile: Software engineering student\nSkills: Python and PostgreSQL\n",
            mimetype="text/plain",
            headers={"Content-Disposition": 'attachment; filename="career-hub-demo-cv.txt"'},
        ))
    if resume.file_url.startswith(BLOB_FILE_PREFIX):
        stored_name = resume.file_url.removeprefix(BLOB_FILE_PREFIX)
        if not fullmatch(STORED_NAME, stored_name):
            abort(404)
        try:
            result = blob.get_blob(f"resumes/{stored_name}", access="private")
        except BlobNotFoundError:
            abort(404)
        except BlobError:
            abort(503, description="CV storage is temporarily unavailable.")
        extension = Path(stored_name).suffix
        return _private_download(send_file(
            BytesIO(result.body), mimetype=RESUME_TYPES[extension], as_attachment=True,
            download_name=f"{secure_filename(resume.title) or 'resume'}{extension}", conditional=False,
        ))

    if current_app.config["RESUME_STORAGE"] != "local" or not resume.file_url.startswith(LOCAL_FILE_PREFIX):
        abort(404)

    stored_name = resume.file_url.removeprefix(LOCAL_FILE_PREFIX)
    if not fullmatch(STORED_NAME, stored_name):
        abort(404)

    upload_dir = Path(current_app.config["RESUME_UPLOAD_DIR"])
    path = upload_dir / stored_name
    if path.is_symlink() or not path.is_file():
        abort(404)

    extension = Path(stored_name).suffix
    download_name = f"{secure_filename(resume.title) or 'resume'}{extension}"
    response = send_from_directory(
        upload_dir,
        stored_name,
        as_attachment=True,
        download_name=download_name,
    )
    return _private_download(response)


def _private_download(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "private, no-store"
    return response
