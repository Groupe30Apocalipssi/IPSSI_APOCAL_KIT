"""
Export Azure DevOps Board work items to Markdown AND to an interactive HTML
project-management report.

Highlights of the HTML report:
- Work items shown as a hierarchy: Epic -> Issue -> Task (child tasks nested
  under their parent issue).
- Attachments (md / pdf / docx) are embedded and can be read inline: Markdown
  is rendered, PDF shown in a frame, docx converted to HTML (via mammoth).
- Group by sprint / artefact / assignee / state / type; search; filter; charts.
- Sidebar navigation isolates the selected section (no clutter from the rest).
- Print / PDF expands everything and keeps the charts.

Run:
    python ado_board_export.py

Security note: prefer setting the PAT via the ADO_PAT environment variable.
"""

from __future__ import annotations

import base64
import html
import json
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

import requests
from requests import HTTPError


def _load_dotenv(path: Path) -> None:
    """Charge un fichier .env minimal (KEY=VALUE) dans os.environ, sans écraser
    les variables déjà définies (ex. export shell) et sans dépendance externe."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


# Cherche un .env à côté du script, puis à la racine du projet (celui utilisé
# par le backend Django) — la valeur la plus proche du script gagne.
_load_dotenv(Path(__file__).resolve().parent / ".env")
_load_dotenv(Path(__file__).resolve().parents[2] / ".env")


# =========================
# CONFIG
# =========================

ORGANIZATION_URL = "https://dev.azure.com/ktchikaya"
PROJECT_NAME = "Groupe30Apocalipssi"
TEAM_NAME = "Groupe30Apocalipssi Team"
BOARD_ID = "Issues"

PERSONAL_ACCESS_TOKEN = os.environ.get("TON_TOKEN_ICI") #"ADO_PAT"

OUTPUT_MARKDOWN_FILE = "board_export.md"
OUTPUT_HTML_FILE = "board_report.html"

DEFAULT_GROUP = "sprint"  # sprint | artefact | assignee | state | type

RESOLVE_GIT_DETAILS = True  # Resolve linked commits/PRs via the Git API (needs PAT scope Code: Read).

RECOVER_EFFORT_FROM_HISTORY = True  # Rebuild effort from work item revisions when Remaining Work
                                    # was cleared on Done / never set on To Do (needs Work Items: Read).

DOWNLOAD_ATTACHMENTS = True
ATTACHMENTS_DIR = "attachments"
EMBED_ATTACHMENTS = True          # Embed md/pdf/docx content into the HTML to read inline.
MAX_EMBED_MB = 8                  # Skip embedding files larger than this (keeps a link instead).

WIQL_EXTRA_FILTER = ""
GROUP_ORDER = ["Epic", "Issues", "Task", "To Do", "In Progress", "Done"]

API_VERSION = "7.1"
BATCH_SIZE = 200

DONE_STATES = {"done", "closed", "resolved", "completed"}
INPROGRESS_STATES = {"doing", "in progress", "active", "committed"}
TODO_STATES = {"to do", "todo", "new", "proposed", "open"}


# =========================
# HTTP / API
# =========================

def ado_session(pat: str) -> requests.Session:
    token = base64.b64encode(f":{pat}".encode("utf-8")).decode("utf-8")
    session = requests.Session()
    session.headers.update(
        {"Authorization": f"Basic {token}", "Accept": "application/json", "Content-Type": "application/json"}
    )
    return session


def api_base_url() -> str:
    return ORGANIZATION_URL.rstrip("/")


def project_path() -> str:
    return quote(PROJECT_NAME.strip(), safe="")


def team_path() -> str:
    return quote(TEAM_NAME.strip(), safe="")


def board_path() -> str:
    return quote(str(BOARD_ID).strip(), safe="")


class AzureDevOpsApiError(RuntimeError):
    pass


def validate_config() -> None:
    missing = [
        name
        for name, value in {
            "ORGANIZATION_URL": ORGANIZATION_URL, "PROJECT_NAME": PROJECT_NAME,
            "TEAM_NAME": TEAM_NAME, "BOARD_ID": BOARD_ID, "PERSONAL_ACCESS_TOKEN": PERSONAL_ACCESS_TOKEN,
        }.items()
        if not str(value).strip() or "YOUR_" in str(value) or "PUT_YOUR_PAT" in str(value)
    ]
    if missing:
        raise ValueError("Missing config values: " + ", ".join(missing) + " (set PAT via ADO_PAT).")
    if PERSONAL_ACCESS_TOKEN.startswith("ghp_"):
        raise ValueError("PERSONAL_ACCESS_TOKEN looks like a GitHub token, not an Azure DevOps PAT.")
    if not TEAM_NAME.strip():
        raise ValueError("TEAM_NAME is required for Azure DevOps board APIs.")


def request_json(session: requests.Session, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
    response = session.request(method, url, timeout=30, **kwargs)
    ctype = response.headers.get("Content-Type", "")
    try:
        response.raise_for_status()
    except HTTPError as exc:
        raise AzureDevOpsApiError(
            f"Request failed.\nMethod: {method}\nURL: {url}\nStatus: {response.status_code}\n"
            f"Content-Type: {ctype}\nResponse:\n{response.text[:1200].strip()}"
        ) from exc
    try:
        return response.json()
    except ValueError as exc:
        raise AzureDevOpsApiError(
            f"Non-JSON response.\nURL: {url}\nStatus: {response.status_code}\n"
            f"Content-Type: {ctype}\nResponse:\n{response.text[:1200].strip()}\n"
            "Check organization URL, project, team, board id, or PAT."
        ) from exc


def get_boards(session):
    url = f"{api_base_url()}/{project_path()}/{team_path()}/_apis/work/boards?api-version={API_VERSION}"
    return request_json(session, "GET", url).get("value", [])


def get_board(session):
    url = f"{api_base_url()}/{project_path()}/{team_path()}/_apis/work/boards/{board_path()}?api-version={API_VERSION}"
    try:
        return request_json(session, "GET", url)
    except AzureDevOpsApiError as exc:
        try:
            names = ", ".join(b.get("name", "<unnamed>") for b in get_boards(session))
        except Exception:
            names = "unable to list boards"
        raise AzureDevOpsApiError(f"Could not fetch board '{BOARD_ID}'. Available: {names}\n\n{exc}") from exc


def get_backlogs(session):
    url = f"{api_base_url()}/{project_path()}/{team_path()}/_apis/work/backlogs?api-version={API_VERSION}"
    return request_json(session, "GET", url).get("value", [])


def get_iterations(session):
    url = f"{api_base_url()}/{project_path()}/{team_path()}/_apis/work/teamsettings/iterations?api-version={API_VERSION}"
    return request_json(session, "GET", url).get("value", [])


def build_wiql():
    extra = f"\n{WIQL_EXTRA_FILTER.strip()}" if WIQL_EXTRA_FILTER.strip() else ""
    return f"""
SELECT [System.Id]
FROM WorkItems
WHERE [System.TeamProject] = @project
  AND [System.WorkItemType] IN ('Epic', 'Issue', 'Task', 'User Story', 'Product Backlog Item', 'Bug')
{extra}
ORDER BY [System.State], [System.ChangedDate] DESC
"""


def query_work_item_ids(session):
    url = f"{api_base_url()}/{project_path()}/_apis/wit/wiql?api-version={API_VERSION}"
    return [i["id"] for i in request_json(session, "POST", url, json={"query": build_wiql()}).get("workItems", [])]


def chunks(values, size):
    return [values[i : i + size] for i in range(0, len(values), size)]


def fetch_work_items(session, ids):
    if not ids:
        return []
    url = f"{api_base_url()}/{project_path()}/_apis/wit/workitemsbatch?api-version={API_VERSION}"
    items = []
    for batch in chunks(ids, BATCH_SIZE):
        payload = {"ids": batch, "$expand": "relations", "errorPolicy": "Omit"}
        items.extend(request_json(session, "POST", url, json=payload).get("value", []))
    return items


# =========================
# Attachments
# =========================

def safe_filename(name):
    name = (name or "attachment").strip()
    return re.sub(r'[\\/:*?"<>|]+', "_", name).strip(". ") or "attachment"


def human_size(num):
    if not isinstance(num, (int, float)):
        return ""
    size = float(num)
    for unit in ["o", "Ko", "Mo", "Go"]:
        if size < 1024 or unit == "Go":
            return f"{size:.0f} {unit}" if unit == "o" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} To"


def extract_attachments(work_item):
    out = []
    for rel in work_item.get("relations", []) or []:
        if rel.get("rel") != "AttachedFile":
            continue
        a = rel.get("attributes", {}) or {}
        out.append({"name": a.get("name") or "attachment", "size": a.get("resourceSize"),
                    "comment": a.get("comment", ""), "url": rel.get("url", "")})
    return out


def download_attachment(session, url, dest):
    r = session.get(url, timeout=60, headers={"Accept": "*/*"})
    r.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)


def collect_attachments(session, work_items):
    total = 0
    for item in work_items:
        item_id = item.get("id")
        attachments = extract_attachments(item)
        for index, att in enumerate(attachments):
            if DOWNLOAD_ATTACHMENTS and att["url"]:
                dest = Path(ATTACHMENTS_DIR) / str(item_id) / safe_filename(att["name"])
                if dest.exists():
                    dest = dest.with_name(f"{dest.stem}_{index}{dest.suffix}")
                try:
                    download_attachment(session, att["url"], dest)
                    att["local"] = dest.as_posix()
                except Exception as exc:
                    att["error"] = str(exc)
        item["_attachments"] = attachments
        total += len(attachments)
    return total


def docx_to_html(path):
    try:
        import mammoth
        with open(path, "rb") as f:
            return mammoth.convert_to_html(f).value
    except Exception:
        return None


def embed_attachment(att):
    """Return a record for the HTML report, embedding md/pdf/docx content when possible."""
    rec = {
        "name": att.get("name", "fichier"),
        "size": human_size(att.get("size")),
        "href": att.get("local") or att.get("url", ""),
        "kind": "other",
    }
    local = att.get("local")
    if not (EMBED_ATTACHMENTS and local and local not in ("", "#")):
        return rec
    path = Path(local)
    if not path.exists():
        return rec
    try:
        if path.stat().st_size > MAX_EMBED_MB * 1024 * 1024:
            return rec
        ext = path.suffix.lower()
        if ext in (".md", ".markdown", ".txt"):
            rec["kind"] = "md"
            rec["text"] = path.read_text(encoding="utf-8", errors="replace")
        elif ext == ".pdf":
            rec["kind"] = "pdf"
            rec["pdf"] = "data:application/pdf;base64," + base64.b64encode(path.read_bytes()).decode()
        elif ext == ".docx":
            converted = docx_to_html(path)
            if converted is not None:
                rec["kind"] = "docx"
                rec["html"] = converted
    except Exception:
        pass
    return rec


# =========================
# Shared helpers
# =========================

def strip_html(value):
    if not value:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\n{3,}", "\n\n", html.unescape(text)).strip()


def markdown_escape(value):
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip().replace("|", r"\|")


def identity_display_name(value):
    if isinstance(value, dict):
        return value.get("displayName", "")
    return str(value) if value else ""


def work_item_url(work_item_id):
    return f"{api_base_url()}/{project_path()}/_workitems/edit/{work_item_id}"


def state_bucket(state):
    n = (state or "").strip().lower()
    if n in DONE_STATES:
        return "Done"
    if n in INPROGRESS_STATES:
        return "In Progress"
    if n in TODO_STATES:
        return "To Do"
    return state.strip() if state else "Unknown"


def parse_tags(tags):
    return [t.strip() for t in tags.split(";") if t.strip()] if tags else []


def iteration_leaf(path):
    if not path:
        return None
    return path.replace("/", "\\").split("\\")[-1].strip() or None


def extract_parent_id(work_item):
    for rel in work_item.get("relations", []) or []:
        if rel.get("rel") == "System.LinkTypes.Hierarchy-Reverse":
            m = re.search(r"/(?:workItems|workitems)/(\d+)", rel.get("url", "")) or re.search(r"/(\d+)$", rel.get("url", ""))
            if m:
                return int(m.group(1))
    return None


def progress_bar(done, total, width=10):
    if total <= 0:
        return "—"
    filled = max(0, min(width, round(width * done / total)))
    return "█" * filled + "░" * (width - filled) + f" {round(100 * done / total)}%"


# =========================
# Development links (commits / branches / pull requests)
# =========================

EFFORT_FIELDS = {
    "est": "Microsoft.VSTS.Scheduling.OriginalEstimate",
    "rem": "Microsoft.VSTS.Scheduling.RemainingWork",
    "done": "Microsoft.VSTS.Scheduling.CompletedWork",
    "sp": "Microsoft.VSTS.Scheduling.StoryPoints",
    "effort": "Microsoft.VSTS.Scheduling.Effort",
}


def _num(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def effort_of(fields):
    """Read scheduling/effort fields. Returns None if the process has none (e.g. Basic)."""
    out = {k: _num(fields.get(field)) for k, field in EFFORT_FIELDS.items()}
    return out if any(v is not None for v in out.values()) else None


def decode_artifact_uri(uri):
    """Decode a vstfs:/// artifact URI into (kind, project, repo, ident)."""
    if not uri or not uri.startswith("vstfs:///Git/"):
        return None
    try:
        kind = uri.split("vstfs:///Git/")[1].split("/")[0]  # Commit | Ref | PullRequestId
        payload = uri.rsplit("/", 1)[1]
        parts = [unquote(p) for p in payload.split("%2F")] if "%2F" in payload else unquote(payload).split("/")
        if len(parts) < 3:
            return None
        project, repo, ident = parts[0], parts[1], "/".join(parts[2:])
        return {"kind": kind, "project": project, "repo": repo, "ident": ident}
    except Exception:
        return None


def parse_dev_links(work_item):
    """Return raw dev artifact links grouped by kind from ArtifactLink relations."""
    commits, branches, prs = [], [], []
    for rel in work_item.get("relations", []) or []:
        if rel.get("rel") != "ArtifactLink":
            continue
        decoded = decode_artifact_uri(rel.get("url", ""))
        if not decoded:
            continue
        if decoded["kind"] == "Commit":
            commits.append(decoded)
        elif decoded["kind"] == "Ref":
            branches.append({**decoded, "branch": decoded["ident"][2:] if decoded["ident"].startswith("GB") else decoded["ident"]})
        elif decoded["kind"] == "PullRequestId":
            prs.append(decoded)
    return {"commits": commits, "branches": branches, "prs": prs}


def get_commit(session, repo_id, commit_id):
    url = f"{api_base_url()}/{project_path()}/_apis/git/repositories/{quote(repo_id, safe='')}/commits/{commit_id}?api-version={API_VERSION}"
    return request_json(session, "GET", url)


def get_pull_request(session, repo_id, pr_id):
    url = f"{api_base_url()}/{project_path()}/_apis/git/repositories/{quote(repo_id, safe='')}/pullrequests/{pr_id}?api-version={API_VERSION}"
    return request_json(session, "GET", url)


def resolve_dev(session, work_items):
    """Resolve commit/PR details for each work item into item['_dev']. Best-effort."""
    commit_cache, pr_cache = {}, {}
    total = 0
    for item in work_items:
        links = parse_dev_links(item)
        dev = {"branches": [b.get("branch", "") for b in links["branches"]], "commits": [], "prs": []}
        if RESOLVE_GIT_DETAILS:
            for c in links["commits"]:
                key = (c["repo"], c["ident"])
                if key not in commit_cache:
                    try:
                        data = get_commit(session, c["repo"], c["ident"])
                        commit_cache[key] = {
                            "short": c["ident"][:8],
                            "message": (data.get("comment", "") or "").split("\n")[0][:140],
                            "author": (data.get("author", {}) or {}).get("name", ""),
                            "date": ((data.get("author", {}) or {}).get("date", "") or "")[:10],
                            "url": (data.get("remoteUrl") or data.get("url") or ""),
                        }
                    except Exception:
                        commit_cache[key] = {"short": c["ident"][:8], "message": "(détail indisponible)", "author": "", "date": "", "url": ""}
                dev["commits"].append(commit_cache[key])
            for p in links["prs"]:
                key = (p["repo"], p["ident"])
                if key not in pr_cache:
                    try:
                        data = get_pull_request(session, p["repo"], p["ident"])
                        pr_cache[key] = {
                            "id": p["ident"],
                            "title": data.get("title", "")[:140],
                            "status": data.get("status", ""),
                            "url": (data.get("_links", {}).get("web", {}) or {}).get("href", "") or data.get("url", ""),
                        }
                    except Exception:
                        pr_cache[key] = {"id": p["ident"], "title": "(détail indisponible)", "status": "", "url": ""}
                dev["prs"].append(pr_cache[key])
        else:
            dev["commits"] = [{"short": c["ident"][:8], "message": "", "author": "", "date": "", "url": ""} for c in links["commits"]]
            dev["prs"] = [{"id": p["ident"], "title": "", "status": "", "url": ""} for p in links["prs"]]
        item["_dev"] = dev
        total += len(dev["commits"]) + len(dev["prs"]) + len(dev["branches"])
    return total


# =========================
# Capacity (per sprint / per member)
# =========================

def get_team_settings(session):
    url = f"{api_base_url()}/{project_path()}/{team_path()}/_apis/work/teamsettings?api-version={API_VERSION}"
    try:
        return request_json(session, "GET", url)
    except Exception:
        return {}


def get_capacities(session, iteration_id):
    url = f"{api_base_url()}/{project_path()}/{team_path()}/_apis/work/teamsettings/iterations/{iteration_id}/capacities?api-version={API_VERSION}"
    try:
        data = request_json(session, "GET", url)
        # API shape changed across versions: rows live under "value" or "teamMembers".
        return data.get("value") or data.get("teamMembers") or []
    except Exception:
        return []


def get_project_iterations(session):
    """Fallback: read all project-level iterations (with dates) from classification nodes,
    regardless of whether the team selected them."""
    url = f"{api_base_url()}/{project_path()}/_apis/wit/classificationnodes/iterations?$depth=10&api-version={API_VERSION}"
    try:
        root = request_json(session, "GET", url)
    except Exception:
        return []
    out = []

    def walk(node):
        for child in node.get("children", []) or []:
            attrs = child.get("attributes", {}) or {}
            out.append({
                "id": child.get("identifier", ""),
                "name": child.get("name", ""),
                "path": child.get("path", ""),
                "attributes": {"startDate": attrs.get("startDate", ""), "finishDate": attrs.get("finishDate", ""), "timeFrame": ""},
            })
            walk(child)

    walk(root)
    dated = [n for n in out if n["attributes"].get("startDate")]
    return dated or out


def build_sprints(iterations, capacity):
    """Combine iteration metadata (dates, timeframe) with team capacity per member."""
    out = []
    for it in iterations:
        a = it.get("attributes", {}) or {}
        name = it.get("name") or iteration_leaf(it.get("path", "")) or "Sprint"
        cap = capacity.get(name, {})
        out.append({
            "name": name,
            "path": it.get("path", ""),
            "start": (a.get("startDate", "") or "")[:10],
            "finish": (a.get("finishDate", "") or "")[:10],
            "timeframe": a.get("timeFrame", "") or "",
            "capacity": cap,
            "totalPerDay": round(sum(cap.values()), 1) if cap else 0,
        })
    return out


# =========================
# Effort (with history recovery)
# =========================

def any_effort_present(work_items):
    """True if at least one item currently carries an effort field (i.e. not a Basic process)."""
    for it in work_items:
        f = it.get("fields", {})
        if any(f.get(field) is not None for field in EFFORT_FIELDS.values()):
            return True
    return False


def get_work_item_updates(session, work_item_id):
    url = f"{api_base_url()}/{project_path()}/_apis/wit/workItems/{work_item_id}/updates?api-version={API_VERSION}"
    try:
        return request_json(session, "GET", url).get("value", [])
    except Exception:
        return []


def max_remaining_from_history(updates):
    """Largest Remaining Work ever recorded — a good proxy for the planned effort
    when only Remaining Work is tracked (it gets zeroed on Done)."""
    best = None
    for update in updates:
        change = (update.get("fields", {}) or {}).get("Microsoft.VSTS.Scheduling.RemainingWork")
        if change and change.get("newValue") is not None:
            value = _num(change.get("newValue"))
            if value is not None:
                best = value if best is None else max(best, value)
    return best


def resolve_effort(session, work_items):
    """Compute a normalized effort per item into item['_effort'], recovering the
    planned effort from history for Done / cleared tasks. Best-effort."""
    if not any_effort_present(work_items):
        return 0  # Basic process (no effort fields) — nothing to do.
    resolved = 0
    for item in work_items:
        f = item.get("fields", {})
        est = _num(f.get(EFFORT_FIELDS["est"]))
        rem = _num(f.get(EFFORT_FIELDS["rem"]))
        done = _num(f.get(EFFORT_FIELDS["done"]))
        sp = _num(f.get(EFFORT_FIELDS["sp"]))
        effort = _num(f.get(EFFORT_FIELDS["effort"]))
        bucket = state_bucket(f.get("System.State"))

        planned = est
        if planned is None and RECOVER_EFFORT_FROM_HISTORY and (bucket == "Done" or rem is None):
            planned = max_remaining_from_history(get_work_item_updates(session, item.get("id")))

        if bucket == "Done":
            if done is None:
                done = planned
            rem = 0.0 if rem is None else rem
            if planned is None:
                planned = done
        else:
            if rem is None and planned is not None:
                rem = planned
            if done is None and planned is not None and rem is not None:
                done = max(planned - rem, 0)

        eff = {"est": planned, "rem": rem, "done": done, "sp": sp, "effort": effort}
        item["_effort"] = eff if any(v is not None for v in eff.values()) else None
        if item["_effort"]:
            resolved += 1
    return resolved


def collect_capacity(session, iterations):
    """Return {sprint_name: {member: capacity_per_day}} across iterations."""
    capacity = {}
    for it in iterations:
        name = it.get("name") or iteration_leaf(it.get("path", "")) or "Sprint"
        rows = get_capacities(session, it.get("id"))
        per_member = {}
        for row in rows:
            member = (row.get("teamMember", {}) or {}).get("displayName", "")
            per_day = sum(_num(a.get("capacityPerDay")) or 0 for a in row.get("activities", []) or [])
            if member:
                per_member[member] = per_member.get(member, 0) + per_day
        if per_member:
            capacity[name] = per_member
    return capacity


# =========================
# Markdown rendering
# =========================

def canonical_group(value):
    if not value:
        return None
    return {"issue": "Issues", "issues": "Issues", "epic": "Epic", "task": "Task",
            "todo": "To Do", "to do": "To Do", "in progress": "In Progress",
            "done": "Done", "closed": "Done", "resolved": "Done"}.get(value.strip().lower())


def group_name(work_item):
    f = work_item.get("fields", {})
    for c in (f.get("System.BoardColumn"), f.get("System.State"), f.get("System.WorkItemType")):
        g = canonical_group(c)
        if g:
            return g
    return "Other"


def group_work_items(work_items):
    grouped = defaultdict(list)
    for item in work_items:
        grouped[group_name(item)].append(item)
    for items in grouped.values():
        items.sort(key=lambda i: i.get("fields", {}).get("System.ChangedDate", ""), reverse=True)
    return grouped


def attachment_link_md(att):
    label = markdown_escape(att.get("name", "attachment"))
    href = att.get("local") or att.get("url", "")
    line = f"[{label}]({href})" + (f" ({human_size(att.get('size'))})" if human_size(att.get("size")) else "")
    if att.get("error"):
        line += " — telechargement echoue"
    elif not att.get("local"):
        line += " — lien authentifie (PAT requis)"
    return line


def render_summary_section(work_items):
    buckets = defaultdict(int)
    for item in work_items:
        buckets[state_bucket(item.get("fields", {}).get("System.State"))] += 1
    total = len(work_items)
    percent = round(100 * buckets.get("Done", 0) / total) if total else 0
    lines = ["## Résumé", "", "| Indicateur | Valeur |", "|---|---:|", f"| Total | {total} |"]
    for b in ["Done", "In Progress", "To Do"]:
        if buckets.get(b):
            lines.append(f"| {b} | {buckets[b]} |")
    lines.append(f"| Avancement | {percent}% |")
    lines.extend(["", "```mermaid", "pie showData", "    title Répartition par statut"])
    for b, c in sorted(buckets.items(), key=lambda p: p[1], reverse=True):
        lines.append(f'    "{b}" : {c}')
    lines.extend(["```", ""])
    return lines


def render_tag_progress_section(work_items):
    stats = defaultdict(lambda: {"done": 0, "prog": 0, "todo": 0, "total": 0})
    for item in work_items:
        f = item.get("fields", {})
        b = state_bucket(f.get("System.State"))
        for tag in parse_tags(f.get("System.Tags")):
            e = stats[tag]
            e["total"] += 1
            e["done" if b == "Done" else "prog" if b == "In Progress" else "todo"] += 1
    lines = [f"## Avancement par artefact ({len(stats)})", ""]
    if not stats:
        return lines + ["_Aucun tag / artefact._", ""]
    lines.extend(["| Artefact | Terminé | En cours | À faire | Total | Avancement |", "|---|---:|---:|---:|---:|---|"])
    for tag, e in sorted(stats.items(), key=lambda p: (p[1]["done"] / p[1]["total"] if p[1]["total"] else 0), reverse=True):
        lines.append(f"| {markdown_escape(tag)} | {e['done']} | {e['prog']} | {e['todo']} | {e['total']} | {progress_bar(e['done'], e['total'])} |")
    lines.append("")
    return lines


def render_member_section(work_items):
    stats = defaultdict(lambda: {"done": 0, "remaining": 0, "total": 0})
    for item in work_items:
        f = item.get("fields", {})
        name = identity_display_name(f.get("System.AssignedTo")) or "Non assigné"
        e = stats[name]
        e["total"] += 1
        e["done" if state_bucket(f.get("System.State")) == "Done" else "remaining"] += 1
    lines = [f"## Charge par membre ({len(stats)})", "", "| Membre | Terminé | Restant | Total | Avancement |", "|---|---:|---:|---:|---|"]
    for name, e in sorted(stats.items(), key=lambda p: p[1]["total"], reverse=True):
        lines.append(f"| {markdown_escape(name)} | {e['done']} | {e['remaining']} | {e['total']} | {progress_bar(e['done'], e['total'])} |")
    lines.append("")
    return lines


def render_attachments_section(work_items):
    items_with = [(i, i.get("_attachments", [])) for i in work_items if i.get("_attachments")]
    count = sum(len(a) for _, a in items_with)
    lines = [f"## Pièces jointes ({count})", ""]
    if not items_with:
        return lines + ["_Aucune pièce jointe._", ""]
    lines.extend(["| Work item | Type | Pièce jointe |", "|---:|---|---|"])
    for item, attachments in sorted(items_with, key=lambda p: p[0].get("id", 0)):
        f = item.get("fields", {})
        for att in attachments:
            lines.append(f"| [{item.get('id')}]({work_item_url(item.get('id'))}) | {markdown_escape(f.get('System.WorkItemType', ''))} | {attachment_link_md(att)} |")
    lines.append("")
    return lines


def render_work_items_section(work_items):
    grouped = group_work_items(work_items)
    lines = [f"## Work Items ({len(work_items)})", ""]
    for group in GROUP_ORDER + sorted(g for g in grouped if g not in GROUP_ORDER):
        items = grouped.get(group, [])
        lines.extend([f"### {group} ({len(items)})", ""])
        if not items:
            lines.extend(["_No work items._", ""])
            continue
        lines.extend([
            "| ID | Title | Type | State | Board column | Iteration | Assigned to | Changed | Tags | 📎 |",
            "|---:|---|---|---|---|---|---|---|---|---:|",
        ])
        for item in items:
            f = item.get("fields", {})
            iid = item.get("id")
            n = len(item.get("_attachments", []))
            lines.append(
                f"| [{iid}]({work_item_url(iid)}) | {markdown_escape(f.get('System.Title', ''))} | "
                f"{markdown_escape(f.get('System.WorkItemType', ''))} | {markdown_escape(f.get('System.State', ''))} | "
                f"{markdown_escape(f.get('System.BoardColumn', ''))} | {markdown_escape(f.get('System.IterationPath', ''))} | "
                f"{markdown_escape(identity_display_name(f.get('System.AssignedTo')))} | {markdown_escape(f.get('System.ChangedDate', ''))} | "
                f"{markdown_escape(f.get('System.Tags', ''))} | {n if n else ''} |")
        lines.append("")
        for item in items:
            f = item.get("fields", {})
            description = strip_html(f.get("System.Description"))
            attachments = item.get("_attachments", [])
            if not description and not attachments:
                continue
            block = ["<details>", f"<summary>{markdown_escape(item.get('id'))} - {markdown_escape(f.get('System.Title', ''))}</summary>", ""]
            if description:
                block.extend([description, ""])
            if attachments:
                block.extend(["**Pièces jointes :**", ""])
                block.extend(f"- {attachment_link_md(a)}" for a in attachments)
                block.append("")
            block.extend(["</details>", ""])
            lines.extend(block)
    return lines


def render_board_section(board):
    lines = ["## Board", "", f"- Name: `{markdown_escape(board.get('name', BOARD_ID))}`",
             f"- ID: `{markdown_escape(board.get('id', ''))}`", f"- URL: `{markdown_escape(board.get('url', ''))}`", ""]
    for c in board.get("columns", []):
        pass
    columns, rows = board.get("columns", []), board.get("rows", [])
    if columns:
        lines.extend(["### Board Columns", "", "| Name | State mappings |", "|---|---|"])
        for c in columns:
            mp = ", ".join(f"{k}: {v}" for k, v in (c.get("stateMappings", {}) or {}).items())
            lines.append(f"| {markdown_escape(c.get('name', ''))} | {markdown_escape(mp)} |")
        lines.append("")
    if rows:
        lines.extend(["### Board Rows", "", "| Name |", "|---|"])
        for r in rows:
            lines.append(f"| {markdown_escape(r.get('name', ''))} |")
        lines.append("")
    return lines


def render_backlogs_section(backlogs):
    lines = [f"## Backlogs ({len(backlogs)})", ""]
    if not backlogs:
        return lines + ["_No backlogs found._", ""]
    lines.extend(["| Name | ID | Type | Rank | Default type | Work item types | Hidden |", "|---|---|---|---:|---|---|---|"])
    for b in sorted(backlogs, key=lambda i: i.get("rank", 0), reverse=True):
        types = ", ".join(t.get("name", "") for t in b.get("workItemTypes", []))
        lines.append(f"| {markdown_escape(b.get('name', ''))} | {markdown_escape(b.get('id', ''))} | {markdown_escape(b.get('type', ''))} | {markdown_escape(b.get('rank', ''))} | {markdown_escape((b.get('defaultWorkItemType') or {}).get('name', ''))} | {markdown_escape(types)} | {markdown_escape(b.get('isHidden', ''))} |")
    lines.append("")
    return lines


def render_iterations_section(iterations):
    lines = [f"## Sprints / Iterations ({len(iterations)})", ""]
    if not iterations:
        return lines + ["_No iterations found._", ""]
    lines.extend(["| Name | Path | Start | Finish | Time frame |", "|---|---|---|---|---|"])
    for it in iterations:
        a = it.get("attributes", {}) or {}
        lines.append(f"| {markdown_escape(it.get('name', ''))} | {markdown_escape(it.get('path', ''))} | {markdown_escape(a.get('startDate', ''))} | {markdown_escape(a.get('finishDate', ''))} | {markdown_escape(a.get('timeFrame', ''))} |")
    lines.append("")
    return lines


def render_markdown(board, backlogs, iterations, work_items, attachment_count):
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# Azure DevOps Export - {markdown_escape(PROJECT_NAME)}", "",
        f"- Project: `{markdown_escape(PROJECT_NAME)}`", f"- Team: `{markdown_escape(TEAM_NAME)}`",
        f"- Board: `{markdown_escape(board.get('name', BOARD_ID))}`", f"- Generated at: `{generated_at}`",
        f"- Backlogs exported: `{len(backlogs)}`", f"- Sprints / iterations exported: `{len(iterations)}`",
        f"- Work items exported: `{len(work_items)}`", f"- Attachments exported: `{attachment_count}`", "",
    ]
    lines.extend(render_summary_section(work_items))
    lines.extend(render_tag_progress_section(work_items))
    lines.extend(render_member_section(work_items))
    lines.extend(render_attachments_section(work_items))
    lines.extend(render_board_section(board))
    lines.extend(render_backlogs_section(backlogs))
    lines.extend(render_iterations_section(iterations))
    lines.extend(render_work_items_section(work_items))
    return "\n".join(lines).rstrip() + "\n"


# =========================
# Interactive HTML report
# =========================

def item_to_record(item):
    f = item.get("fields", {})
    iid = item.get("id")
    leaf = iteration_leaf(f.get("System.IterationPath", ""))
    sprint = leaf if (leaf and leaf != PROJECT_NAME) else "Backlog (non planifié)"
    return {
        "id": iid,
        "title": f.get("System.Title", ""),
        "type": f.get("System.WorkItemType", ""),
        "state": f.get("System.State", ""),
        "bucket": state_bucket(f.get("System.State")),
        "column": f.get("System.BoardColumn", "") or "",
        "sprint": sprint,
        "assignee": identity_display_name(f.get("System.AssignedTo")) or "Non assigné",
        "changed": (f.get("System.ChangedDate", "") or "")[:10],
        "tags": parse_tags(f.get("System.Tags")),
        "description": strip_html(f.get("System.Description")),
        "url": work_item_url(iid),
        "parent": extract_parent_id(item),
        "attachments": [embed_attachment(a) for a in item.get("_attachments", [])],
        "dev": item.get("_dev", {"branches": [], "commits": [], "prs": []}),
        "effort": item["_effort"] if "_effort" in item else effort_of(f),
    }


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.0/marked.min.js"></script>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1c2128;--muted:#6b7280;--line:#e5e7eb;--accent:#4f46e5;
--done:#15a06e;--prog:#e0940f;--todo:#8b94a3;--epic:#7c3aed;--issue:#2563eb;--task:#0f766e;}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--ink);line-height:1.55}
a{color:var(--accent);text-decoration:none}
.wrap{display:grid;grid-template-columns:220px minmax(0,1fr) 300px;max-width:1440px;margin:0 auto}
aside{position:sticky;top:0;align-self:start;height:100vh;overflow:auto;padding:20px 16px;background:var(--card)}
aside.left{border-right:1px solid var(--line)}
aside.right{border-left:1px solid var(--line)}
aside .title{font-weight:600;font-size:15px;margin-bottom:10px}
.navlink{display:flex;justify-content:space-between;gap:8px;padding:6px 8px;border-radius:6px;color:var(--ink);font-size:14px;cursor:pointer}
.navlink:hover{background:var(--bg)}
.navlink.active{background:#eef2ff;color:var(--accent);font-weight:600}
.navlink.all{color:var(--muted);border-bottom:1px solid var(--line);border-radius:0;margin-bottom:4px;padding-bottom:8px}
.navlink .n{color:var(--muted);font-variant-numeric:tabular-nums}
main{padding:24px 28px;min-width:0}
h1{font-size:24px;margin:0 0 4px}
.sub{color:var(--muted);font-size:14px;margin-bottom:20px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px;margin-bottom:20px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.kpi .l{font-size:12px;color:var(--muted)}
.kpi .v{font-size:26px;font-weight:600;font-variant-numeric:tabular-nums}
.charts{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.panel h4{margin:0 0 10px;font-size:13px;color:var(--muted);font-weight:600}
.chart-box{position:relative;height:200px}.chart-tall{position:relative;height:240px}
.toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:18px;position:sticky;top:0;background:var(--bg);padding:10px 0;z-index:5}
.toolbar input,.toolbar select{padding:8px 10px;border:1px solid var(--line);border-radius:8px;font-size:14px;background:var(--card);color:var(--ink)}
.toolbar input[type=search]{flex:1;min-width:180px}
.chips{display:flex;gap:6px}
.chip{padding:6px 12px;border:1px solid var(--line);border-radius:20px;font-size:13px;cursor:pointer;background:var(--card);color:var(--muted)}
.chip.on{background:var(--accent);border-color:var(--accent);color:#fff}
.btn{padding:8px 12px;border:1px solid var(--line);border-radius:8px;font-size:13px;cursor:pointer;background:var(--card);color:var(--ink)}
.btn:hover{background:var(--bg)}
.group{margin-bottom:26px}
.group>h2{font-size:16px;margin:0 0 10px;padding:8px 0;border-bottom:2px solid var(--line);display:flex;justify-content:space-between;align-items:center;gap:10px}
.group>h2 .gcount{font-size:13px;color:var(--muted);font-weight:500;display:flex;align-items:center;gap:8px;white-space:nowrap}
.mini{height:6px;background:var(--line);border-radius:4px;overflow:hidden;width:120px}
.mini>span{display:block;height:100%;background:var(--done)}
.wi{background:var(--card);border:1px solid var(--line);border-radius:10px;margin-bottom:8px;overflow:hidden}
.wi>summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:10px;padding:10px 14px}
.wi>summary::-webkit-details-marker{display:none}
.wi[open]>summary{border-bottom:1px solid var(--line)}
.badge{font-size:11px;font-weight:600;padding:2px 8px;border-radius:6px;color:#fff;white-space:nowrap}
.badge.Epic{background:var(--epic)}.badge.Issue{background:var(--issue)}.badge.Task{background:var(--task)}.badge.other{background:var(--muted)}
.wid{font-variant-numeric:tabular-nums;color:var(--muted);font-size:13px;font-weight:600}
.wtitle{font-size:14px;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.kidcount{font-size:11px;color:var(--muted);background:var(--bg);border:1px solid var(--line);padding:1px 7px;border-radius:20px;white-space:nowrap}
.who{font-size:12px;color:var(--muted);white-space:nowrap}
.st{font-size:11px;font-weight:600;padding:2px 8px;border-radius:20px;white-space:nowrap}
.st.Done{background:#e3f6ee;color:var(--done)}.st.InProgress{background:#fbefd7;color:var(--prog)}.st.ToDo,.st.Unknown{background:#eef0f3;color:#4b5563}
.clip{font-size:12px;color:var(--muted)}
.body{padding:12px 14px;font-size:14px}
.body .desc{margin:0 0 10px;white-space:pre-wrap;color:#374151}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px}
.tag{font-size:11px;background:#eef2ff;color:#4338ca;padding:2px 8px;border-radius:6px}
.parent{font-size:12px;color:var(--muted);margin-bottom:6px}
.children{margin:8px 0 2px;padding-left:12px;border-left:2px solid #eceef1}
.atts{margin:8px 0}
.att-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:6px 10px;margin-top:6px}
.att-name{font-size:13px;flex:1;min-width:120px}
.mini-btn{font-size:12px;padding:4px 10px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink);cursor:pointer}
.mini-btn:hover{background:#eef2ff}
.viewer{display:none;width:100%;margin-top:8px}
.viewer.show{display:block}
.viewer .doc{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px;max-height:600px;overflow:auto;font-size:14px}
.viewer .doc h1,.viewer .doc h2,.viewer .doc h3{margin:.6em 0 .3em}
.viewer .doc pre{background:var(--bg);padding:10px;border-radius:6px;overflow:auto}
.viewer .doc code{background:var(--bg);padding:1px 5px;border-radius:4px}
.viewer .doc table{border-collapse:collapse}.viewer .doc td,.viewer .doc th{border:1px solid var(--line);padding:4px 8px}
.viewer iframe{width:100%;height:600px;border:1px solid var(--line);border-radius:8px}
.metaline{font-size:12px;color:var(--muted);margin-top:8px}
.effort{display:inline-block;font-size:12px;background:#eef7f2;color:#0f7a54;border:1px solid #cdeadd;padding:3px 10px;border-radius:20px;margin-bottom:8px}
.dev{margin:8px 0;font-size:13px}
.branches{margin:4px 0}
.branch{display:inline-block;font-size:12px;background:#f0fdf4;border:1px solid #bbf7d0;color:#15803d;padding:2px 8px;border-radius:6px;margin:2px 6px 2px 0}
.commit{padding:3px 0;border-left:2px solid var(--line);padding-left:10px;margin:3px 0}
.sha{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;background:var(--bg);border:1px solid var(--line);padding:1px 6px;border-radius:4px;color:#334155}
.pr{font-weight:600;color:#7c3aed}
.pstatus{font-size:11px;background:#f3e8ff;color:#7c3aed;padding:1px 7px;border-radius:20px}
.cauthor{color:var(--muted);font-size:12px}
.effort-panel{margin-bottom:24px}
.etable{width:100%;border-collapse:collapse;font-size:13px}
.etable th,.etable td{border-bottom:1px solid var(--line);padding:6px 10px;text-align:right}
.etable th:first-child,.etable td:first-child{text-align:left}
.etable th{color:var(--muted);font-weight:600}
.note{font-size:12px;color:var(--muted);margin-top:8px}
.scope-tag{font-size:11px;font-weight:500;color:var(--accent);background:#eef2ff;padding:2px 8px;border-radius:20px}
.sprint-card{border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin-bottom:10px}
.sprint-card:last-child{margin-bottom:0}
.sprint-head{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.sprint-dates{color:var(--muted);font-size:12px;margin-top:4px}
.sprint-prog{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--muted);margin:8px 0}
.sprint-prog .mini{flex:1}
.sprint-cap{margin-top:6px}
.sprint-cap>summary{cursor:pointer;font-size:12px;color:var(--accent);list-style:none}
.sprint-cap>summary::-webkit-details-marker{display:none}
.tf{font-size:11px;font-weight:600;padding:2px 9px;border-radius:20px;background:#eef0f3;color:#4b5563}
.tf.current{background:#e3f6ee;color:var(--done)}
.tf.future{background:#eef2ff;color:#4338ca}
.tf.past{background:#eef0f3;color:#6b7280}
@media(max-width:1080px){.wrap{grid-template-columns:1fr}aside{display:none}.charts{grid-template-columns:1fr}}
.empty{color:var(--muted);font-size:14px;padding:20px;text-align:center}
footer{color:var(--muted);font-size:12px;margin:30px 0 10px;text-align:center}
@media print{
  aside,.toolbar{display:none!important}
  main{padding:0}
  body{background:#fff;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .charts{display:grid!important;break-inside:avoid}
  .wi,.group,.panel{break-inside:avoid}
  .viewer.show iframe{height:400px}
}
</style>
</head>
<body>
<div class="wrap">
  <aside class="left">
    <div class="title">Navigation</div>
    <div id="nav"></div>
  </aside>
  <main>
    <h1>__TITLE__</h1>
    <div class="sub" id="subtitle"></div>
    <div class="kpis" id="kpis"></div>
    <div class="charts">
      <div class="panel"><h4>Répartition par statut</h4><div class="chart-box"><canvas id="cStatus" role="img" aria-label="Répartition par statut"></canvas></div></div>
      <div class="panel"><h4>Avancement par artefact</h4><div class="chart-tall"><canvas id="cTag" role="img" aria-label="Avancement par artefact"></canvas></div></div>
      <div class="panel" style="grid-column:1/-1"><h4>Charge par membre</h4><div class="chart-tall"><canvas id="cMember" role="img" aria-label="Charge par membre"></canvas></div></div>
    </div>
    <div id="effortPanel"></div>
    <div class="toolbar">
      <input type="search" id="q" placeholder="Rechercher (titre, id, membre, tag)…">
      <label style="font-size:13px;color:var(--muted)">Grouper&nbsp;par</label>
      <select id="groupby">
        <option value="sprint">Sprint</option><option value="artefact">Artefact</option>
        <option value="assignee">Membre</option><option value="state">Statut</option><option value="type">Type</option>
      </select>
      <select id="assignee"></select>
      <div class="chips" id="stateChips"></div>
      <button class="btn" id="toggleAll">Tout déplier</button>
      <button class="btn" onclick="printReport()">Imprimer / PDF</button>
    </div>
    <div id="content"></div>
    <footer id="footer"></footer>
  </main>
  <aside class="right">
    <div class="title">Sprints <span id="scopeTag" class="scope-tag"></span></div>
    <div id="sprintPanel"></div>
  </aside>
</div>
<script>
const DATA = __DATA__;
const META = __META__;
const CAP = __CAP__;
const SPRINTS = __SPRINTS__;
let GROUP = "__DEFAULT_GROUP__";
let stateFilter = "all";
let allOpen = false;
let selectedGroup = null;

const esc = s => String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const bucketClass = b => b.replace(/\s/g,"");
const bucketLabel = b => ({ "To Do":"À faire","In Progress":"En cours","Done":"Terminé" }[b]||b);
const typeClass = t => (["Epic","Issue","Task"].includes(t)?t:"other");
const TYPE_ORDER = {Epic:0,Issue:1,"User Story":2,"Product Backlog Item":2,Bug:3,Task:4};
const LAST = {"Backlog (non planifié)":1,"Sans artefact":1,"Non assigné":1};
const byId = {}; DATA.forEach(i=>byId[i.id]=i);

function keyOf(it){
  if(GROUP==="sprint") return it.sprint;
  if(GROUP==="artefact") return it.tags.length?it.tags[0]:"Sans artefact";
  if(GROUP==="assignee") return it.assignee;
  if(GROUP==="state") return bucketLabel(it.bucket);
  if(GROUP==="type") return it.type||"—";
  return "Tous";
}
function filteredItems(){
  const q=document.getElementById("q").value.trim().toLowerCase();
  const asg=document.getElementById("assignee").value;
  return DATA.filter(it=>{
    if(stateFilter!=="all" && it.bucket!==stateFilter) return false;
    if(asg!=="all" && it.assignee!==asg) return false;
    if(q){const hay=(it.id+" "+it.title+" "+it.assignee+" "+it.tags.join(" ")+" "+it.type).toLowerCase();
      if(!hay.includes(q)) return false;}
    return true;
  });
}
function slug(s){return "g-"+String(s).toLowerCase().replace(/[^a-z0-9]+/g,"-");}
const sortItems = a => a.sort((x,y)=>(TYPE_ORDER[x.type]??9)-(TYPE_ORDER[y.type]??9)||x.id-y.id);

function attHtml(it){
  if(!it.attachments.length) return "";
  const rows=it.attachments.map((a,idx)=>{
    const read=a.kind!=="other"?`<button class="mini-btn" onclick="readAtt(${it.id},${idx},this)">Lire</button><div class="viewer"></div>`:"";
    const dl=a.href&&a.href!=="#"?`<a class="mini-btn" href="${esc(a.href)}" target="_blank">Télécharger</a>`:"";
    return `<div class="att-row"><span class="att-name">📄 ${esc(a.name)}${a.size?` · ${esc(a.size)}`:""}</span>${read}${dl}</div>`;
  }).join("");
  return `<div class="atts"><b style="font-size:13px">Pièces jointes :</b>${rows}</div>`;
}
function devHtml(it){
  const d=it.dev||{};
  const nb=(d.commits||[]).length+(d.prs||[]).length+(d.branches||[]).length;
  if(!nb) return "";
  const branches=(d.branches||[]).map(b=>`<span class="branch">🌿 ${esc(b)}</span>`).join("");
  const prs=(d.prs||[]).map(p=>`<div class="commit"><span class="pr">PR !${esc(p.id)}</span> ${p.url?`<a href="${esc(p.url)}" target="_blank">${esc(p.title||"pull request")}</a>`:esc(p.title||"pull request")} ${p.status?`<span class="pstatus">${esc(p.status)}</span>`:""}</div>`).join("");
  const commits=(d.commits||[]).map(c=>`<div class="commit"><span class="sha">${esc(c.short)}</span> ${c.url?`<a href="${esc(c.url)}" target="_blank">${esc(c.message||"commit")}</a>`:esc(c.message||"commit")} ${c.author?`<span class="cauthor">— ${esc(c.author)}${c.date?" · "+esc(c.date):""}</span>`:""}</div>`).join("");
  return `<div class="dev"><b style="font-size:13px">Développement :</b>
    ${branches?`<div class="branches">${branches}</div>`:""}${prs}${commits}</div>`;
}
function effortHtml(it){
  const e=it.effort; if(!e) return "";
  const parts=[];
  if(e.est!=null) parts.push(`Estimé ${e.est}h`);
  if(e.done!=null) parts.push(`Réalisé ${e.done}h`);
  if(e.rem!=null) parts.push(`Restant ${e.rem}h`);
  if(e.sp!=null) parts.push(`${e.sp} SP`);
  if(e.effort!=null && e.sp==null) parts.push(`Effort ${e.effort}`);
  if(!parts.length) return "";
  return `<div class="effort">⏱ ${parts.join(" · ")}</div>`;
}
function nodeHtml(it, childrenMap){
  const kids = sortItems((childrenMap[it.id]||[]).slice());
  const kidsHtml = kids.length?`<div class="children">${kids.map(k=>nodeHtml(k,childrenMap)).join("")}</div>`:"";
  const kidBadge = kids.length?`<span class="kidcount">${kids.length} tâche${kids.length>1?"s":""}</span>`:"";
  const who=it.assignee!=="Non assigné"?`<span class="who">${esc(it.assignee)}</span>`:"";
  const clip=it.attachments.length?`<span class="clip">📎 ${it.attachments.length}</span>`:"";
  const devNb=((it.dev||{}).commits||[]).length+((it.dev||{}).prs||[]).length;
  const gitBadge=devNb?`<span class="clip">⎇ ${devNb}</span>`:"";
  const tags=it.tags.length?`<div class="tags">${it.tags.map(t=>`<span class="tag">${esc(t)}</span>`).join("")}</div>`:"";
  const desc=it.description?`<p class="desc">${esc(it.description)}</p>`:"";
  return `<details class="wi"${allOpen?" open":""}>
    <summary>
      <span class="badge ${typeClass(it.type)}">${esc(it.type)}</span>
      <a class="wid" href="${esc(it.url)}" target="_blank" onclick="event.stopPropagation()">#${it.id}</a>
      <span class="wtitle">${esc(it.title)}</span>${kidBadge}
      ${who}<span class="st ${bucketClass(it.bucket)}">${bucketLabel(it.bucket)}</span>${gitBadge}${clip}
    </summary>
    <div class="body">${tags}${effortHtml(it)}${desc}${attHtml(it)}${devHtml(it)}
      <div class="metaline">Modifié le ${esc(it.changed||"—")} · colonne ${esc(it.column||"—")}</div>
      ${kidsHtml}
    </div></details>`;
}
function buildTree(items){
  const present=new Set(items.map(i=>i.id));
  const childrenMap={}; const roots=[];
  items.forEach(i=>{
    if(i.parent && present.has(i.parent)) (childrenMap[i.parent]=childrenMap[i.parent]||[]).push(i);
    else roots.push(i);
  });
  return {roots:sortItems(roots), childrenMap};
}
function render(){
  const items=filteredItems();
  const groups={};
  items.forEach(it=>{const k=keyOf(it);(groups[k]=groups[k]||[]).push(it);});
  let keys=Object.keys(groups).sort((a,b)=>{
    const la=LAST[a]?1:0, lb=LAST[b]?1:0;
    if(la!==lb) return la-lb;
    return groups[b].length-groups[a].length || a.localeCompare(b);
  });
  const nav=document.getElementById("nav");
  nav.innerHTML=`<div class="navlink all${selectedGroup===null?" active":""}" onclick="selectGroup(null)"><span>Toutes les sections</span><span class="n">${items.length}</span></div>`+
    keys.map(k=>`<div class="navlink${selectedGroup===k?" active":""}" onclick="selectGroup('${encodeURIComponent(k)}')"><span>${esc(k)}</span><span class="n">${groups[k].length}</span></div>`).join("");
  const shown = selectedGroup && keys.includes(selectedGroup) ? [selectedGroup] : keys;
  const scoped = shown.reduce((acc,k)=>acc.concat(groups[k]||[]),[]);
  // Everything below reacts to the current scope (filters + selected section)
  updateKpis(scoped);
  updateCharts(scoped);
  renderEffort(scoped);
  renderSprints(scoped);
  document.getElementById("scopeTag").textContent = selectedGroup ? selectedGroup : "";
  const content=document.getElementById("content");
  if(!shown.length){content.innerHTML='<div class="empty">Aucun élément ne correspond aux filtres.</div>';return;}
  content.innerHTML=shown.map(k=>{
    const {roots,childrenMap}=buildTree(groups[k]);
    const done=groups[k].filter(i=>i.bucket==="Done").length;
    const pct=Math.round(100*done/groups[k].length);
    return `<section class="group" id="${slug(k)}">
      <h2><span>${esc(k)}</span><span class="gcount"><span class="mini"><span style="width:${pct}%"></span></span> ${done}/${groups[k].length} · ${pct}%</span></h2>
      ${roots.map(r=>nodeHtml(r,childrenMap)).join("")}
    </section>`;
  }).join("");
}
function selectGroup(k){selectedGroup=k===null?null:decodeURIComponent(k);render();
  if(selectedGroup)window.scrollTo({top:0,behavior:"smooth"});}
function readAtt(id,idx,btn){
  const a=byId[id].attachments[idx];
  const box=btn.nextElementSibling;
  const open=box.classList.contains("show");
  box.classList.toggle("show"); btn.textContent=open?"Lire":"Masquer";
  if(!open && !box.dataset.loaded){
    if(a.kind==="md") box.innerHTML='<div class="doc">'+(window.marked?marked.parse(a.text||""):esc(a.text||""))+'</div>';
    else if(a.kind==="pdf") box.innerHTML='<iframe src="'+a.pdf+'" title="'+esc(a.name)+'"></iframe>';
    else if(a.kind==="docx") box.innerHTML='<div class="doc">'+(a.html||"")+'</div>';
    box.dataset.loaded="1";
  }
}
let _opened=[];
function printReport(){
  _opened=[];
  document.querySelectorAll("details.wi").forEach(d=>{if(!d.open){_opened.push(d);d.open=true;}});
  window.print();
}
window.onafterprint=()=>{_opened.forEach(d=>d.open=false);_opened=[];};

function buildControls(){
  document.getElementById("subtitle").textContent=`${META.project} · ${META.team} · généré le ${META.generated} · ${DATA.length} work items · ${META.attachments} pièce(s) jointe(s)`;
  document.getElementById("stateChips").innerHTML=[["all","Tous"],["To Do","À faire"],["In Progress","En cours"],["Done","Terminé"]]
    .map(([v,l])=>`<span class="chip${v==="all"?" on":""}" data-s="${v}">${l}</span>`).join("");
  document.querySelectorAll(".chip").forEach(c=>c.onclick=()=>{stateFilter=c.dataset.s;selectedGroup=null;
    document.querySelectorAll(".chip").forEach(x=>x.classList.toggle("on",x===c));render();});
  const names=[...new Set(DATA.map(i=>i.assignee))].sort();
  document.getElementById("assignee").innerHTML='<option value="all">Tous les membres</option>'+names.map(n=>`<option value="${esc(n)}">${esc(n)}</option>`).join("");
  const gb=document.getElementById("groupby"); gb.value=GROUP;
  gb.onchange=e=>{GROUP=e.target.value;selectedGroup=null;render();};
  document.getElementById("assignee").onchange=()=>{selectedGroup=null;render();};
  document.getElementById("q").oninput=()=>{selectedGroup=null;render();};
  document.getElementById("toggleAll").onclick=e=>{allOpen=!allOpen;e.target.textContent=allOpen?"Tout replier":"Tout déplier";render();};
  document.getElementById("footer").textContent=`Rapport généré automatiquement depuis Azure DevOps — ${META.generated}`;
}
let chStatus, chTag, chMember;
function createCharts(){
  const opt={responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},animation:{duration:250}};
  chStatus=new Chart(cStatus,{type:"doughnut",data:{labels:["Terminé","En cours","À faire"],datasets:[{data:[0,0,0],backgroundColor:["#15a06e","#e0940f","#8b94a3"]}]},options:{...opt,cutout:"62%",plugins:{legend:{display:true,position:"bottom",labels:{boxWidth:12,font:{size:11}}}}}});
  chTag=new Chart(cTag,{type:"bar",data:{labels:[],datasets:[{label:"Terminé",data:[],backgroundColor:"#15a06e"},{label:"Restant",data:[],backgroundColor:"#d7dbe0"}]},options:{...opt,indexAxis:"y",scales:{x:{stacked:true},y:{stacked:true}}}});
  chMember=new Chart(cMember,{type:"bar",data:{labels:[],datasets:[{label:"Terminé",data:[],backgroundColor:"#15a06e"},{label:"Restant",data:[],backgroundColor:"#d7dbe0"}]},options:{...opt,indexAxis:"y",scales:{x:{stacked:true},y:{stacked:true}}}});
}
function updateKpis(items){
  const total=items.length,done=items.filter(i=>i.bucket==="Done").length;
  const prog=items.filter(i=>i.bucket==="In Progress").length,todo=items.filter(i=>i.bucket==="To Do").length;
  document.getElementById("kpis").innerHTML=[["Total",total],["Terminés",done],["En cours",prog],["À faire",todo],["Avancement",(total?Math.round(100*done/total):0)+"%"]]
    .map(([l,v])=>`<div class="kpi"><div class="l">${l}</div><div class="v">${v}</div></div>`).join("");
}
function updateCharts(items){
  const done=items.filter(i=>i.bucket==="Done").length,prog=items.filter(i=>i.bucket==="In Progress").length,todo=items.filter(i=>i.bucket==="To Do").length;
  chStatus.data.datasets[0].data=[done,prog,todo]; chStatus.update("none");
  const tagStat={};items.forEach(i=>{const t=i.tags.length?i.tags[0]:"Sans artefact";(tagStat[t]=tagStat[t]||{d:0,r:0});i.bucket==="Done"?tagStat[t].d++:tagStat[t].r++;});
  const tk=Object.keys(tagStat).sort((a,b)=>(tagStat[b].d+tagStat[b].r)-(tagStat[a].d+tagStat[a].r));
  chTag.data.labels=tk; chTag.data.datasets[0].data=tk.map(k=>tagStat[k].d); chTag.data.datasets[1].data=tk.map(k=>tagStat[k].r); chTag.update("none");
  const mStat={};items.forEach(i=>{const m=i.assignee;(mStat[m]=mStat[m]||{d:0,r:0});i.bucket==="Done"?mStat[m].d++:mStat[m].r++;});
  const mk=Object.keys(mStat).sort((a,b)=>(mStat[b].d+mStat[b].r)-(mStat[a].d+mStat[a].r));
  chMember.data.labels=mk; chMember.data.datasets[0].data=mk.map(k=>mStat[k].d); chMember.data.datasets[1].data=mk.map(k=>mStat[k].r); chMember.update("none");
}
function renderEffort(items){
  const panel=document.getElementById("effortPanel");
  const hasEffort=items.some(i=>i.effort);
  const hasCap=Object.keys(CAP).length>0;
  if(!hasEffort && !hasCap){ panel.innerHTML=""; return; }
  const agg={};
  items.forEach(i=>{
    if(!i.effort) return;
    const m=i.assignee; const a=agg[m]=agg[m]||{est:0,done:0,rem:0,sp:0};
    a.est+=i.effort.est||0; a.done+=i.effort.done||0; a.rem+=i.effort.rem||0; a.sp+=i.effort.sp||0;
  });
  const capMember={};
  Object.values(CAP).forEach(members=>Object.entries(members).forEach(([m,v])=>{capMember[m]=(capMember[m]||0)+v;}));
  // Only show capacity rows for members present in scope (or with effort)
  const scopeMembers=new Set(items.map(i=>i.assignee));
  const members=[...new Set([...Object.keys(agg),...Object.keys(capMember).filter(m=>scopeMembers.has(m))])].sort();
  if(!members.length){ panel.innerHTML=""; return; }
  const showSP=Object.values(agg).some(a=>a.sp>0);
  const showHrs=Object.values(agg).some(a=>a.est||a.done||a.rem);
  const round1=x=>Math.round(x*10)/10;
  let rows=members.map(m=>{
    const a=agg[m]||{est:0,done:0,rem:0,sp:0}; const cap=capMember[m];
    const load=(cap&&a.rem)?Math.round(100*a.rem/cap):null;
    return `<tr><td>${esc(m)}</td>
      ${showHrs?`<td>${a.est?round1(a.est):"—"}</td><td>${a.done?round1(a.done):"—"}</td><td>${a.rem?round1(a.rem):"—"}</td>`:""}
      ${showSP?`<td>${a.sp||"—"}</td>`:""}
      ${hasCap?`<td>${cap!=null?cap+" h/j":"—"}</td><td>${load!=null?load+"%":"—"}</td>`:""}
    </tr>`;
  }).join("");
  const head=`<tr><th>Membre</th>${showHrs?"<th>Estimé (h)</th><th>Réalisé (h)</th><th>Restant (h)</th>":""}${showSP?"<th>Story Points</th>":""}${hasCap?"<th>Capacité</th><th>Charge</th>":""}</tr>`;
  panel.innerHTML=`<div class="panel effort-panel"><h4>Effort & capacité${selectedGroup?` — ${esc(selectedGroup)}`:""}</h4>
    <table class="etable">${head}${rows}</table>
    ${!hasEffort?'<div class="note">Aucun champ d\'effort trouvé (process Basic ?).</div>':""}
  </div>`;
}
function renderSprints(items){
  const el=document.getElementById("sprintPanel");
  const tf={past:"Passé",current:"En cours",future:"À venir"};
  if(!SPRINTS.length){
    el.innerHTML=`<div class="note">Aucun sprint renvoyé par l'API pour cette équipe.<br>
      Vérifie <b>Team settings → Team configuration → Iterations</b> : les sprints définis au niveau projet doivent être <b>rattachés à l'équipe</b> « ${esc(META.team)} » pour remonter ici (dates et capacité incluses).</div>`;
    return;
  }
  el.innerHTML=SPRINTS.map(s=>{
    const its=items.filter(i=>i.sprint===s.name);
    const done=its.filter(i=>i.bucket==="Done").length;
    const pct=its.length?Math.round(100*done/its.length):0;
    const prog=its.length
      ? `<div class="sprint-prog"><div class="mini"><span style="width:${pct}%"></span></div><span>${done}/${its.length} · ${pct}%</span></div>`
      : `<div class="note">Aucun item de la sélection dans ce sprint.</div>`;
    const cap=Object.entries(s.capacity||{});
    const capBody=cap.length
      ? `<table class="etable" style="margin-top:6px"><tr><th>Membre</th><th>h/j</th></tr>${cap.map(([m,v])=>`<tr><td>${esc(m)}</td><td>${v}</td></tr>`).join("")}<tr><td><b>Total</b></td><td><b>${s.totalPerDay}</b></td></tr></table>`
      : '<div class="note">Capacité non renseignée (onglet Capacity du sprint).</div>';
    const dates=(s.start||s.finish)?`${esc(s.start||"?")} → ${esc(s.finish||"?")}`:"dates non définies";
    return `<div class="sprint-card">
      <div class="sprint-head"><b>${esc(s.name)}</b> <span class="tf ${esc(s.timeframe)}">${esc(tf[s.timeframe]||s.timeframe||"")}</span></div>
      <div class="sprint-dates">📅 ${dates}</div>
      ${prog}
      <details class="sprint-cap"><summary>Capacité (${cap.length}) ▾</summary>${capBody}</details>
    </div>`;
  }).join("");
}
buildControls();createCharts();render();
</script>
</body>
</html>
"""


def render_html(board, backlogs, iterations, work_items, attachment_count, capacity=None, sprints=None, default_group=DEFAULT_GROUP):
    records = [item_to_record(it) for it in work_items]
    meta = {
        "project": PROJECT_NAME, "team": TEAM_NAME, "board": board.get("name", BOARD_ID),
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"), "attachments": attachment_count,
    }
    data_json = json.dumps(records, ensure_ascii=False).replace("</", "<\\/")
    meta_json = json.dumps(meta, ensure_ascii=False).replace("</", "<\\/")
    cap_json = json.dumps(capacity or {}, ensure_ascii=False).replace("</", "<\\/")
    sprints_json = json.dumps(sprints or [], ensure_ascii=False).replace("</", "<\\/")
    return (
        HTML_TEMPLATE.replace("__TITLE__", html.escape(f"Rapport projet — {PROJECT_NAME}"))
        .replace("__DATA__", data_json)
        .replace("__META__", meta_json)
        .replace("__CAP__", cap_json)
        .replace("__SPRINTS__", sprints_json)
        .replace("__DEFAULT_GROUP__", default_group)
    )


# =========================
# Entry point
# =========================

def export_board():
    validate_config()
    session = ado_session(PERSONAL_ACCESS_TOKEN)
    print("Fetching board metadata...")
    board = get_board(session)
    print("Fetching backlogs...")
    backlogs = get_backlogs(session)
    print("Fetching sprints / iterations...")
    iterations = get_iterations(session)
    if not iterations:
        print("  No iterations assigned to the team — falling back to project-level iterations.")
        print("  (Tip: Team settings > Team configuration > Iterations to attach sprints to the team.)")
        iterations = get_project_iterations(session)
    print(f"  {len(iterations)} iteration(s).")
    print("Querying work item ids...")
    ids = query_work_item_ids(session)
    print(f"Fetching {len(ids)} work items...")
    work_items = fetch_work_items(session, ids)
    print("Collecting attachments...")
    attachment_count = collect_attachments(session, work_items)
    print(f"Found {attachment_count} attachment(s).")
    print("Resolving development links (commits / PRs)...")
    dev_count = resolve_dev(session, work_items)
    print(f"Found {dev_count} dev link(s).")
    print("Resolving effort (with history recovery)...")
    effort_count = resolve_effort(session, work_items)
    print(f"Effort resolved for {effort_count} item(s).")
    print("Collecting team capacity...")
    capacity = collect_capacity(session, iterations)
    print(f"Capacity found for {len(capacity)} sprint(s).")
    sprints = build_sprints(iterations, capacity)

    Path(OUTPUT_MARKDOWN_FILE).write_text(render_markdown(board, backlogs, iterations, work_items, attachment_count), encoding="utf-8")
    Path(OUTPUT_HTML_FILE).write_text(render_html(board, backlogs, iterations, work_items, attachment_count, capacity=capacity, sprints=sprints), encoding="utf-8")
    print(f"Markdown: {Path(OUTPUT_MARKDOWN_FILE).resolve()}")
    print(f"HTML report: {Path(OUTPUT_HTML_FILE).resolve()}")


if __name__ == "__main__":
    export_board()
