# Entwicklungsplan für ein kommerzielles Produkt

VALDRIQ v0.1 ist **ein lauffähiger Single-Operator-Prototyp**, nicht die behauptete Integration aller kompletten Fremdsysteme. Die folgenden Erweiterungen sind priorisiert.

## P0 — Vor Internet-Exposition

1. Aus SQLite auf PostgreSQL migrieren, Versionierung der Schema-Migrationen ergänzen.
2. Reverse Proxy (HTTPS, HSTS), Backup-Verschlüsselung, Monitoring, zentrale Secrets-Verwaltung, Security Review und Penetrationstest.
3. Rollen/Teams/Mandantentrennung inklusive Row-Level-Security und Auditlog entwickeln.
4. API-Ratelimits, Request-/Job-Quoten, Worker-Isolation, Provider-Timeouts, Retrystrategie und Dead-Letter-Queue.
5. Versions-/Update-Mechanismus und automatisierte Backups mit Wiederherstellungstest.

## P1 — Mehr Daten und bessere Qualifizierung

1. Universelle Datenquellen-Plugin-API; Apollo, Firmenregister/Verzeichnisse nur mit expliziten Nutzungsrechten; OSM/Overpass wo passend.
2. Dublettenabgleich nach Domain, Adresse, Handelsregister-ID und normalisierter Firmenbezeichnung.
3. Nachweisbasierte KI-Recherche: strukturierte Website-Fakten, Quellenlinks, Zeitstempel, Unsicherheitsindikator.
4. RAG-basierte Angebotspalette und nachvollziehbare Lead-Priorisierung je Kampagne.
5. Mehrsprachigkeit, Regionen, Segmentlisten, gespeicherte Suchen, intelligente Projektvorschläge.

## P2 — Vertriebsprozesse und Kommunikation

1. Kampagnen-Designer für ausschließlich zulässige Kontakte mit Einwilligungsprüfung je Kontakt/Versand.
2. IMAP/Webhook-Eingang, Antwortklassifizierung, sicherer Stopp bei Reply/Opt-out/Bounce.
3. Wiedervorlagen, freizugebende Follow-up-Entwürfe und Benachrichtigungen.
4. E-Mail-Vorlagenvarianten, dedizierte SMTP-Domain- und Deliverability-Checks (SPF, DKIM, DMARC).
5. Integration vorhandener CRMs über externe APIs statt Copyleft-Code-Kopie.

## P3 — SaaS und Analytics

1. Abrechnung, Mandantentrennung, Limits und Adminportal.
2. Pipeline-Reports, Quellenperformance, Conversion-Auswertung ohne unseriöse Öffnungstracking-Versprechen.
3. Konfigurierbare Unternehmensdatenbanken, interne Team-Workflows und DSGVO-Self-Service.
4. Transparente KI-Kosten, Provider-Health, DSGVO-Löschkonzepte und Datenresidenz.

## Definition of Done

Jede neue Funktion benötigt API-/UI-Tests, Rechteprüfung, dokumentierte Datenflüsse, sichere Fehlerbehandlung, ein operatives Runbook und – bei Drittanbietern – eine nachvollziehbare Lizenzprüfung.
