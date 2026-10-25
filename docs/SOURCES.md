# Recherchebasis und Lizenzgrenzen

Stand der Repositoriesichtung: 25. Oktober 2026. Nur die **eigenen Originaldateien** von VALDRIQ stehen unter dessen MIT-Lizenz; externe Repositories wurden nicht vendort, geforkt oder in den Code kopiert.

| Externes Repository | Relevante Idee | VALDRIQ-Umsetzung | Lizenz-/Integrationsstatus |
|---|---|---|---|
| [Mahanaicoach/google-maps-scraper-kit](https://github.com/Mahanaicoach/google-maps-scraper-kit) | Regionale Firmenrecherche / CSV | Optionaler CLI-Adapter | MIT-Datei geprüft; extern zu installieren |
| [AI-Invention/lead-pipeline](https://github.com/AI-Invention/lead-pipeline) | Research → Draft → Reply | Eigenständige Pipeline / getrennte Stufen | MIT-Datei geprüft; kein Code übernommen |
| [eracle/OpenOutreach](https://github.com/eracle/OpenOutreach) | KI-Qualifizierung und Kontext | Nachvollziehbares Scoring; optional grounded AI draft | Lizenz in dieser Sitzung nicht sicher verifiziert; keine Übernahme |
| [twentyhq/twenty](https://github.com/twentyhq/twenty) | Kontakte/Opportunities/CRM | Eigenes schlankes CRM | AGPLv3 sowie ausgewiesene Enterprise-Komponenten: nicht eingebaut |
| [mautic/mautic](https://github.com/mautic/mautic) | Kampagnenautomation | Für Ausbauphase vorgesehen | Vor Integration Lizenz und Version prüfen |
| [n8n-io/n8n](https://github.com/n8n-io/n8n) | Workflow-Orchestrierung | Hintergrundjobs und eigene Module | Sustainable Use License / Sonderbedingungen separat prüfen |
| [knadh/listmonk](https://github.com/knadh/listmonk) | Listen und E-Mail-Kampagnen | Suppression, manuelle Einzelversendung | AGPLv3-Datei geprüft; nicht eingebaut |
| [ozhehkovski/geoleadscraper](https://github.com/ozhehkovski/geoleadscraper) | Lokale Suche, Kontakt-Export | Konzeptuell abgedeckt durch Recherche/CSV | Lizenz nicht verifiziert; nicht eingebaut |

## Warum nicht "alles zusammenkopieren"?

Für ein nutzbares Produkt braucht es konsistente Datenmodelle, Authentifizierung, Aktualisierbarkeit, Datenschutz und eine saubere Lizenzgrundlage. Eine bloße Mischung aus Drittanbieterquellen würde inkompatible APIs, Datenbankschemata und Lizenzen erzeugen. VALDRIQ realisiert deshalb dieselben sinnvollen **Workflows** eigenständig und hängt externe Tools nur an dokumentierte Schnittstellen.

Funktional **noch nicht gleichwertig** zu Mautic, Twenty oder n8n: insbesondere keine komplexen Kampagnen-Builder, geteilte Team-Workspaces, mehrstufige Sequenzengine, omnichannel Outreach oder Workflow-Editor. Diese Funktionen sind ausdrücklich als spätere Ausbauphasen geplant.
