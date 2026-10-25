import http.cookiejar
import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

from valdriq import db
from valdriq.server import Handler
from tests.test_domain import sample_project


class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.database = db.initialize(Path(cls.folder.name) / "test.db")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.server.database = cls.database
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.folder.cleanup()

    def setUp(self):
        self.client = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.csrf = ""

    def req(self, route, method="GET", body=None, use_csrf=True):
        headers = {}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if use_csrf and self.csrf and method != "GET":
            headers["X-CSRF-Token"] = self.csrf
        request = Request(self.base + "/api" + route, data=json.dumps(body).encode() if body is not None else None,
                          headers=headers, method=method)
        try:
            with self.client.open(request, timeout=10) as response:
                return response.status, json.load(response)
        except HTTPError as exc:
            return exc.code, json.load(exc)

    def login(self):
        with db.connect(self.database) as conn:
            count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if not count:
            status, data = self.req("/setup", "POST", {"email": "admin@example.de", "password": "strong-password-2026"})
        else:
            status, data = self.req("/login", "POST", {"email": "admin@example.de", "password": "strong-password-2026"})
        self.assertEqual(status, 200)
        self.csrf = data["csrf"]

    def test_01_bootstrap_auth_csrf(self):
        self.assertEqual(self.req('/projects')[0], 403)
        self.login()
        status, _ = self.req('/projects', 'POST', {'name': 'No CSRF'}, use_csrf=False)
        self.assertEqual(status, 403)
        self.assertEqual(self.req('/projects', 'POST', {'name': 'Valid project'})[0], 201)

    def test_02_project_lead_draft_permission_and_sending(self):
        self.login()
        status, response = self.req('/projects', 'POST', {'name': 'EIRA'})
        self.assertEqual(status, 201)
        pid = response['id']
        update = self.req(f'/projects/{pid}', 'PATCH', sample_project())
        self.assertEqual(update[0], 200, update)
        self.assertTrue(self.req(f'/projects/{pid}/interview')[1]['complete'])
        status, lead = self.req(f'/projects/{pid}/leads', 'POST', {'business': 'Praxis A', 'email': 'info@example.de'})
        self.assertEqual(status, 201)
        lid = lead['id']
        duplicate = self.req(f'/projects/{pid}/leads', 'POST', {'business': 'Praxis A', 'email': 'info@example.de'})
        self.assertEqual(duplicate[1]['created'], False, (duplicate, self.req(f'/projects/{pid}/leads')))
        status, draft = self.req(f'/leads/{lid}/draft', 'POST', {})
        self.assertEqual(status, 201)
        mid = draft['id']
        self.assertEqual(self.req(f'/messages/{mid}/approve', 'POST', {})[0], 400)
        self.assertEqual(self.req(f'/leads/{lid}', 'PATCH', {'permission': 'consent',
                     'permission_evidence': 'Opt-in log', 'permission_date': '2026-10-25'})[0], 200)
        self.assertEqual(self.req('/suppression', 'POST', {'email': 'info@example.de', 'reason': 'Widerspruch'})[0], 200)
        self.assertEqual(self.req(f'/messages/{mid}/approve', 'POST', {})[0], 400)
        # A different verified recipient can be approved and sent, after config.
        self.assertEqual(self.req(f'/leads/{lid}', 'PATCH', {'email': 'new@example.de'})[0], 200)
        self.assertEqual(self.req(f'/messages/{mid}/approve', 'POST', {})[0], 200)
        with patch('valdriq.server.mailer.available', return_value=True), patch('valdriq.server.mailer.deliver') as mocked:
            self.assertEqual(self.req(f'/messages/{mid}/send', 'POST', {})[0], 200)
            mocked.assert_called_once()
        self.assertEqual(self.req(f'/messages/{mid}/send', 'POST', {})[0], 400)

    def test_03_csv_and_export(self):
        self.login()
        response = self.req('/projects', 'POST', {'name': 'CSV Project'})
        self.assertEqual(response[0], 201, response)
        pid = response[1]['id']
        csv = 'title,emails,category,address\nBetrieb X,hello@company.de,Handwerk,Frankfurt\n'
        self.assertEqual(self.req(f'/projects/{pid}/import', 'POST', {'csv': csv})[1]['imported'], 1)
        self.assertEqual(len(self.req(f'/projects/{pid}/leads')[1]), 1)


if __name__ == '__main__':
    unittest.main()
