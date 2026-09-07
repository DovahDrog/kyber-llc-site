"""Public threat-statistic provenance and motion/no-script regressions."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from html import unescape
from pathlib import Path
import json
import re
import unittest
from urllib.parse import urlsplit
from test_security_site import ROOT, PUBLIC_PAGES, Page

class ThreatAndMotionTests(unittest.TestCase):
    def setUp(self):
        self.home = Page(ROOT / 'index.html')
        self.css = (ROOT / 'assets/security-services.css').read_text()
        self.data = json.loads((ROOT / 'assets/threat-statistics.json').read_text())

    def test_source_ledger_is_complete_unique_and_public_safe(self):
        stats = self.data['statistics']
        self.assertGreaterEqual(len(stats), 2)
        self.assertEqual(len(stats), len({s['id'] for s in stats}))
        for row in stats:
            for field in ['id','display_value','unit','scope','source_url','source_title','source_id','period','evidence_quote','interpretation','daily_method']:
                self.assertTrue(row.get(field), (row.get('id'),field))
            self.assertEqual(urlsplit(row['source_url']).scheme,'https')
            self.assertIn(urlsplit(row['source_url']).hostname, self.data['approved_source_hosts'])
        text=json.dumps(self.data)
        self.assertNotRegex(text, r'/Users/|192\.168\.|access_token|secret_key|Bearer ')
        self.assertLessEqual(date.fromisoformat(self.data['verified_on']),date.today())

    def test_daily_arithmetic_and_rounding_are_reproducible(self):
        for row in self.data['statistics']:
            if row['daily_method']=='published_daily':
                self.assertEqual(row['period_days'],1)
            elif row['daily_method']=='weekly_average':
                self.assertEqual(row['period_days'],7)
                self.assertIn('average',row['interpretation'].lower())
                self.assertIn('per organization',row['scope'].lower())
            elif row['daily_method']=='period_average':
                start=date.fromisoformat(row['period_start'])
                end=date.fromisoformat(row['period_end'])
                self.assertEqual((end-start).days+1,row['period_days'])
                self.assertIn('average',row['interpretation'].lower())
            else:
                self.fail('Unknown daily method')
            calculated=Decimal(str(row['period_value'])) / Decimal(row['period_days'])
            self.assertLess(abs(calculated-Decimal(str(row['daily_value']))), Decimal('0.0001'))
            rounded=int(calculated.quantize(Decimal('1'),rounding=ROUND_HALF_UP))
            self.assertEqual(rounded,row['rounded_daily_value'])
            self.assertEqual(row['display_value'],f'≈{rounded:,}')

    def test_every_stat_has_exact_visible_value_and_source(self):
        for row in self.data['statistics']:
            card=re.search(r'<article[^>]*\bid="'+re.escape(row['id'])+r'"[^>]*>(.*?)</article>',self.home.source,re.S)
            self.assertIsNotNone(card,row['id'])
            body=unescape(re.sub('<[^>]+>',' ',card.group(1)))
            body=re.sub(r'\s+',' ',body)
            number=re.search(r'<p class="stat-value">([^<]+)<small>([^<]+)</small></p>',card.group(1))
            assert number is not None, row['id']
            self.assertEqual(unescape(number.group(1)).strip(),row['display_value'])
            self.assertEqual(number.group(2),'Calculated daily average · '+row['period'])
            self.assertIn(row['display_value'],body)
            self.assertIn(row['unit'],body)
            self.assertIn(row['scope'],body)
            self.assertIn(row['source_url'],card.group(1))
            self.assertIn('['+str(row['source_id'])+']',card.group(1))
        self.assertNotIn('VERIFIED_THREAT_STATS',self.home.source)
        self.assertNotRegex(self.home.text.lower(),r'attacks since you arrived|attacks happening now|live threat count|worldwide total')

    def test_methodology_distinguishes_phishing_and_denominators(self):
        text=self.home.text.lower()
        for phrase in ['not a live counter','not successful breaches','phishing','social engineering','not added together']:
            self.assertIn(phrase,text)
        self.assertRegex(self.home.source,r'<details[^>]*id="threat-sources"')
        self.assertIn('2026-09-07',self.home.source)

    def test_shared_styles_are_versioned_on_every_public_page(self):
        for rel in PUBLIC_PAGES:
            self.assertIn('/assets/security-services.css?v=3',(ROOT/rel).read_text())

    def test_exaggerated_display_and_missing_period_are_rejected(self):
        self.data['statistics'][0]['display_value']='≈999,999'
        self.home.source=self.home.source.replace('≈334','≈999,999')
        with self.assertRaises(AssertionError):
            self.test_daily_arithmetic_and_rounding_are_reproducible()
        self.setUp()
        self.home.source=self.home.source.replace('Calculated daily average · July 2026','Live data · Today')
        with self.assertRaises(AssertionError):
            self.test_every_stat_has_exact_visible_value_and_source()

    def test_brand_accessible_name_favicon_and_print_fallback(self):
        for rel in PUBLIC_PAGES:
            source=(ROOT/rel).read_text()
            self.assertNotIn('aria-label="Kyber home"',source)
            self.assertIn('<link rel="icon" href="/assets/kyber-mark.svg"',source)
        self.assertTrue((ROOT/'assets/kyber-mark.svg').is_file())
        print_css=self.css[self.css.index('@media print'): ]
        for selector in ['.hero .lead','.page-hero .lead','.page-hero p:not(.eyebrow)']:
            self.assertIn(selector,print_css)

    def test_motion_has_static_no_script_and_reduced_fallbacks(self):
        self.assertGreaterEqual(self.css.count('@keyframes'),2)
        self.assertIn('prefers-reduced-motion: reduce',self.css)
        self.assertRegex(self.css,r'animation(?:-name)?:\s*none\s*!important')
        self.assertNotIn('infinite',re.sub(r'/\*.*?\*/','',self.css,flags=re.S))
        self.assertNotRegex(self.home.source,r'<script\b(?![^>]*type="application/ld\+json")')
        self.assertNotIn('unsafe-inline',self.home.source)
        self.assertNotIn('unsafe-eval',self.home.source)
        self.assertNotRegex(self.css,r'@import|https?://')

if __name__=='__main__':
    unittest.main()
