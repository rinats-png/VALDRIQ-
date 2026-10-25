"""Authenticated JSON API and static UI, using Python's standard library.

Single-operator/local-first deployment. Put a hardened reverse proxy in front
of it when publishing, or keep the default loopback binding.
"""
import base64
import csv
import hashlib
import hmac
import io
import json
import mimetypes
import os
import re
import secrets
import sqlite3
import threading
import time
from datetime import date
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import __version__
from . import ai, connectors, db, domain, mailer

STATIC = Path(__file__).resolve().parent.parent / "web"
MAX_JSON = 2_500_000
PROJECT_ID = re.compile(r"^/api/projects/(\d+)(?:/(interview|leads|import|discover|jobs|metrics|export))?$")
LEAD_ID = re.compile(r"^/api/leads/(\d+)(?:/(draft|messages))?$")
MESSAGE_ID = re.compile(r"^/api/messages/(\d+)(?:/(approve|send))?$")
RL_LOCK = threading.Lock()
LOGIN_ATTEMPTS = {}


def password_hash(password):
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return base64.b64encode(salt + key).decode()


def check_password(password, encoded):
    try:
        data = base64.b64decode(encoded)
        candidate = hashlib.scrypt(password.encode(), salt=data[:16], n=2**14, r=8, p=1)
        return hmac.compare_digest(candidate, data[16:])
    except (ValueError, TypeError):
        return False


def insert_lead(connection, project_id, raw, source="manual", source_ref=""):
    lead = domain.normalize_lead(raw)
    project = db.one(connection.execute("SELECT * FROM projects WHERE id=?", (project_id,)))
    if not project:
        raise ValueError("Projekt nicht gefunden.")
    points = domain.score_lead(project, lead)
    # Matching business + website or business + address is a reasonable fallback
    # when external providers do not supply a stable source id.
    duplicate = connection.execute("""SELECT id FROM leads WHERE project_id=? AND
        ( (source=? AND source_ref!='' AND source_ref=?) OR
          (LOWER(business)=LOWER(?) AND (website=? OR address=?)) ) LIMIT 1""",
        (project_id, source, source_ref, lead["business"], lead.get("website", ""), lead.get("address", ""))).fetchone()
    if duplicate:
        return duplicate["id"], False
    cursor = connection.execute("""INSERT INTO leads
      (project_id,business,contact_name,email,phone,website,industry,address,notes,evidence,
       status,score,source,source_ref,permission,permission_evidence,permission_date)
       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
      (project_id, lead["business"], lead.get("contact_name", ""), lead.get("email", ""),
       lead.get("phone", ""), lead.get("website", ""), lead.get("industry", ""),
       lead.get("address", ""), lead.get("notes", ""), lead.get("evidence", ""),
       lead["status"], points["score"], source, source_ref, lead["permission"],
       lead.get("permission_evidence", ""), lead.get("permission_date", "")))
    return cursor.lastrowid, True


def execute_discovery(job_id, project_id, provider, query, city, limit, grid, database):
    try:
        with db.connect(database) as connection:
            connection.execute("UPDATE discovery_jobs SET status='running' WHERE id=?", (job_id,))
        results = connectors.search(provider, query, city, limit, grid)
        imported = 0
        with db.connect(database) as connection:
            # Explicit transaction: either all normalized records get added or none.
            for record, external_id in results:
                _, created = insert_lead(connection, project_id, record, provider, external_id)
                imported += int(created)
            connection.execute("""UPDATE discovery_jobs SET status='done', imported=?,
                finished_at=CURRENT_TIMESTAMP WHERE id=?""", (imported, job_id))
            connection.execute("INSERT INTO activities(project_id,type,detail) VALUES (?,?,?)",
                               (project_id, "discovery", f"{provider}: {imported} neue Leads"))
    except Exception as exc:
        with db.connect(database) as connection:
            connection.execute("""UPDATE discovery_jobs SET status='failed', error=?,
                finished_at=CURRENT_TIMESTAMP WHERE id=?""", (str(exc)[:400], job_id))


class Handler(BaseHTTPRequestHandler):
    server_version = "VALDRIQ/" + __version__

    def log_message(self, fmt, *args):
        # Do not log session cookies, payloads or provider API keys.
        print("[%s] %s" % (self.log_date_time_string(), fmt % args), flush=True)

    def response(self, code, content, content_type="application/json; charset=utf-8", headers=None):
        # Commit successful writes before the client observes the response.
        # Otherwise the next HTTP request can race the end of the with-block.
        if 200 <= int(code) < 400 and getattr(self, "_connection", None) is not None:
            self._connection.commit()
        if isinstance(content, (dict, list)):
            data = json.dumps(content, ensure_ascii=False).encode()
        elif isinstance(content, str):
            data = content.encode()
        else:
            data = content
        self.send_response(int(code))
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)

    def json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= MAX_JSON:
            raise ValueError("Ungültige Anfragegröße (max. 2,5 MB).")
        result = json.loads(self.rfile.read(length))
        if not isinstance(result, dict):
            raise ValueError("Ein JSON-Objekt wird erwartet.")
        return result

    def _cookie(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
            return cookie.get("valdriq_session").value if "valdriq_session" in cookie else ""
        except Exception:
            return ""

    def session(self, connection):
        token = self._cookie()
        if not token:
            return None
        return db.one(connection.execute("""SELECT s.csrf, s.user_id, u.email FROM sessions s
             JOIN users u ON u.id=s.user_id WHERE token_hash=? AND expires_at>?""",
            (hashlib.sha256(token.encode()).hexdigest(), int(time.time()))))

    def same_origin(self):
        origin = self.headers.get("Origin", "")
        allowed = os.getenv("VALDRIQ_PUBLIC_ORIGIN", "").rstrip("/")
        # For requests without Origin (e.g. CLI) CSRF token is still required.
        if origin and origin not in {allowed, "http://" + self.headers.get("Host", ""),
                                     "https://" + self.headers.get("Host", "")}:
            return False
        return True

    def authenticate(self, connection, write=False):
        session = self.session(connection)
        if not session:
            raise PermissionError("Bitte anmelden.")
        if write and (not self.same_origin() or not hmac.compare_digest(
                self.headers.get("X-CSRF-Token", ""), session["csrf"])):
            raise PermissionError("CSRF-Prüfung fehlgeschlagen.")
        return session

    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")

    def do_PATCH(self):
        self.route("PATCH")

    def do_DELETE(self):
        self.route("DELETE")

    def route(self, method):
        path = urlparse(self.path).path
        if not path.startswith("/api/"):
            if method == "GET":
                return self.static(path)
            return self.response(404, {"error": "Not found"})
        try:
            with db.connect(self.server.database) as connection:
                self._connection = connection
                if path == "/api/health" and method == "GET":
                    count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                    return self.response(200, {"version": __version__, "initialized": count > 0})
                if path == "/api/setup" and method == "POST":
                    return self.setup_account(connection, self.json_body())
                if path == "/api/login" and method == "POST":
                    return self.login(connection, self.json_body())
                if path == "/api/auth" and method == "GET":
                    session = self.session(connection)
                    return self.response(200, {"authenticated": bool(session),
                                               "email": session["email"] if session else "",
                                               "csrf": session["csrf"] if session else ""})
                session = self.authenticate(connection, write=method != "GET")
                if path == "/api/logout" and method == "POST":
                    connection.execute("DELETE FROM sessions WHERE token_hash=?",
                                       (hashlib.sha256(self._cookie().encode()).hexdigest(),))
                    return self.response(200, {"ok": True}, headers={"Set-Cookie": self.session_cookie("", 0)})
                if path == "/api/config" and method == "GET":
                    return self.response(200, {"smtp": mailer.available(),
                         "ai": bool(os.getenv("VALDRIQ_OPENAI_API_KEY")),
                         "google_places": bool(os.getenv("VALDRIQ_GOOGLE_PLACES_API_KEY")),
                         "scraper_kit": bool(os.getenv("VALDRIQ_SCRAPER_KIT_DIR"))})
                if path == "/api/projects":
                    if method == "GET":
                        return self.response(200, db.rows(connection.execute(
                            "SELECT * FROM projects ORDER BY updated_at DESC,id DESC")))
                    if method == "POST":
                        return self.project_create(connection, self.json_body())
                if path == "/api/suppression":
                    if method == "GET":
                        return self.response(200, db.rows(connection.execute("SELECT * FROM suppression ORDER BY created_at DESC")))
                    if method == "POST":
                        body = self.json_body()
                        email = domain.require_string(body.get("email"), "email", 320).lower()
                        if not domain.EMAIL_RE.fullmatch(email):
                            raise ValueError("Ungültige E-Mail-Adresse.")
                        reason = domain.require_string(body.get("reason", "Widerspruch"), "reason", 500)
                        connection.execute("INSERT OR REPLACE INTO suppression(email,reason) VALUES(?,?)", (email, reason))
                        return self.response(200, {"ok": True})
                matched = PROJECT_ID.fullmatch(path)
                if matched:
                    return self.project_route(connection, method, int(matched[1]), matched[2])
                matched = LEAD_ID.fullmatch(path)
                if matched:
                    return self.lead_route(connection, method, int(matched[1]), matched[2])
                matched = MESSAGE_ID.fullmatch(path)
                if matched:
                    return self.message_route(connection, method, int(matched[1]), matched[2])
                return self.response(404, {"error": "Endpunkt nicht gefunden."})
        except PermissionError as exc:
            return self.response(403, {"error": str(exc)})
        except (ValueError, json.JSONDecodeError, TypeError) as exc:
            return self.response(400, {"error": str(exc)})
        except sqlite3.IntegrityError:
            return self.response(409, {"error": "Eintrag bereits vorhanden oder ungültige Referenz."})
        except Exception as exc:
            print(f"Internal error: {type(exc).__name__}: {exc}", flush=True)
            return self.response(500, {"error": "Interner Fehler. Serverlogs prüfen."})

    def static(self, path):
        files = {"/": "index.html", "/index.html": "index.html", "/app.js": "app.js", "/styles.css": "styles.css", "/favicon.svg": "favicon.svg"}
        filename = files.get(path)
        if not filename:
            return self.response(404, "Not found", "text/plain")
        content = (STATIC / filename).read_bytes()
        mime = {".js": "application/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".html": "text/html"}[Path(filename).suffix]
        return self.response(200, content, mime + "; charset=utf-8")

    def session_cookie(self, token, seconds):
        secure = "; Secure" if os.getenv("VALDRIQ_PUBLIC_ORIGIN", "").startswith("https://") else ""
        return f"valdriq_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={seconds}{secure}"

    def new_session(self, connection, user_id):
        token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
        connection.execute("INSERT INTO sessions(token_hash,user_id,csrf,expires_at) VALUES(?,?,?,?)",
                           (hashlib.sha256(token.encode()).hexdigest(), user_id, csrf, int(time.time()) + 86400 * 7))
        return self.response(200, {"ok": True, "csrf": csrf},
                             headers={"Set-Cookie": self.session_cookie(token, 86400 * 7)})

    def setup_account(self, connection, data):
        if not self.same_origin():
            raise PermissionError("Ungültige Herkunft.")
        if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
            raise PermissionError("Einrichtung abgeschlossen.")
        email = domain.require_string(data.get("email"), "email", 320).lower()
        password = domain.require_string(data.get("password"), "password", 256)
        if not domain.EMAIL_RE.fullmatch(email) or len(password) < 12:
            raise ValueError("Gültige E-Mail und Passwort mit mindestens 12 Zeichen erforderlich.")
        cursor = connection.execute("INSERT INTO users(email,password_hash) VALUES(?,?)",
                                    (email, password_hash(password)))
        return self.new_session(connection, cursor.lastrowid)

    def login(self, connection, data):
        if not self.same_origin():
            raise PermissionError("Ungültige Herkunft.")
        ip = self.client_address[0]
        with RL_LOCK:
            previous = [t for t in LOGIN_ATTEMPTS.get(ip, []) if time.time() - t < 600]
            if len(previous) >= 8:
                raise PermissionError("Zu viele Loginversuche. Bitte später erneut versuchen.")
            LOGIN_ATTEMPTS[ip] = previous + [time.time()]
        email = str(data.get("email", "")).lower()
        password = str(data.get("password", ""))
        user = connection.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if not user or not check_password(password, user["password_hash"]):
            raise PermissionError("E-Mail oder Passwort falsch.")
        with RL_LOCK:
            LOGIN_ATTEMPTS.pop(ip, None)
        return self.new_session(connection, user["id"])

    def project_create(self, connection, body):
        data = domain.clean_project(body)
        name = domain.require_string(data.get("name"), "name", 600)
        cursor = connection.execute("INSERT INTO projects(name) VALUES(?)", (name,))
        pid = cursor.lastrowid
        self.update_fields(connection, "projects", pid, {k: v for k, v in data.items() if k != "name"}, domain.PROJECT_FIELDS)
        return self.response(201, {"id": pid})

    def update_fields(self, connection, table, item_id, data, allowed):
        if not data:
            return
        entries = {k: v for k, v in data.items() if k in allowed}
        if not entries:
            return
        values = list(entries.values())
        sql = ",".join(f"{key}=?" for key in entries)
        connection.execute(f"UPDATE {table} SET {sql}, updated_at=CURRENT_TIMESTAMP WHERE id=?", (*values, item_id))

    def project_route(self, connection, method, project_id, action):
        project = db.one(connection.execute("SELECT * FROM projects WHERE id=?", (project_id,)))
        if not project:
            return self.response(404, {"error": "Projekt nicht gefunden."})
        if action is None:
            if method == "GET":
                return self.response(200, project)
            if method == "PATCH":
                self.update_fields(connection, "projects", project_id, domain.clean_project(self.json_body()), domain.PROJECT_FIELDS)
                return self.response(200, {"ok": True})
            if method == "DELETE":
                connection.execute("DELETE FROM projects WHERE id=?", (project_id,))
                return self.response(200, {"ok": True})
        if action == "interview" and method == "GET":
            return self.response(200, domain.interview(project))
        if action == "metrics" and method == "GET":
            leads = connection.execute("SELECT COUNT(*) FROM leads WHERE project_id=?", (project_id,)).fetchone()[0]
            qualified = connection.execute("SELECT COUNT(*) FROM leads WHERE project_id=? AND score>=60", (project_id,)).fetchone()[0]
            sent = connection.execute("""SELECT COUNT(*) FROM messages m JOIN leads l ON l.id=m.lead_id
                    WHERE l.project_id=? AND m.state='sent'""", (project_id,)).fetchone()[0]
            replied = connection.execute("SELECT COUNT(*) FROM leads WHERE project_id=? AND status='replied'", (project_id,)).fetchone()[0]
            return self.response(200, {"leads": leads, "qualified": qualified, "sent": sent, "replied": replied})
        if action == "leads":
            if method == "GET":
                params = parse_qs(urlparse(self.path).query)
                search = str(params.get("q", [""])[0])[:100]
                return self.response(200, db.rows(connection.execute("""SELECT * FROM leads WHERE project_id=?
                    AND (business LIKE ? OR industry LIKE ? OR address LIKE ?) ORDER BY score DESC,id DESC LIMIT 500""",
                    (project_id, *(f"%{search}%",) * 3))))
            if method == "POST":
                lead_id, created = insert_lead(connection, project_id, self.json_body())
                return self.response(201 if created else 200, {"id": lead_id, "created": created})
        if action == "import" and method == "POST":
            data = self.json_body()
            parsed = domain.parse_csv(domain.require_string(data.get("csv"), "csv", 2_000_000))
            added = 0
            source = "csv"
            for record in parsed:
                _, created = insert_lead(connection, project_id, record, source)
                added += int(created)
            return self.response(200, {"imported": added, "duplicates": len(parsed) - added})
        if action == "discover" and method == "POST":
            params = self.json_body()
            provider = params.get("provider")
            if provider not in {"google_places", "scraper_kit"}:
                raise ValueError("Rechercheanbieter auswählen.")
            query = domain.require_string(params.get("query"), "Suchbegriff", 140)
            city = domain.require_string(params.get("city"), "Stadt", 120)
            limit = int(params.get("limit", 20))
            grid = int(params.get("grid", 1))
            if not 1 <= limit <= 200 or not 1 <= grid <= 3:
                raise ValueError("Limit 1–200; Grid 1–3.")
            if provider == "google_places":
                limit = min(limit, 20)
            running = connection.execute("""SELECT COUNT(*) FROM discovery_jobs
                WHERE status IN ('queued','running')""").fetchone()[0]
            if running:
                raise ValueError("Es läuft bereits eine Recherche. Bitte Abschluss abwarten.")
            cursor = connection.execute("""INSERT INTO discovery_jobs(project_id,provider,query,city)
                VALUES(?,?,?,?)""", (project_id, provider, query, city))
            job_id = cursor.lastrowid
            connection.commit()  # Worker uses a new connection, so commit before spawning it.
            thread = threading.Thread(target=execute_discovery,
                args=(job_id, project_id, provider, query, city, limit, grid, self.server.database), daemon=True)
            thread.start()
            return self.response(202, {"job_id": job_id, "status": "queued"})
        if action == "jobs" and method == "GET":
            return self.response(200, db.rows(connection.execute(
                "SELECT * FROM discovery_jobs WHERE project_id=? ORDER BY id DESC LIMIT 30", (project_id,))))
        if action == "export" and method == "GET":
            leads = db.rows(connection.execute("SELECT * FROM leads WHERE project_id=? ORDER BY id", (project_id,)))
            output = io.StringIO()
            fields = ["business", "contact_name", "email", "phone", "website", "industry", "address", "notes",
                      "evidence", "status", "score", "source", "permission", "permission_evidence", "permission_date"]
            writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(leads)
            return self.response(200, "\ufeff" + output.getvalue(), "text/csv; charset=utf-8",
                                 {"Content-Disposition": f'attachment; filename="valdriq-project-{project_id}.csv"'})
        return self.response(404, {"error": "Unbekannte Aktion."})

    def lead_route(self, connection, method, lead_id, action):
        lead = db.one(connection.execute("SELECT * FROM leads WHERE id=?", (lead_id,)))
        if not lead:
            return self.response(404, {"error": "Lead nicht gefunden."})
        if action is None:
            if method == "GET":
                return self.response(200, lead)
            if method == "PATCH":
                data = domain.normalize_lead({**lead, **self.json_body()})
                project = db.one(connection.execute("SELECT * FROM projects WHERE id=?", (lead["project_id"],)))
                data["score"] = domain.score_lead(project, data)["score"]
                self.update_fields(connection, "leads", lead_id, data, (*domain.LEAD_FIELDS, "score"))
                return self.response(200, {"ok": True})
            if method == "DELETE":
                connection.execute("DELETE FROM leads WHERE id=?", (lead_id,))
                return self.response(200, {"ok": True})
        if action == "draft" and method == "POST":
            project = db.one(connection.execute("SELECT * FROM projects WHERE id=?", (lead["project_id"],)))
            kind = self.json_body().get("kind", "intro")
            if kind == "followup":
                sent = connection.execute("SELECT 1 FROM messages WHERE lead_id=? AND state='sent' LIMIT 1", (lead_id,)).fetchone()
                if not sent or lead["status"] in {"replied", "won", "lost"}:
                    raise ValueError("Follow-up nur nach einer früheren gesendeten E-Mail ohne Antwort/Abschluss.")
            message = ai.generate_message(project, lead, kind)
            cursor = connection.execute("INSERT INTO messages(lead_id,subject,body) VALUES(?,?,?)",
                                        (lead_id, message["subject"], message["body"]))
            return self.response(201, {"id": cursor.lastrowid, **message})
        if action == "messages" and method == "GET":
            return self.response(200, db.rows(connection.execute(
                "SELECT * FROM messages WHERE lead_id=? ORDER BY id DESC", (lead_id,))))
        return self.response(404, {"error": "Unbekannte Aktion."})

    def message_route(self, connection, method, message_id, action):
        message = db.one(connection.execute("""SELECT m.*, l.email, l.permission, l.permission_evidence,
            l.permission_date, l.status AS lead_status, l.project_id FROM messages m
            JOIN leads l ON l.id=m.lead_id WHERE m.id=?""", (message_id,)))
        if not message:
            return self.response(404, {"error": "Nachricht nicht gefunden."})
        if action is None and method == "PATCH":
            if message["state"] not in {"draft", "failed"}:
                raise ValueError("Nur Entwürfe oder fehlgeschlagene Nachrichten sind bearbeitbar.")
            data = self.json_body()
            subject = domain.require_string(data.get("subject"), "Betreff", 300)
            if "\n" in subject or "\r" in subject:
                raise ValueError("Betreff darf keine Zeilenumbrüche enthalten.")
            body = domain.require_string(data.get("body"), "Nachricht", 10000)
            connection.execute("UPDATE messages SET subject=?, body=?, state='draft',error='' WHERE id=?",
                               (subject, body, message_id))
            return self.response(200, {"ok": True})
        if action == "approve" and method == "POST":
            if message["state"] not in {"draft", "failed"}:
                raise ValueError("Nachricht ist nicht freigabefähig.")
            suppressed = connection.execute("SELECT 1 FROM suppression WHERE email=?", (message["email"].lower(),)).fetchone()
            eligible, reason = domain.can_send(message, bool(suppressed))
            if not eligible:
                raise ValueError(reason)
            if message["lead_status"] in {"replied", "won", "lost"}:
                raise ValueError("Lead hat bereits reagiert oder wurde abgeschlossen.")
            connection.execute("UPDATE messages SET state='approved',error='' WHERE id=?", (message_id,))
            return self.response(200, {"ok": True})
        if action == "send" and method == "POST":
            if message["state"] != "approved":
                raise ValueError("Nur freigegebene Nachrichten können versandt werden.")
            suppressed = connection.execute("SELECT 1 FROM suppression WHERE email=?", (message["email"].lower(),)).fetchone()
            eligible, reason = domain.can_send(message, bool(suppressed))
            if not eligible or message["lead_status"] in {"replied", "won", "lost"}:
                raise ValueError(reason or "Kontakt ist abgeschlossen.")
            if not mailer.available():
                raise ValueError("SMTP-Konfiguration fehlt.")
            # Claim for exactly one in-process attempt, then release the SQLite lock
            # before making a slow network call.
            changed = connection.execute("UPDATE messages SET state='sending' WHERE id=? AND state='approved'", (message_id,))
            if changed.rowcount != 1:
                raise ValueError("Nachricht wird bereits versandt.")
            connection.commit()
            try:
                mailer.deliver(message["email"], message["subject"], message["body"])
            except mailer.MailError as exc:
                connection.execute("UPDATE messages SET state='failed',error=? WHERE id=?", (str(exc), message_id))
                connection.commit()
                return self.response(502, {"error": str(exc)})
            connection.execute("UPDATE messages SET state='sent',sent_at=CURRENT_TIMESTAMP,error='' WHERE id=?", (message_id,))
            connection.execute("UPDATE leads SET status='contacted',last_contact_at=CURRENT_TIMESTAMP WHERE id=?",
                               (message["lead_id"],))
            connection.execute("INSERT INTO activities(project_id,lead_id,type,detail) VALUES(?,?,?,?)",
                               (message["project_id"], message["lead_id"], "email_sent", "Freigegebene E-Mail versandt"))
            return self.response(200, {"ok": True, "state": "sent"})
        return self.response(404, {"error": "Unbekannte Aktion."})


def run():
    database = db.initialize()
    # Unknown delivery state after a crash must never be silently retried.
    with db.connect(database) as connection:
        connection.execute("""UPDATE messages SET state='failed',
            error='Unklarer Versandzustand nach Neustart: vor erneuter Freigabe SMTP-Protokoll prüfen.'
            WHERE state='sending'""")
        connection.execute("""UPDATE discovery_jobs SET status='failed',
            error='Recherche wurde durch einen Neustart unterbrochen.', finished_at=CURRENT_TIMESTAMP
            WHERE status IN ('running','queued')""")
    host = os.getenv("VALDRIQ_HOST", "127.0.0.1")
    port = int(os.getenv("VALDRIQ_PORT", "8765"))
    server = ThreadingHTTPServer((host, port), Handler)
    server.database = database
    print(f"VALDRIQ {__version__} — http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
