"""OnTrack data fetching — CLI subprocess and direct API calls."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from datetime import date

import requests

_GRADE_LABELS = {0: "P (Pass)", 1: "C (Credit)", 2: "D (Distinction)", 3: "HD (High Distinction)"}


def _run_ontrack(cmd: list[str]) -> list | dict:
    result = subprocess.run(["ontrack"] + cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ontrack error: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def fetch_active_projects() -> list[dict]:
    today = date.today()
    projects = _run_ontrack(["projects", "--json"])
    return [p for p in projects if date.fromisoformat(p["unit"]["end_date"]) >= today]


def fetch_tasks(project_id: int) -> list[dict]:
    data = _run_ontrack(["project", str(project_id), "--json"])
    tasks = data["tasks"]

    submitted_def_ids = {t["task_definition_id"] for t in tasks}
    today = date.today().isoformat()

    for td in data["unit"]["task_definitions"]:
        if td["id"] in submitted_def_ids:
            continue
        if td.get("start_date", "0000") > today:
            continue
        tasks.append({
            "id":                 None,
            "task_definition_id": td["id"],
            "abbreviation":       td["abbreviation"],
            "name":               td["name"],
            "status":             "not_started",
            "status_label":       "Not Started",
            "target_grade":       td.get("target_grade"),
            "target_grade_label": _GRADE_LABELS.get(td.get("target_grade"), "P (Pass)"),
            "due_date":           td.get("target_date") or td.get("due_date"),
            "deadline":           td.get("due_date"),
            "submission_date":    None,
            "completion_date":    None,
            "extensions":         0,
            "grade":              None,
            "is_overdue":         False,
        })

    return tasks


def load_api_auth() -> tuple[str, dict, int | None]:
    """Return (base_url, headers, student_id) using the ontrack CLI's stored auth."""
    candidates = list(pathlib.Path.home().glob(
        ".local/share/uv/tools/ontrack-cli/lib/python*/site-packages"
    ))
    if not candidates:
        print("Could not locate ontrack-cli site-packages for API auth.", file=sys.stderr)
        sys.exit(1)

    sys.path.insert(0, str(candidates[0]))
    from ontrack_cli.config import load_auth_config  # type: ignore

    auth = load_auth_config()
    headers = {
        "Username":   auth.username,
        "Auth-Token": auth.auth_token,
        "Accept":     "application/json",
    }
    student_id = auth.cached_user.id if auth.cached_user else None
    return auth.base_url, headers, student_id


_API_AUTH: tuple | None = None


def _api_auth() -> tuple[str, dict, int | None]:
    global _API_AUTH
    if _API_AUTH is None:
        _API_AUTH = load_api_auth()
    return _API_AUTH


def fetch_task_sheet(unit_id: int, task_def_id: int) -> bytes | None:
    """Return the task sheet PDF bytes, or None if unavailable."""
    base_url, headers, _ = _api_auth()
    url = f"{base_url}/api/units/{unit_id}/task_definitions/{task_def_id}/task_pdf.json"

    try:
        r = requests.get(url, headers={**headers, "Accept": "*/*"},
                         params={"as_attachment": "true"}, timeout=15)
        r.raise_for_status()
    except requests.RequestException:
        return None

    if r.content[:4] != b"%PDF":
        return None
    return r.content


def fetch_submission(project_id: int, task_def_id: int) -> tuple[bytes, str] | None:
    """Return (pdf_bytes, filename) for the latest submission, or None if unavailable."""
    base_url, headers, _ = _api_auth()
    url = f"{base_url}/api/projects/{project_id}/task_def_id/{task_def_id}/submission"

    try:
        r = requests.get(url, headers={**headers, "Accept": "*/*"},
                         params={"as_attachment": "true"}, timeout=15)
        r.raise_for_status()
    except requests.RequestException:
        return None

    if r.content[:4] != b"%PDF":
        return None

    disposition = r.headers.get("Content-Disposition", "")
    filename = disposition.split("filename=")[-1].strip() if "filename=" in disposition else f"{task_def_id}.pdf"
    return r.content, filename


def fetch_last_feedback(project_id: int, task_def_id: int) -> str | None:
    """Return the most recent tutor text comment, or None."""
    base_url, headers, student_id = _api_auth()
    url = f"{base_url}/api/projects/{project_id}/task_def_id/{task_def_id}/comments"

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
    except requests.RequestException:
        return None

    comments = r.json()
    if not isinstance(comments, list):
        return None

    for comment in reversed(comments):
        if comment.get("type") != "text":
            continue
        author_id = (comment.get("author") or {}).get("id")
        if author_id and author_id == student_id:
            continue
        text = (comment.get("comment") or "").strip()
        if text:
            return text

    return None
