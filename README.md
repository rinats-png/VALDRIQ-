# VALDRIQ

**Guided Lead Intelligence · Research → Qualify → Connect**

VALDRIQ ist ein eigenständiger, deutschsprachiger Lead-Recherche- und CRM-Workspace. Ein geführter Assistent fragt die notwendigen strategischen Angaben schrittweise ab. Anschließend kannst du Unternehmen über eine optionale Google-Places-API oder das separat installierte Google Maps Scraper Kit suchen, CSVs importieren, Leads deduplizieren, transparent bewerten, personalisierte E-Mail-Entwürfe erzeugen und **nach dokumentierter Berechtigung sowie expliziter Freigabe einzeln versenden**.

> **Status:** Lauffähige lokale Einzelbenutzer-Version v0.1.0. Kein vollautomatisches SaaS-Produkt, keine juristische Freigabe von Werbeaktionen und keine Garantie auf externe Datenquellen. Externe Open-Source-Projekte werden nicht in dieses Repository hineinkopiert. Ihre Funktionen sind als eigenständige Komponenten bzw. Schnittstellen aufgenommen.

## Funktionsumfang

| Bereich | Aktuell implementiert | Hinweise |
|---|---|---|
| Setup und Sicherheit | Ersteinrichtung, scrypt-Passworthash, Sessions, SameSite-Cookie, CSRF-Prüfung, Login-Drosselung | Einzelner Admin / lokale Installation |
| Strategischer Assistent | 16 adaptive Pflichtfragen, Fortschritt, Empfehlungen, nachträgliche Bearbeitung | Fragt immer nur noch fehlende Angaben |
| Google Maps / Places | Google Places (New) API, Google Maps Scraper Kit per optionalem lokalem CLI-Connector | API-Keys / externer Dienst separat |
| CSV-Import | Scraper-Kit-Format, Alias-Spalten, Validierung, 1000 Datensätze pro Import | Keine Kontakte automatisch freigegeben |
| CRM | Projekte, Leads, Ansprechpartner, Pipeline-Status, Notizen, Quellenhinweise | SQLite; Daten lokal |
| Lead Scoring | Nachvollziehbare Branchen-, Standort-, Kanal- und Quellensignale | Kein behauptetes KI-Prognosemodell |
| Entwürfe | Vier Vorlagen (Erstkontakt, Nutzen, Demo, Follow-up); optional OpenAI zur Individualisierung | Kein Versand durch KI, Follow-up nur nach Erstversand |
| E-Mail-Versand | SMTP mit TLS, Entwurf bearbeiten, Einzel-Freigabe, Einmal-Versandversuch, Fehlerstatus | Nur bei dokumentierter Kontaktgrundlage |
| Compliance | Opt-in-/Bestandskundennachweise, Widerspruchs-/Sperrliste, Versandblockaden | Rechtmäßigkeit bleibt Betreiberverantwortung |
| Datenexport | CSV-Export und Backup über SQLite-Datei | Für Einzeluser-Auszug geeignet |
| Betrieb | Docker, Compose, Python ohne Runtime-Pakete, Unittests, CI | Kein Multi-Tenant-Betrieb |

## Schnellstart

Voraussetzung: **Python 3.12+**. Für das lokale Grundsystem sind keine pip- oder npm-Installationen nötig.

```bash
cd valdriq
python3 -m valdriq
```

Browser: **http://127.0.0.1:8765**. Beim ersten Start Admin-E-Mail und ein Passwort mit mindestens zwölf Zeichen festlegen. Anschließend das erste Projekt anlegen und den Fragen folgen. Die Datenbank entsteht unter `data/valdriq.db`.

### Docker

```bash
cp .env.example .env
docker compose up --build -d
```

Danach `http://localhost:8765` öffnen. Das Compose-Beispiel bindet nur an die Loopback-Schnittstelle des Hosts.

### Konfiguration lokaler Integrationen

`.env` wird von Docker Compose automatisch gelesen. Bei direktem Python-Start die benötigten Werte in der Prozessumgebung setzen (Beispiel):

```bash
export VALDRIQ_GOOGLE_PLACES_API_KEY='dein-key'
export VALDRIQ_OPENAI_API_KEY='dein-key'
python3 -m valdriq
```

Die komplette Variablenliste steht in [.env.example](.env.example); genaue Anleitungen unter [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md).

## Erste Schritte

1. **Projekt und Zielgruppe festlegen:** Produkt, Zielbranchen, Entscheider, Geografie und Verkaufsargumente im Assistenten angeben.
2. **Recherche starten:** Quelle, Branche und Stadt wählen. Die Suche läuft als Hintergrundjob und importiert Ergebnisse ins Projekt.
3. **Leads prüfen:** Relevanz, Website, Quelle und ggf. Ansprechpartner kontrollieren; deduplizierte Datensätze erscheinen im CRM.
4. **Nachricht erstellen:** Entwurf generieren, faktisch prüfen und bearbeiten.
5. **Kontaktgrundlage dokumentieren:** Einwilligung oder tatsächlich anwendbare Bestandskundenausnahme mit Quelle und Datum eintragen.
6. **Freigeben und senden:** Manuell pro Nachricht freigeben; SMTP muss separat eingerichtet sein. Widersprüche sofort auf der Sperrliste erfassen.

**Wichtig:** Die Recherche nach einer E-Mail-Adresse berechtigt nicht zum Versand einer Werbe-E-Mail. Gerade in Deutschland gelten für B2B-E-Mails strenge UWG-Vorgaben. Siehe [SECURITY.md](SECURITY.md) und [docs/COMPLIANCE.md](docs/COMPLIANCE.md).

## Architektur

```text
VALDRIQ
├── web/                     # responsives Dashboard, Vanilla JS/CSS
├── valdriq/
│   ├── server.py            # JSON API, Sessions, CRM und Versandworkflow
│   ├── db.py                # SQLite-Schema und Transaktionen
│   ├── domain.py            # Bedarfsassistent, Validierung und Lead Scoring
│   ├── connectors.py        # Google Places API / Scraper Kit (CLI)
│   ├── ai.py                # optionales OpenAI-Modul mit Template-Fallback
│   └── mailer.py            # SMTP mit TLS
├── tests/                   # Fach- und HTTP-Integrationstests
├── docs/                    # Betrieb, Lizenzen, Integration, Ausbauplan
├── .github/workflows/       # automatische Tests
├── Dockerfile
└── compose.yaml
```

**Warum ohne große Abhängigkeitskette?** Die erste Version lässt sich in Codex sehr schnell verstehen, überprüfen und verändern. Die Kernarchitektur ist absichtlich modular. Für einen kommerziellen Multi-User-/SaaS-Betrieb ist eine zweite Ausbaustufe mit PostgreSQL, Rollen, Queue-Workern, Auditlog und überprüfter Infrastruktur nötig. Der konkrete Plan steht unter [docs/ROADMAP.md](docs/ROADMAP.md).

## Repositories und Lizenzstrategie

VALDRIQ ist **neu geschriebener MIT-Code**. Drittanbieter-Code ist nicht gebündelt oder kopiert. Die zuvor besprochenen Repositories dienten als Funktionsreferenz, und wo sinnvoll wird eine externe Integration angeboten. Besonders wichtig: Twenty und Listmonk verwenden AGPL-Bestandteile; n8n verwendet eine Sonderlizenz. Daher sind diese Produkte bewusst nicht in einen angeblich einheitlichen MIT-Codebestand eingebaut. Vollständige Übersicht: [docs/SOURCES.md](docs/SOURCES.md).

## Tests

```bash
python3 -m unittest discover -v
node --check web/app.js  # optional
```

Ein CI-Workflow führt die Python-Tests bei Pushes und Pull Requests aus.

## Geplanter GitHub-Push

Du kannst nach der Prüfung ein neues **leeres** Repository anlegen und diesen Projektordner als Initial-Commit pushen (ohne `.env`/Datenbank). Beispiel:

```bash
cd valdriq
git init
git add .
git commit -m "feat: initial VALDRIQ lead intelligence workspace"
git branch -M main
git remote add origin https://github.com/DEIN-NAME/valdriq.git
git push -u origin main
```

Noch nicht selbst ausführen müssen: Sobald du die URL nennst, kann der Upload gesondert vorbereitet werden. **Kein Push wurde im Rahmen dieser Erstellung ausgeführt.**

## Lizenz

MIT für den neu geschriebenen VALDRIQ-Code. Rechte, API-Bedingungen und Lizenzen externer Projekte bleiben eigenständig. Der Name VALDRIQ ist ein Arbeitstitel; Marken-/Domainverfügbarkeit ist nicht abschließend geprüft.
