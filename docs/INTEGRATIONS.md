# Integrationen

## Google Maps Scraper Kit (optional)

Projekt: https://github.com/Mahanaicoach/google-maps-scraper-kit (laut am 25.10.2026 geprüftem Repository: MIT-Lizenz).

**Expliziter Hinweis:** Das Projekt selbst weist darauf hin, dass Google-Maps-Scraping gegen Googles Nutzungsbedingungen verstößt. VALDRIQ lädt es **nicht** automatisch herunter und startet auch nicht heimlich Browser-Scraping. Der Betreiber entscheidet, ob er es unter Einhaltung der einschlägigen Bedingungen betreibt.

### Anbindung

1. Scraper Kit separat gemäß seinem `README.md` und `SETUP.md` installieren.
2. Seine Engine mittels `docker compose up -d` im Scraper-Kit-Verzeichnis starten; lokal erreichbar halten.
3. Den **absoluten** lokalen Pfad zu seinem Ordner konfigurieren, z. B.:

   ```bash
   export VALDRIQ_SCRAPER_KIT_DIR='/opt/google-maps-scraper-kit'
   python3 -m valdriq
   ```

4. In VALDRIQ **Lead-Recherche → Google Maps Scraper Kit** wählen, Branche, Stadt, Trefferzahl und Raster angeben.
5. VALDRIQ startet die dokumentierte `scripts/scrape.py`-CLI als separaten Prozess, wartet begrenzt und importiert deren CSV-Ergebnis. Das externe CLI/Engine-Paket bleibt vollständig getrennt und unverändert.

Die VALDRIQ-Schnittstelle nutzt `--city`, `--depth 5`, `--out` und optional `--grid`; mit `--no-deep-emails` wird der zusätzliche Website-Durchlauf reduziert. Die CLI kann dennoch veröffentlichte E-Mail-Adressen ermitteln. Solche Adressen bekommen im CRM standardmäßig **keine Versandfreigabe**.

**Docker-Besonderheit:** Der Compose-Container enthält absichtlich keinen Docker-Socket. Das separate lokale Scraper Kit muss in diesem Fall für den VALDRIQ-Container erreichbar und dessen Pfad geeignet gemountet sein; die vorliegende Compose-Datei aktiviert das bewusst nicht. Am einfachsten: VALDRIQ direkt mit Python und den Kit-Dienst separat betreiben.

## Offizielle Google Places API (New)

- In einem Google-Cloud-Projekt die Places API (New) aktivieren und Abrechnung/Quota konfigurieren.
- `VALDRIQ_GOOGLE_PLACES_API_KEY` setzen.
- Der Connector ruft `places:searchText` auf und fordert Firmennamen, Adresse, Website, Telefonnummer, Kategorie und Place-ID ab.
- Pro Job werden bis zu 20 Ergebnisse abgefragt. Ein externer API-Schlüssel und eventuell kostenpflichtige API-Nutzung sind nötig.

**Nutzungs- und Speicherungsvorgaben prüfen:** Google Maps Platform reglementiert das Speichern, Zwischenspeichern und Wiederverwenden von Places-Inhalten. Für produktiven Betrieb sind diese Pflichten vor Aktivierung des Connectors zu klären. Ein eigener Datenanbieter mit passenden Exportrechten kann sinnvoller sein.

## OpenAI (optional)

- `VALDRIQ_OPENAI_API_KEY` setzen.
- Optional `VALDRIQ_OPENAI_MODEL` ändern (Standard: `gpt-4.1-mini`).
- Nur Projektdetails und ein begrenztes Set an Lead-Feldern wird für die Entwurfserstellung übermittelt.
- Ohne Schlüssel oder bei Fehler wird eine deterministische Vorlage erzeugt. Keine automatisierte Versendung.
- Bitte Datenverarbeitung, Rechtsgrundlage und vertragliche Bedingungen des KI-Dienstes für die konkret verwendeten Lead-Daten prüfen.

## SMTP (optional)

```dotenv
VALDRIQ_SMTP_HOST=smtp.example.de
VALDRIQ_SMTP_PORT=587
VALDRIQ_SMTP_USER=user
VALDRIQ_SMTP_PASSWORD=secret
VALDRIQ_SMTP_FROM=vertrieb@example.de
VALDRIQ_SMTP_STARTTLS=true
```

Port 587 nutzt STARTTLS, Port 465 SSL/TLS. Der Sender wird serverseitig konfiguriert. Auf keinen Fall API-Keys oder Mail-Passwörter ins Repository committen.

## CSV als universelle Schnittstelle

Header wie `title,phone,emails,website,category,address` aus Scraper Kit werden direkt erkannt, ebenso `business,email,industry,contact_name,notes,evidence`. Weitere Drittanbieter wie Apollo-/CRM-Exporte können per Spaltenmapping vorbereitet werden.
