# Sicherheit und Produktivbetrieb

**Standardbetrieb:** Ein Admin auf einem privaten Rechner oder via SSH-Tunnel. Es handelt sich nicht um ein für das offene Internet gehärtetes Multi-Tenant-CRM.

- Server bindet standardmäßig an `127.0.0.1:8765`; Docker Compose veröffentlicht ebenfalls nur auf Loopback.
- Passwörter: `hashlib.scrypt` mit zufälligem Salt.
- Sessions: zufällige Tokens, deren SHA-256-Hash in der Datenbank liegt; 7 Tage Laufzeit, HttpOnly und SameSite=Strict.
- Mutationen nach Anmeldung: CSRF-Token plus Origin-Prüfung; einfache Limitierung von Loginversuchen.
- SQL: parametrisiert. HTML-Daten in der Oberfläche werden maskiert. Keine benutzerdefinierten Shell-Ausdrücke.
- Keine automatischen Werbe-E-Mails: Einwilligungs-/Bestandskundenbeleg, Widerspruchssperre, Freigabe und nochmalige Prüfung beim Versand.
- SMTP: TLS verpflichtend. API- und SMTP-Geheimnisse gehören in die Prozessumgebung oder einen Secret Store.
- **Ersteinrichtung:** Die allererste Person, die den uninitialisierten Dienst erreicht, kann das Admin-Konto anlegen. Daher **immer lokal initialisieren, bevor irgendein öffentlicher Zugang geschaltet wird**.
- Bei einem Neustart während des Mailversands markiert VALDRIQ den unbekannten Versandzustand als fehlgeschlagen und verlangt manuelle Kontrolle vor einem neuen Versuch.

## Grenzen / erforderliche Härtung

- Kein eingebautes TLS, kein RBAC/MFA, keine Mandantentrennung, keine umfassenden API-Ratelimits und kein offizielles Datenschutz-/Löschkonzept.
- SQLite und Python `http.server` eignen sich für lokalen Einzelbenutzerbetrieb, nicht für hohe Last oder öffentliche SaaS-Bereitstellung.
- Der Scraper-Kit-Connector kann einen externen Prozess starten. Nur ein lokaler Administrator darf `VALDRIQ_SCRAPER_KIT_DIR` setzen. Den externen Dienst nicht ungeschützt veröffentlichen.
- Für produktive Mails: SPF/DKIM/DMARC, SMTP-Auswahl, Bounce-/Reply-Handling, Rechtstexte und Einwilligungsbelege unabhängig prüfen.
- Keine schutzwürdigen personenbezogenen Daten zu Testzwecken importieren. Datenbank und Backups verschlüsselt aufbewahren.

Sicherheitsprobleme bitte privat an den jeweiligen Repository-Maintainer melden; keine personenbezogenen Daten oder Schlüssel in öffentliche Issues.
