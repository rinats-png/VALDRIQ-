import unittest

from valdriq.domain import can_send, clean_project, draft_message, interview, normalize_lead, parse_csv, score_lead


def sample_project():
    return dict(name="EIRA", offer="Telefonassistent mit Kalenderanbindung.", target_industries="Zahnarztpraxis, SHK",
                target_customer="Praxisinhaber", geography="Frankfurt", customer_problem="verpasste Telefonanrufe",
                differentiator="24/7 Erreichbarkeit", price_model="100€/Monat", lead_source="google_places",
                contact_strategy="E-Mail mit Einwilligung", tone="sachlich", sender_name="Alex Meyer",
                sender_company="EIRA GmbH", sender_email="alex@example.de", sender_address="Teststraße 1, Frankfurt",
                sender_site="https://example.de")


class DomainTests(unittest.TestCase):
    def test_interview_asks_only_missing_fields(self):
        result = interview({"name": "EIRA", "offer": "Assistent"})
        self.assertEqual(result["answered"], 2)
        self.assertEqual(result["next"]["field"], "target_industries")
        self.assertFalse(result["complete"])
        self.assertTrue(interview(sample_project())["complete"])

    def test_lead_normalization(self):
        lead = normalize_lead({"title": "Praxis A", "emails": "info@praxis.de, mail@praxis.de", "category": "Zahnarztpraxis"})
        self.assertEqual(lead["business"], "Praxis A")
        self.assertEqual(lead["email"], "info@praxis.de")
        self.assertEqual(lead["permission"], "none")

    def test_scoring_is_transparent(self):
        score = score_lead(sample_project(), {"business": "Praxis A", "industry": "Zahnarztpraxis",
                     "address": "Frankfurt", "website": "https://praxis.de", "email": "", "phone": "", "evidence": ""})
        self.assertEqual(score["score"], 80)
        self.assertIn("Branchenübereinstimmung", score["reasons"])

    def test_csv_limits(self):
        leads = parse_csv("title,emails,category\nPraxis A,info@example.de,Zahnarztpraxis\n")
        self.assertEqual(len(leads), 1)
        self.assertRaises(ValueError, parse_csv, "company\n" + "\n".join("A" for _ in range(1001)))

    def test_permission_is_required(self):
        lead = {"email": "info@example.de", "permission": "none", "permission_evidence": "", "permission_date": ""}
        self.assertFalse(can_send(lead)[0])
        lead.update(permission="consent", permission_evidence="Opt-in Log #42", permission_date="2026-10-25")
        self.assertTrue(can_send(lead)[0])
        self.assertFalse(can_send(lead, True)[0])

    def test_draft_avoids_unfounded_claim(self):
        draft = draft_message(sample_project(), {"business": "Praxis Muster", "contact_name": "", "email": "info@example.de"})
        self.assertIn("Praxis Muster", draft["body"])
        self.assertNotIn("Sie verpassen", draft["body"])


if __name__ == "__main__":
    unittest.main()
