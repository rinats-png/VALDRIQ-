"""Pluggable lead discovery. External projects are never bundled or executed implicitly."""
import csv
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .domain import normalize_lead


class ConnectorError(RuntimeError):
    pass


def google_places_search(query, city, limit=20):
    """Google Places API (New), documented field mask; API billing and terms apply."""
    key = os.getenv("VALDRIQ_GOOGLE_PLACES_API_KEY", "")
    if not key:
        raise ConnectorError("VALDRIQ_GOOGLE_PLACES_API_KEY ist nicht konfiguriert.")
    limit = max(1, min(int(limit), 20))
    data = json.dumps({"textQuery": f"{query} in {city}", "languageCode": "de", "pageSize": limit}).encode()
    request = Request("https://places.googleapis.com/v1/places:searchText", data=data, method="POST",
                      headers={"Content-Type": "application/json", "X-Goog-Api-Key": key,
                               "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.websiteUri,places.nationalPhoneNumber,places.primaryTypeDisplayName"})
    try:
        with urlopen(request, timeout=25) as response:
            payload = json.load(response)
    except HTTPError as exc:
        raise ConnectorError(f"Places API HTTP {exc.code}. API-Key, Billing und Berechtigungen prüfen.") from exc
    except (URLError, TimeoutError) as exc:
        raise ConnectorError("Places API ist momentan nicht erreichbar.") from exc
    output = []
    for place in payload.get("places", []):
        name = place.get("displayName", {}).get("text", "")
        if not name:
            continue
        output.append((normalize_lead({"business": name, "address": place.get("formattedAddress", ""),
                                       "website": place.get("websiteUri", ""),
                                       "phone": place.get("nationalPhoneNumber", ""),
                                       "industry": place.get("primaryTypeDisplayName", {}).get("text", ""),
                                       "evidence": "Google Places API; Angaben vor Ansprache überprüfen"}),
                       place.get("id", "")))
    return output


def scraper_kit_search(query, city, limit=100, grid=1):
    """Run a separately installed MIT-licensed kit via its documented Python CLI.

    Only enabled by a local administrator via VALDRIQ_SCRAPER_KIT_DIR.
    External command args are passed as an array (never via a shell).
    """
    root_value = os.getenv("VALDRIQ_SCRAPER_KIT_DIR", "").strip()
    if not root_value:
        raise ConnectorError("Scraper Kit nicht konfiguriert. Siehe docs/INTEGRATIONS.md.")
    root = Path(root_value).resolve()
    cli = root / "scripts" / "scrape.py"
    if not cli.is_file():
        raise ConnectorError("Scraper Kit CLI nicht gefunden. VALDRIQ_SCRAPER_KIT_DIR prüfen.")
    if not 1 <= grid <= 3:
        raise ConnectorError("Grid muss zwischen 1 und 3 liegen.")
    with tempfile.TemporaryDirectory(prefix="valdriq-scrape-") as folder:
        output = Path(folder) / "leads.csv"
        command = [sys.executable, str(cli), query, "--city", city, "--depth", "5",
                   "--out", str(output), "--no-deep-emails"]
        if grid > 1:
            command += ["--grid", str(grid)]
        try:
            result = subprocess.run(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, timeout=720, check=False)
        except subprocess.TimeoutExpired as exc:
            raise ConnectorError("Scraper-Lauf hat das Zeitlimit überschritten.") from exc
        if result.returncode != 0 or not output.is_file():
            raise ConnectorError("Scraper fehlgeschlagen. Läuft sein Docker-Engine-Dienst? Logs lokal prüfen.")
        with output.open("r", encoding="utf-8-sig", newline="") as handle:
            records = list(csv.DictReader(io.StringIO(handle.read(2_000_000))))
        return [(normalize_lead(record), "") for record in records[:max(1, min(limit, 200))]]


def search(provider, query, city, limit=20, grid=1):
    if provider == "google_places":
        return google_places_search(query, city, limit)
    if provider == "scraper_kit":
        return scraper_kit_search(query, city, limit, grid)
    raise ConnectorError("Unbekannter Rechercheanbieter.")
