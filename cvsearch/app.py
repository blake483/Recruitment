"""Flask web app: upload CVs, search them, review candidates."""

import csv
import io
import os
import re
import tempfile
import zipfile
from urllib.parse import urlencode

from flask import (Flask, Response, abort, flash, redirect, render_template, request,
                   send_from_directory, url_for)

from . import taxonomy
from .db import EDITABLE, Store
from .extract import SUPPORTED_EXTENSIONS
from .query import parse_query
from .search import empty_criteria, is_empty, run_search

# URL parameter name -> criteria key, for the list-valued filters.
MULTI_PARAMS = {
    "sector": "sectors", "role": "roles", "location": "locations", "region": "regions",
    "strategy": "strategies", "firm_group": "firm_groups", "qual": "qualifications",
}


def create_app(data_dir=None):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 ** 3  # allow big zip uploads
    app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)
    store = Store(data_dir or os.environ.get("CVSEARCH_DATA", "data"))
    app.store = store
    password = os.environ.get("APP_PASSWORD")

    @app.before_request
    def _auth():
        # Optional: set APP_PASSWORD if you ever run this somewhere others can reach.
        if not password:
            return None
        auth = request.authorization
        if auth and auth.password == password:
            return None
        return Response("Login required", 401, {"WWW-Authenticate": 'Basic realm="CV Search"'})

    @app.context_processor
    def _globals():
        return {"taxonomy": taxonomy, "stats": store.stats()}

    # ---------------------------------------------------------------- search

    def criteria_from_args(args):
        c = empty_criteria()
        for param, key in MULTI_PARAMS.items():
            c[key] = [v for v in args.getlist(param) if v]
        c["keywords"] = split_keywords(args.get("kw", ""))
        c["min_years"] = _float(args.get("min_years"))
        c["max_years"] = _float(args.get("max_years"))
        c["years_flex"] = _float(args.get("flex")) or 0.0
        c["buy_side"] = args.get("buy_side") == "1"
        c["sell_side"] = args.get("sell_side") == "1"
        c["include_unknown_years"] = args.get("unknown") == "1"
        return c

    def criteria_to_params(c, q=None):
        params = []
        for param, key in MULTI_PARAMS.items():
            params += [(param, v) for v in c[key]]
        if c["keywords"]:
            params.append(("kw", join_keywords(c["keywords"])))
        for key in ("min_years", "max_years"):
            if c[key] is not None:
                params.append((key, _fmt_num(c[key])))
        if c["buy_side"]:
            params.append(("buy_side", "1"))
        if c["sell_side"]:
            params.append(("sell_side", "1"))
        if q:
            params.append(("q", q))
        return params

    @app.route("/")
    def index():
        q = request.args.get("q", "").strip()
        if q and request.args.get("parsed") != "1":
            # Natural-language box: translate to filters and redirect so the URL
            # (and the filter panel) show exactly what is being searched.
            parsed = parse_query(q)
            c = empty_criteria()
            c.update({k: v for k, v in parsed.items() if k in c})
            params = criteria_to_params(c, q) + [("parsed", "1")]
            return redirect(url_for("index") + "?" + urlencode(params))

        c = criteria_from_args(request.args)
        results, info = run_search(store, c)
        limit = 1000 if request.args.get("all") else 100
        return render_template(
            "search.html", c=c, q=q, kw_text=join_keywords(c["keywords"]), results=results[:limit], total=len(results), info=info,
            searched=not is_empty(c), export_url=url_for("export") + "?" + request.query_string.decode(),
            show_all_url=request.full_path.rstrip("?&") + ("&" if request.args else "?") + "all=1"
            if len(results) > limit else None,
        )

    @app.route("/export.csv")
    def export():
        results, _ = run_search(store, criteria_from_args(request.args))
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["Name", "Email", "Phone", "LinkedIn", "Years exp (est.)", "Current role",
                    "Location", "Sectors", "Firms", "Qualifications", "Score", "CV file", "Notes"])
        for r in results:
            w.writerow([r["name"], r["email"], r["phone"], r["linkedin"], r.get("years_experience") or "",
                        r.get("current_role", ""), r.get("primary_location") or "", ", ".join(r["sectors"]),
                        ", ".join(r["firms"]), ", ".join(r["qualifications"]), r["score"],
                        r["filename"], r["notes"]])
        return Response(out.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": "attachment; filename=shortlist.csv"})

    # ---------------------------------------------------------------- upload

    @app.route("/upload", methods=["GET", "POST"])
    def upload():
        if request.method == "GET":
            return render_template("upload.html", report=None)
        report = {"added": [], "duplicate": [], "unsupported": [], "error": [], "warnings": []}
        with tempfile.TemporaryDirectory() as tmp:
            for f in request.files.getlist("files"):
                if not f.filename:
                    continue
                name = os.path.basename(f.filename.replace("\\", "/"))
                path = os.path.join(tmp, "upload" + os.path.splitext(name)[1].lower())
                f.save(path)
                if name.lower().endswith(".zip"):
                    for inner_path, inner_name in _unzip(path, tmp):
                        _import(store, inner_path, inner_name, report)
                else:
                    _import(store, path, name, report)
        return render_template("upload.html", report=report)

    @app.route("/reparse", methods=["POST"])
    def reparse():
        n = store.reparse_all()
        flash(f"Re-analysed {n} CVs with the current keyword lists.")
        return redirect(url_for("upload"))

    # ---------------------------------------------------------------- candidates

    @app.route("/candidate/<int:cid>", methods=["GET", "POST"])
    def candidate(cid):
        cand = store.get(cid)
        if not cand:
            abort(404)
        if request.method == "POST":
            overrides = {}
            for field in EDITABLE:
                if field == "sectors":
                    value = request.form.getlist("sectors")
                    if sorted(value) == sorted(cand["parsed_sectors"]):
                        value = []
                elif field == "years_experience":
                    value = _float(request.form.get(field))
                else:
                    value = request.form.get(field, "").strip()
                overrides[field] = value
            store.update(cid, overrides, request.form.get("notes", ""))
            flash("Saved.")
            return redirect(url_for("candidate", cid=cid, back=request.args.get("back", "")))
        return render_template("candidate.html", cand=cand, back=request.args.get("back") or url_for("index"),
                               highlight=split_keywords(request.args.get("kw", "")))

    @app.route("/candidate/<int:cid>/file")
    def candidate_file(cid):
        cand = store.get(cid)
        if not cand:
            abort(404)
        return send_from_directory(store.files_dir, cand["stored_name"], download_name=cand["filename"],
                                   as_attachment=request.args.get("download") == "1")

    @app.route("/candidate/<int:cid>/delete", methods=["POST"])
    def candidate_delete(cid):
        store.delete(cid)
        flash("Candidate and CV file deleted.")
        return redirect(url_for("index"))

    @app.template_filter("highlight")
    def highlight(text, words):
        from markupsafe import Markup, escape

        text = str(escape(text))
        if words:
            pattern = re.compile("(" + "|".join(re.escape(str(escape(w))) for w in words) + ")", re.I)
            text = pattern.sub(r"<mark>\1</mark>", text)
        return Markup(text)

    @app.template_global()
    def url_without(param, value):
        """Current search URL with one filter value removed (for the 'x' on chips)."""
        args = [(k, v) for k, v in request.args.items(multi=True)
                if not (k == param and (value is None or v == value)) and k not in ("q", "all")]
        return url_for("index") + ("?" + urlencode(args) if args else "")

    return app


def split_keywords(s):
    return [a or b for a, b in re.findall(r'"([^"]+)"|([^\s,"]+)', s or "")]


def join_keywords(words):
    return " ".join(f'"{w}"' if " " in w else w for w in words)


def _float(v):
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


def _fmt_num(x):
    return str(int(x)) if float(x).is_integer() else str(x)


def _unzip(zip_path, tmp):
    out_dir = tempfile.mkdtemp(dir=tmp)
    with zipfile.ZipFile(zip_path) as z:
        for i, info in enumerate(z.infolist()):
            name = os.path.basename(info.filename)
            if info.is_dir() or not name or name.startswith((".", "~$")) or "__MACOSX" in info.filename:
                continue
            if os.path.splitext(name)[1].lower() not in SUPPORTED_EXTENSIONS:
                continue
            target = os.path.join(out_dir, f"{i}{os.path.splitext(name)[1].lower()}")
            with z.open(info) as src, open(target, "wb") as dst:
                dst.write(src.read())
            yield target, name


def _import(store, path, name, report):
    status, cid, message = store.add_file(path, name)
    entry = {"name": name, "id": cid, "message": message}
    report[status].append(entry)
    if status == "added" and message != "ok":
        report["warnings"].append(entry)
