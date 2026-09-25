"""Offline contract tests for Website Care; no checkout or external calls."""
from html import unescape
import json
import re
import unittest
from urllib.parse import parse_qs, urlsplit
from test_security_site import ROOT, Page
from test_monthly_care import CARE_ROUTES, visible
import xml.etree.ElementTree as ET

WEBSITE_ROUTE = "website-care/index.html"
WEBSITE_SUBJECT = "Website Care $600 plan"
WEBSITE_MAILTO = "mailto:harley@kyber-llc.com?subject=Website%20Care%20%24600%20plan"
COMBINED_SUBJECT = "Website and Office Care fit and scope"


class WebsiteSubscriptionTests(unittest.TestCase):
    def test_landing_explains_design_development_and_a_real_inquiry_path(self):
        path = ROOT / WEBSITE_ROUTE
        self.assertTrue(path.is_file(), "Website Care needs its own working landing page")
        page = Page(path)
        text = visible(page.source).lower()
        self.assertIn('<p class="lead"><strong>$600/month.</strong>', page.source,
                      "The landing price must be prominent, not only in a small eyebrow")
        for phrase in ["kyber website care", "$600/month", "design and development",
                       "new website", "refresh an existing website", "one agreed-scope",
                       "business marketing website", "while subscribed", "text", "photo",
                       "service", "layout", "page", "routine upkeep", "client permission",
                       "scope, timing, and subscription terms", "before work begins"]:
            self.assertIn(phrase, text)
        for heading in ["Request", "Preview", "Approval", "Publish"]:
            self.assertRegex(page.source, rf"<h3>{heading}</h3>")
        links = [a.get("href", "") for a in page.attrs("a")]
        self.assertIn(WEBSITE_MAILTO, links)
        self.assertIn("mailto:harley@kyber-llc.com", links)
        cta = urlsplit(WEBSITE_MAILTO)
        self.assertEqual(cta.path, "harley@kyber-llc.com")
        self.assertEqual(parse_qs(cta.query), {"subject": [WEBSITE_SUBJECT]})
        self.assertIn('href="https://kyber-llc.com/website-care/"', page.source)
        self.assertIn('class="faq"', page.source)
        self.assertGreaterEqual(len(page.attrs("summary")), 4)

    def test_all_entry_pages_lead_to_website_care_without_a_physical_work_gate(self):
        for rel in CARE_ROUTES:
            with self.subTest(route=rel):
                source = (ROOT / rel).read_text()
                hero = re.search(r'<section class="(?:page-hero|hero)">(.*?)</section>', source, re.S)
                self.assertIsNotNone(hero)
                assert hero is not None
                primary = hero.group(1).split('<aside', 1)[0]
                text = visible(primary).lower()
                for phrase in ["website care", "$600/month", "design", "development"]:
                    self.assertIn(phrase, text)
                self.assertNotRegex(text, r"not available for scheduling|proposed|service preview|\$1,600")
                self.assertIn('href="/website-care/"', primary)
                self.assertIn(WEBSITE_MAILTO, primary)
        for rel in ["index.html", "pricing/index.html", "contact/index.html"]:
            source = (ROOT / rel).read_text()
            subjects = [parse_qs(urlsplit(a["href"]).query).get("subject", [])
                        for a in Page(ROOT / rel).attrs("a")
                        if a.get("href", "").startswith("mailto:")]
            self.assertIn([WEBSITE_SUBJECT], subjects)
            self.assertIn([COMBINED_SUBJECT], subjects)
            self.assertLess(source.index("$600/month"), source.index("$1,600/month"))

    def test_landing_metadata_and_sitemap_are_canonical(self):
        page = Page(ROOT / WEBSITE_ROUTE)
        metadata = {m.get("name") or m.get("property"): m.get("content") for m in page.attrs("meta")}
        self.assertEqual(metadata["description"], metadata["og:description"])
        title = re.search(r"<title>(.*?)</title>", page.source)
        assert title is not None
        self.assertEqual(metadata["og:title"], unescape(title.group(1)))
        self.assertEqual([a["href"] for a in page.attrs("link") if a.get("rel") == "canonical"],
                         ["https://kyber-llc.com/website-care/"])
        self.assertEqual(metadata["og:url"], "https://kyber-llc.com/website-care/")
        self.assertIn("$600/month", metadata["description"])
        self.assertIn("design and development", metadata["description"])
        self.assertNotIn("noindex", metadata.get("robots", ""))
        baseline = json.loads((ROOT / "tests/monthly_care_preservation.json").read_text())
        policies = [m["content"] for m in page.attrs("meta")
                    if m.get("http-equiv") == "Content-Security-Policy"]
        self.assertEqual(policies, [baseline["csp"]])
        self.assertNotIn("style=", page.source)
        self.assertFalse(page.attrs("style"))
        self.assertFalse(page.attrs("script"))
        self.assertEqual([a["href"] for a in page.attrs("link") if a.get("rel") == "stylesheet"],
                         ["/assets/security-services.css?v=4"])
        locations = [el.text for el in ET.parse(ROOT / "sitemap.xml").findall(".//{*}loc")]
        self.assertEqual(locations.count("https://kyber-llc.com/website-care/"), 1)

    def test_referrals_never_leak_into_the_website_only_offer(self):
        for rel in CARE_ROUTES + [WEBSITE_ROUTE]:
            with self.subTest(route=rel):
                source = (ROOT / rel).read_text()
                details = re.findall(r'<details\b[^>]*id="referrals"[^>]*>(.*?)</details>', source, re.S)
                for terms in details:
                    text = visible(terms).lower()
                    self.assertIn("website & office care only", text)
                    self.assertIn("not the website-only subscription", text)
                    self.assertNotIn("$600", text)
                unscoped = re.sub(r'<aside\b[^>]*id="combined-plan"[^>]*>.*?</aside>', "", source, flags=re.S)
                unscoped = re.sub(r'<details\b[^>]*id="referrals"[^>]*>.*?</details>', "", unscoped, flags=re.S)
                self.assertNotIn("15%", visible(unscoped))
                footer = re.search(r'<nav aria-label="Footer navigation">(.*?)</nav>', source, re.S)
                assert footer is not None
                self.assertIn("Combined-plan referral terms", visible(footer.group(1)))
        landing = (ROOT / WEBSITE_ROUTE).read_text()
        primary = landing.split('<section class="section" id="separate-plan">', 1)[0]
        self.assertNotIn("15%", primary)
        self.assertNotIn("$1,600", primary)

    def test_website_scope_excludes_unapproved_work_and_terms(self):
        text = visible((ROOT / WEBSITE_ROUTE).read_text()).lower()
        for phrase in ["not unlimited builds", "complex applications", "ecommerce",
                       "integrations", "separately scoped", "office visits", "wi-fi",
                       "physical-security", "penetration testing", "not included",
                       "client approval before publication", "no public checkout"]:
            self.assertIn(phrase, text)
        for rel in CARE_ROUTES + [WEBSITE_ROUTE]:
            source = (ROOT / rel).read_text()
            # The preserved combined referral continuity terms are not website
            # subscription cancellation terms. Do not strip any other copy.
            source = re.sub(r'<details\b[^>]*id="referrals"[^>]*>.*?</details>', "", source, flags=re.S)
            text = visible(source).lower()
            for pattern in [r"cancel any\s*time", r"no (?:minimum term|contract|setup fee)",
                            r"no-setup-fee", r"free (?:setup|hosting|domain)",
                            r"\b(?:12|six|6|twelve)[ -]month (?:minimum|commitment|term)",
                            r"you own (?:the|your) (?:site|website|code)",
                            r"(?:24|48|72)[ -]hour (?:turnaround|delivery)",
                            r"unlimited (?:website )?(?:builds|revisions|changes) included",
                            r"guaranteed (?:leads|rankings|security|seo)", r"subscribe now|pay now",
                            r"leadconnector|gohighlevel|retell|buy\.stripe|checkout\.stripe"]:
                self.assertNotRegex(text, pattern, rel)


if __name__ == "__main__":
    unittest.main()
