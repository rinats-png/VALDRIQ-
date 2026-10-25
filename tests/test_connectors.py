import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from valdriq import connectors


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class ConnectorTests(unittest.TestCase):
    def test_google_places_maps_fields_and_requires_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(connectors.ConnectorError):
                connectors.google_places_search('Zahnarzt', 'Frankfurt')
        payload = {'places': [{'id': 'place-1', 'displayName': {'text': 'Praxis A'},
                   'formattedAddress': 'Frankfurt', 'nationalPhoneNumber': '069 123',
                   'websiteUri': 'https://praxis.example', 'primaryTypeDisplayName': {'text': 'Zahnarzt'}}]}
        with patch.dict(os.environ, {'VALDRIQ_GOOGLE_PLACES_API_KEY': 'example-key'}):
            with patch('valdriq.connectors.urlopen', return_value=FakeResponse(json.dumps(payload).encode())) as mocked:
                data = connectors.google_places_search('Zahnarzt', 'Frankfurt')
        self.assertEqual(data[0][0]['business'], 'Praxis A')
        self.assertEqual(data[0][1], 'place-1')
        self.assertEqual(mocked.call_args.args[0].full_url, 'https://places.googleapis.com/v1/places:searchText')

    def test_scraper_kit_cli_adapter_parses_csv_without_shell(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'scripts').mkdir()
            (root / 'scripts' / 'scrape.py').touch()

            def fake_run(command, **kwargs):
                self.assertNotIn('shell', kwargs)
                target = Path(command[command.index('--out') + 1])
                target.write_text('title,phone,emails,website,category,address\nPraxis A,069,info@praxis.de,praxis.de,Zahnarzt,Frankfurt\n')
                return type('Result', (), {'returncode': 0})()

            with patch.dict(os.environ, {'VALDRIQ_SCRAPER_KIT_DIR': folder}):
                with patch('valdriq.connectors.subprocess.run', side_effect=fake_run):
                    records = connectors.scraper_kit_search('Zahnarzt', 'Frankfurt')
            self.assertEqual(records[0][0]['business'], 'Praxis A')
            self.assertEqual(records[0][0]['email'], 'info@praxis.de')
            self.assertEqual(records[0][0]['permission'], 'none')


if __name__ == '__main__':
    unittest.main()
