"""Offline regression checks for the service-first public website.

Run: python3 -m unittest discover -s tests -v
No requests to production, form submissions, or third-party services.
"""
from html.parser import HTMLParser
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import unittest
from urllib.parse import unquote, urljoin, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PAGES = ["index.html", "services/index.html", "about/index.html", "contact/index.html",
                "pricing/index.html", "products/index.html", "systems/index.html",
                "platform/index.html", "legacy/index.html", "privacy.html", "terms.html"]


def public_route(relative):
    return "/" + relative.removesuffix("index.html") if relative.endswith("index.html") else "/" + relative


def local_target(url):
    relative = unquote(urlsplit(url).path).lstrip("/")
    path = ROOT / relative
    return path / "index.html" if path.is_dir() else path


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.source = path.read_text(encoding="utf-8")
        self.tags = []
        self.words = []
        self.feed(self.source)
        self.text = re.sub(r"\s+", " ", " ".join(self.words))

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.words.append(data)

    def attrs(self, tag):
        return [attrs for name, attrs in self.tags if name == tag]


class SecuritySiteTests(unittest.TestCase):
    def test_homepage_sells_scoped_security_services(self):
        page = Page(ROOT / "index.html")
        for phrase in [
            "Security testing", "Digital", "Physical", "Combined",
            "written authorization", "rules of engagement", "stop conditions",
            "capability review", "remediation", "retest", "quote",
            "American organizations", "Majority disabled veteran-owned",
        ]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase.lower(), page.text.lower())
        self.assertIn("mailto:harley@kyber-llc.com", page.source)
        self.assertNotRegex(page.source.lower(), r"saas|portal login|codeflow-first|review queue preview")
        self.assertEqual(len(page.attrs("h1")), 1)

    def test_public_navigation_is_service_first_with_safe_metadata(self):
        for relative in PUBLIC_PAGES:
            with self.subTest(page=relative):
                path = ROOT / relative
                self.assertTrue(path.exists(), f"Missing public route: {relative}")
                page = Page(path)
                primary = re.search(r'<nav aria-label="Primary navigation">(.*?)</nav>', page.source, re.S)
                self.assertIsNotNone(primary, f"Missing service navigation: {relative}")
                assert primary is not None
                for route in ["/services/", "/#approach", "/about/", "/pricing/", "/contact/"]:
                    self.assertIn(f'href="{route}"', primary.group(1))
                self.assertNotIn("codeflow", primary.group(1).lower())
                self.assertNotRegex(page.source.lower(), r"codeflow-first|location.replace|http-equiv=\"refresh\"")
                metas = page.attrs("meta")
                policies = [m.get("content", "") for m in metas if m.get("http-equiv", "").lower() == "content-security-policy"]
                self.assertEqual(len(policies), 1)
                for directive in ["default-src 'none'", "script-src 'none'", "connect-src 'none'", "base-uri 'none'", "form-action 'none'"]:
                    self.assertIn(directive, policies[0])
                self.assertNotIn("frame-ancestors", policies[0])
                self.assertIn({"name": "referrer", "content": "no-referrer"}, metas)
                self.assertFalse(page.attrs("form"), f"No inquiry form may submit to an old backend: {relative}")
                self.assertNotRegex(page.source.lower(), r"leadconnector|gohighlevel|widgets\.|buy\.stripe|checkout\.stripe")
                if relative not in ["privacy.html", "terms.html"]:
                    self.assertNotIn("tel:", page.source.lower())
                self.assertTrue(all(s.get("type") == "application/ld+json" for s in page.attrs("script")))

    def test_discovery_points_to_services_and_preserves_existing_urls(self):
        sitemap = ET.parse(ROOT / "sitemap.xml")
        locations = [el.text for el in sitemap.findall(".//{*}loc")]
        self.assertEqual(len(locations), len(set(locations)), "Duplicate sitemap entries")
        for route in ["/", "/services/", "/about/", "/contact/", "/pricing/", "/products/",
                      "/privacy.html", "/terms.html", "/codeflow/", "/codeflow/proposal/",
                      "/codeflow/intake/", "/codeflow/app/", "/codeflow/proof/",
                      "/codeflow/portal/", "/codeflow/system-stack/",
                      "/codeflow/assets/codeflow-municipal-scope-questionnaire.pdf",
                      "/codeflow/assets/codeflow-sales-model-pricing-explanation.pdf"]:
            with self.subTest(route=route):
                self.assertIn("https://kyber-llc.com" + route, locations)
        for url in locations:
            self.assertIsNotNone(url)
            assert url is not None
            self.assertTrue(local_target(url).is_file(), f"Missing sitemap target: {url}")

    def test_security_contact_has_valid_expiry_and_static_host_support(self):
        path = ROOT / ".well-known/security.txt"
        self.assertTrue(path.exists(), "Missing security contact file")
        text = path.read_text()
        fields = dict(line.split(": ", 1) for line in text.splitlines() if ": " in line)
        self.assertEqual(fields.get("Contact"), "mailto:harley@kyber-llc.com")
        self.assertEqual(fields.get("Canonical"), "https://kyber-llc.com/.well-known/security.txt")
        expiry = datetime.fromisoformat(fields["Expires"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        self.assertGreater(expiry, now, "Renew security.txt expiry after reviewing the contact")
        self.assertLess((expiry - now).days, 366)
        self.assertNotRegex(text.lower(), r"bounty|safe.harbor|permission|reward")
        self.assertTrue((ROOT / ".nojekyll").exists(), "GitHub Pages must serve .well-known")

    def test_changed_pages_have_working_internal_links_and_landmarks(self):
        checked = set()
        for relative in PUBLIC_PAGES:
            page = Page(ROOT / relative)
            with self.subTest(page=relative):
                self.assertEqual(len(page.attrs("h1")), 1)
                self.assertEqual(len(page.attrs("main")), 1)
                self.assertIn({"lang": "en"}, page.attrs("html"))
                self.assertEqual(len(page.attrs("title")), 1)
                ids = [a["id"] for _, a in page.tags if "id" in a]
                self.assertEqual(len(ids), len(set(ids)), "Duplicate element IDs")
                self.assertIn("main", ids)
                self.assertIn('href="#main"', page.source)
                canonical = [a["href"] for a in page.attrs("link") if a.get("rel") == "canonical"]
                self.assertEqual(canonical, ["https://kyber-llc.com" + public_route(relative)])
                description = [a.get("content", "") for a in page.attrs("meta") if a.get("name") == "description"]
                self.assertEqual(len(description), 1)
                self.assertTrue(description[0])
                for tag, attrs in page.tags:
                    target = attrs.get("href") or attrs.get("src")
                    if not target:
                        continue
                    resolved = urljoin("https://kyber-llc.com" + public_route(relative), target)
                    parts = urlsplit(resolved)
                    if parts.scheme == "mailto":
                        self.assertEqual(parts.path, "harley@kyber-llc.com")
                        continue
                    if parts.scheme == "tel":
                        self.assertIn(relative, ["privacy.html", "terms.html"])
                        preserved = json.loads((ROOT / "tests/preserved_assets.json").read_text())["legal_blocks"][relative]
                        self.assertIn('href="' + target + '"', preserved)
                        self.assertRegex(parts.path, r"^\+[1-9]\d{1,14}$")
                        continue
                    self.assertEqual(parts.netloc, "kyber-llc.com", f"Unexpected external dependency: {target}")
                    path = local_target(resolved)
                    self.assertTrue(path.is_file(), f"Broken target from {relative}: {target}")
                    checked.add((relative, target))
                    if parts.fragment:
                        ids = [a.get("id") for _, a in Page(path).tags]
                        self.assertIn(unquote(parts.fragment), ids, f"Broken fragment: {relative} -> {target}")
        self.assertGreater(len(checked), 100, "Link coverage unexpectedly narrow")
        print(f"\nVerified {len(checked)} distinct page/link pairs across {len(PUBLIC_PAGES)} public pages.")

    def test_service_claims_depth_and_quote_boundaries(self):
        for relative in PUBLIC_PAGES:
            page = Page(ROOT / relative)
            with self.subTest(page=relative):
                self.assertNotRegex(page.source.lower(), r"\bcrest\b|\boscp\b|daybreak\s+red|accredited|certified|federal clearance|security clearance")
                self.assertNotRegex(page.text.lower(), r"\d+\+? years|trusted by \d|[1-9]\d*\s*%|\$\s*\d")
        services = Page(ROOT / "services/index.html").text.lower()
        for phrase in ["written authorization", "third-party permissions", "stop conditions", "emergency contacts",
                       "raw scanner output is not a full penetration test", "manual validation",
                       "full adversary simulation", "scope and capability review", "exclusions",
                       "executive summary", "technical findings and evidence", "remediation",
                       "retest", "fee", "window", "secure transfer", "unconfirmed observations"]:
            self.assertIn(phrase, services)
        pricing = Page(ROOT / "pricing/index.html").text.lower()
        for phrase in ["written quote", "same agreed scope", "scoping", "reporting", "travel", "retest"]:
            self.assertIn(phrase, pricing)
        contact = Page(ROOT / "contact/index.html").text.lower()
        self.assertIn("not authorization", contact)
        self.assertIn("nothing is submitted through a website form", contact)
        self.assertIn("copy the address", contact)
        self.assertIn("harley katt", Page(ROOT / "about/index.html").text.lower())
        self.assertIn("alex ruby", Page(ROOT / "about/index.html").text.lower())

    def test_schema_has_no_product_pricing_reviews_or_credentials(self):
        page = Page(ROOT / "index.html")
        scripts = re.findall(r'<script type="application/ld\+json">(.*?)</script>', page.source, re.S)
        self.assertEqual(len(scripts), 1)
        schema = json.loads(scripts[0])
        self.assertEqual(schema["@type"], "Organization")
        self.assertEqual(schema["email"], "harley@kyber-llc.com")
        self.assertEqual(schema["url"], "https://kyber-llc.com/")
        for key in ["offers", "aggregateRating", "review", "award", "hasCredential"]:
            self.assertNotIn(key, schema)

    def test_physical_and_combined_readiness_is_not_claimed(self):
        for path in [p for p in PUBLIC_PAGES if p not in ['privacy.html', 'terms.html']]:
            with self.subTest(path=path):
                text = (ROOT / path).read_text(encoding='utf-8').lower()
                for phrase in ['proposed services', 'not available for scheduling', 'legal/licensing', 'demonstrated competence', 'insurance']:
                    self.assertIn(phrase, text)
        css = (ROOT / 'assets/security-services.css').read_text(encoding='utf-8')
        self.assertIn('html { scroll-behavior: auto;', css)

    def test_codeflow_assets_and_existing_legal_blocks_are_unchanged(self):
        baseline = json.loads((ROOT / "tests/preserved_assets.json").read_text())
        self.assertEqual(len(baseline["sha256"]), 35)
        self.assertIn("codeflow/index.html", baseline["sha256"])
        self.assertIn("codeflow/app/index.html", baseline["sha256"])
        self.assertIn("assets/codeflow-system.css", baseline["sha256"])
        for relative, expected in baseline["sha256"].items():
            with self.subTest(asset=relative):
                path = ROOT / relative
                self.assertTrue(path.is_file())
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected,
                                 "Protected existing-product asset changed")
        for relative, block in baseline["legal_blocks"].items():
            self.assertIn(block, (ROOT / relative).read_text(), "Existing legal language changed")
        products = Page(ROOT / "products/index.html")
        self.assertIn("existing products", products.text.lower())
        self.assertIn("separate from security", products.text.lower())
        self.assertIn('href="/codeflow/"', products.source)
        self.assertIn('href="/codeflow/app/"', products.source)


if __name__ == "__main__":
    unittest.main()
