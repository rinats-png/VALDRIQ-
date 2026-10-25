"""Input validation, progressive discovery and deterministic scoring."""
import csv
import io
import json
import re
from datetime import date
from urllib.parse import urlparse

PROJECT_FIELDS = (
    "name", "offer", "target_industries", "target_customer", "geography", "customer_problem",
    "differentiator", "price_model", "lead_source", "contact_strategy", "tone",
    "sender_name", "sender_company", "sender_email", "sender_address", "sender_site"
)
LEAD_FIELDS = (
    "business", "contact_name", "email", "phone", "website", "industry", "address",
    "notes", "evidence", "permission", "permission_evidence", "permission_date", "status"
)
STATUSES = {"new", "qualified", "contacted", "replied", "won", "lost"}
PERMISSIONS = {"none", "consent", "existing_customer"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

QUESTIONS = [
    ("name", "Wie heißt dein Vertriebsprojekt?", "z. B. EIRA – B2B Vertrieb"),
    ("offer", "Was verkaufst du? Beschreibe das Angebot konkret.", "Produkt, Nutzen, Funktionsumfang"),
    ("target_industries", "Welche Branchen sollen wir suchen?", "z. B. Zahnarztpraxen, SHK, Hausverwaltung"),
    ("target_customer", "Wer entscheidet über den Kauf?", "z. B. Praxisinhaber, Geschäftsführer"),
    ("geography", "Wo befinden sich deine Wunschkunden?", "Stadt, Region oder Bundesland"),
    ("customer_problem", "Welches messbare Problem löst dein Angebot?", "z. B. verpasste Anrufe außerhalb der Öffnungszeit"),
    ("differentiator", "Warum sollen Kunden gerade dich wählen?", "Ein glaubwürdiger Vorteil gegenüber Alternativen"),
    ("price_model", "Wie sieht das Preismodell aus?", "z. B. 99 € / Monat; 'noch offen' möglich"),
    ("lead_source", "Woher sollen Leads stammen?", "google_places, scraper_kit, csv, manual"),
    ("contact_strategy", "Wie ist die rechtmäßige Erstansprache geplant?", "z. B. Kontaktformular auf Anfrage, Opt-in-E-Mail, Post"),
    ("tone", "Wie soll die Ansprache klingen?", "z. B. prägnant, sachlich, Sie-Form"),
    ("sender_name", "Wer ist der Absender?", "Vor- und Nachname"),
    ("sender_company", "Zu welchem Unternehmen gehört der Absender?", "Firmenname"),
    ("sender_email", "Welche Absender-E-Mail verwendest du?", "firma@example.de"),
    ("sender_address", "Welche Geschäftsanschrift gehört in die Signatur?", "Straße, PLZ, Stadt"),
    ("sender_site", "Welche Website kannst du verlinken?", "https://example.de oder 'keine'"),
]


def require_string(value, field, limit=2000, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError(f"{field} muss Text sein.")
    value = value.strip()
    if not allow_empty and not value:
        raise ValueError(f"{field} darf nicht leer sein.")
    if len(value) > limit:
        raise ValueError(f"{field} darf höchstens {limit} Zeichen enthalten.")
    return value


def clean_project(data):
    if not isinstance(data, dict):
        raise ValueError("Projekt muss ein Objekt sein.")
    output = {k: require_string(v, k, 4000 if k in {"offer", "customer_problem"} else 600, True)
              for k, v in data.items() if k in PROJECT_FIELDS}
    if "sender_email" in output and output["sender_email"] and not EMAIL_RE.fullmatch(output["sender_email"]):
        raise ValueError("Absender-E-Mail ist ungültig.")
    return output


def interview(project):
    missing = [{"field": field, "question": question, "hint": hint}
               for field, question, hint in QUESTIONS if not str(project.get(field, "")).strip()]
    total = len(QUESTIONS)
    return {"complete": not missing, "answered": total - len(missing), "total": total,
            "percent": round(100 * (total - len(missing)) / total), "next": missing[0] if missing else None,
            "missing": missing,
            "recommendations": recommendations(project)}


def recommendations(project):
    tips = []
    if project.get("lead_source") == "scraper_kit":
        tips.append("Scraper Kit erfordert externe Installation und kann gegen Plattformbedingungen verstoßen.")
    if "email" in project.get("contact_strategy", "").lower():
        tips.append("Für Werbe-E-Mails in Deutschland eine dokumentierte Einwilligung oder eng begrenzte Bestandskundenausnahme prüfen.")
    if not project.get("differentiator"):
        tips.append("Ein belegbarer Unterschied erhöht die Qualität personalisierter Nachrichten.")
    return tips


def normalize_lead(data):
    aliases = {"title": "business", "name": "business", "company": "business", "emails": "email",
               "category": "industry", "rating": "notes", "source_url": "evidence"}
    result = {}
    for key, val in data.items():
        if not isinstance(key, str):
            continue
        field = aliases.get(key.strip().lower(), key.strip().lower())
        if field in LEAD_FIELDS and field not in result:
            if val is None:
                val = ""
            result[field] = require_string(str(val), field, 4000 if field in {"notes", "evidence"} else 600, True)
    result["business"] = require_string(result.get("business", ""), "business", 600)
    if "," in result.get("email", ""):
        result["email"] = result["email"].split(",", 1)[0].strip()
    if result.get("email") and not EMAIL_RE.fullmatch(result["email"]):
        result["email"] = ""
    result["permission"] = result.get("permission") or "none"
    if result["permission"] not in PERMISSIONS:
        raise ValueError("Ungültige Kontaktgrundlage.")
    result["status"] = result.get("status") or "new"
    if result["status"] not in STATUSES:
        raise ValueError("Ungültiger Leadstatus.")
    if result.get("permission_date"):
        try:
            given_date = date.fromisoformat(result["permission_date"])
        except ValueError as exc:
            raise ValueError("Datum der Kontaktgrundlage muss im ISO-Format YYYY-MM-DD vorliegen.") from exc
        if given_date > date.today():
            raise ValueError("Datum der Kontaktgrundlage darf nicht in der Zukunft liegen.")
    return result


def parse_csv(raw):
    if len(raw) > 2_000_000:
        raise ValueError("CSV ist zu groß (max. 2 MB).")
    result = []
    for i, record in enumerate(csv.DictReader(io.StringIO(raw.lstrip("\ufeff")))):
        if i >= 1000:
            raise ValueError("Pro Import maximal 1000 Leads.")
        if not any(str(v or "").strip() for v in record.values()):
            continue
        result.append(normalize_lead(record))
    return result


def score_lead(project, lead):
    """Transparent relevance estimate; no ungrounded 'AI certainty'."""
    score, reasons = 15, []
    industries = [x.strip().casefold() for x in re.split("[,;\n]", project.get("target_industries", "")) if x.strip()]
    searchable = " ".join(str(lead.get(k, "")) for k in ("industry", "business", "notes")).casefold()
    if industries and any(x in searchable for x in industries):
        score += 35
        reasons.append("Branchenübereinstimmung")
    location = project.get("geography", "").casefold()
    locations = [x.strip() for x in re.split("[,;\n]", location) if len(x.strip()) > 2]
    if locations and any(x in str(lead.get("address", "")).casefold() for x in locations):
        score += 20
        reasons.append("Standortübereinstimmung")
    if lead.get("website"):
        score += 10
        reasons.append("Website vorhanden")
    if lead.get("email") or lead.get("phone"):
        score += 10
        reasons.append("Kontaktkanal gefunden")
    if lead.get("evidence"):
        score += 10
        reasons.append("Quellenhinweis hinterlegt")
    return {"score": min(score, 100), "reasons": reasons}


TEMPLATE_KINDS = {"intro", "value", "demo", "followup"}


def draft_message(project, lead, kind="intro"):
    if not interview(project)["complete"]:
        raise ValueError("Bitte zuerst alle Fragen im Strategie-Assistenten beantworten.")
    if kind not in TEMPLATE_KINDS:
        raise ValueError("Unbekannte E-Mail-Vorlage.")
    offer = project["offer"].split(".")[0][:200]
    problem = project["customer_problem"].split(".")[0][:200]
    name = lead.get("contact_name") or "Damen und Herren"
    salutation = f"Guten Tag {name}," if name != "Damen und Herren" else "Guten Tag,"
    openings = {
        "intro": f"ich beschäftige mich mit Lösungen für {problem}. Unser Angebot: {offer}.\n\n"
                 f"Ich würde gern herausfinden, ob dieses Thema für {lead['business']} relevant ist. "
                 "Falls Sie konkrete Anforderungen haben, freue ich mich über eine Rückmeldung.",
        "value": f"in Unternehmen Ihrer Branche kann das Thema {problem} relevant sein. "
                 f"Wir bieten {offer} an. Unser Ansatz: {project['differentiator']}.\n\n"
                 "Mich würde interessieren, ob eine kurze Übersicht dazu für Sie sinnvoll wäre.",
        "demo": f"ich möchte Ihnen {offer} kurz vorstellen. "
                f"Das Angebot beschäftigt sich mit {problem}.\n\n"
                "Falls das für Sie interessant ist, könnten wir einen unverbindlichen Gesprächstermin vereinbaren.",
        "followup": f"ich wollte zu meiner vorherigen Nachricht über {offer} kurz nachfragen.\n\n"
                    "Wenn das Thema derzeit nicht relevant ist, genügt eine kurze Rückmeldung."
    }
    body = (f"{salutation}\n\n" + openings[kind] + "\n\n"
            f"Mit freundlichen Grüßen\n{project['sender_name']}\n{project['sender_company']}\n"
            f"{project['sender_address']}\n{project['sender_email']}\n{project['sender_site']}\n\n"
            "Falls Sie keine weiteren Nachrichten wünschen, genügt eine kurze Mitteilung.")
    subjects = {"intro": f"Kurze Anfrage an {lead['business']}",
                "value": f"Möglicher Ansatz für {lead['business']}",
                "demo": "Unverbindliche Kurzvorstellung", "followup": "Kurze Rückfrage zu meiner Nachricht"}
    return {"subject": subjects[kind], "body": body,
            "disclaimer": "Entwurf: Keine nachgewiesene Problemlage des Unternehmens behauptet. Versand erst bei gültiger Kontaktgrundlage."}


def can_send(lead, email_suppressed=False):
    if not lead.get("email") or not EMAIL_RE.fullmatch(lead["email"]):
        return False, "Keine gültige E-Mail-Adresse."
    if email_suppressed:
        return False, "E-Mail-Adresse steht auf der Sperrliste."
    if lead.get("permission") not in ("consent", "existing_customer"):
        return False, "Keine dokumentierte zulässige Kontaktgrundlage."
    if not lead.get("permission_evidence") or not lead.get("permission_date"):
        return False, "Beleg und Datum zur Kontaktgrundlage fehlen."
    return True, ""
