"""Offline contract regressions for the proposed monthly-care offer.

Run with the full suite: python3 -m unittest discover -s tests -v
No customer testing, network requests, or checkout actions.
"""
from decimal import Decimal
from html import unescape
import hashlib
import json
import re
import unittest
from test_security_site import ROOT, Page

CARE_ROUTES = [
    "index.html", "services/index.html", "pricing/index.html", "about/index.html",
    "contact/index.html", "products/index.html", "systems/index.html",
    "platform/index.html", "legacy/index.html",
]
OFFER = "Kyber Website & Office Care"
READINESS = (
    "Physical and combined assessments are proposed services, not available for scheduling. "
    "We are accepting non-binding scope inquiries only. Field work and full adversary simulation "
    "remain unavailable until activity-specific legal/licensing review, demonstrated competence, "
    "insurance, written authorization, and capability review are complete. "
    "An inquiry is not a booking or authorization to test."
)


def visible(source):
    # Metadata, comments and script text cannot satisfy a visible-copy assertion.
    source = re.sub(r"<(head|script|style)\b[^>]*>.*?</\1>", "", source, flags=re.S | re.I)
    source = re.sub(r"<!--.*?-->", "", source, flags=re.S)
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", source))).strip()


class MonthlyCareTests(unittest.TestCase):
    def test_route_inventory_covers_all_active_security_marketing(self):
        discovered = sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob("*.html")
                            if "/assets/security-services.css" in p.read_text()
                            and p.name not in ("privacy.html", "terms.html"))
        self.assertEqual(discovered, sorted(CARE_ROUTES))
        # Partners is an existing redirect, not an active marketing page.
        self.assertIn('content="0;url=/legacy/"', (ROOT / "partners/index.html").read_text())

    def test_every_entry_has_a_visible_scoped_preview_near_the_offer(self):
        for rel in CARE_ROUTES:
            with self.subTest(route=rel):
                page = Page(ROOT / rel)
                hero = re.search(r'<section class="(?:page-hero|hero)">(.*?)</section>', page.source, re.S)
                self.assertIsNotNone(hero)
                assert hero is not None
                text = visible(hero.group(1))
                for phrase in [OFFER, "$1,600/month", "planned", "service preview",
                               "within agreed scope", "not available for scheduling",
                               "legal/licensing", "demonstrated competence", "insurance",
                               "written authorization"]:
                    self.assertIn(phrase.lower(), text.lower(), phrase)
                self.assertIn(READINESS, visible(page.source))
                self.assertNotRegex(visible(page.source).lower(), r"book now|subscribe now|pay now|schedule your visit")
                self.assertIn("Discuss fit", visible(page.source))

    def test_metadata_and_organization_describe_the_same_preview(self):
        for rel in CARE_ROUTES:
            with self.subTest(route=rel):
                page = Page(ROOT / rel)
                title_match = re.search(r"<title>(.*?)</title>", page.source)
                assert title_match is not None
                title = unescape(title_match.group(1))
                meta = {m.get("name") or m.get("property"): m.get("content") for m in page.attrs("meta")}
                self.assertIn("Website & Office Care", title)
                self.assertEqual(meta["og:title"], title)
                self.assertEqual(meta["og:description"], meta["description"])
                for phrase in ["Website & Office Care", "$1,600/month", "planned", "preview", "not available for scheduling"]:
                    self.assertIn(phrase, meta["description"])
        home = (ROOT / "index.html").read_text()
        schema_match = re.search(r'<script type="application/ld\+json">(.*?)</script>', home, re.S)
        assert schema_match is not None
        schema = json.loads(schema_match.group(1))
        self.assertEqual(schema["@type"], "Organization")
        self.assertIn(OFFER, schema["description"])
        for phrase in ["$1,600/month", "planned", "preview", "not available for scheduling"]:
            self.assertIn(phrase, schema["description"])
        self.assertNotIn("offers", schema, "Do not advertise a purchasable offer before readiness")

    def test_monthly_scope_is_concrete_and_limited(self):
        for rel in ["index.html", "services/index.html", "pricing/index.html"]:
            with self.subTest(route=rel):
                text = visible((ROOT / rel).read_text()).lower()
                for phrase in ["new website", "existing website", "agreed ongoing changes",
                               "recurring authorized website bug/vulnerability checks",
                               "two office visits per calendar month", "first and third weeks",
                               "wi-fi/security configuration", "authorized low-impact vulnerability review",
                               "non-invasive observational office-security walkthrough", "findings",
                               "priorities", "agreed fix verification", "within agreed scope"]:
                    self.assertIn(phrase, text)
                for phrase in ["not unlimited", "new build", "onboarding", "major changes",
                               "before agreement", "no fixed setup charge", "no security guarantee",
                               "not a full penetration test", "24/7 soc"]:
                    self.assertIn(phrase, text)
                self.assertNotIn("biweekly", text, "Two visits per calendar month is not every two weeks")
        services = (ROOT / "services/index.html").read_text()
        for section in ["physical", "combined"]:
            found = re.search(r'<section[^>]*id="' + section + r'"[^>]*>(.*?)</section>', services, re.S)
            assert found is not None
            self.assertIn(READINESS, visible(found.group(1)))
            self.assertIn("two office visits per calendar month", visible(found.group(1)).lower())

    def referral_text(self, rel):
        source = (ROOT / rel).read_text()
        terms = re.search(r'<details\b[^>]*id="referrals"[^>]*>(.*?)</details>', source, re.S)
        self.assertIsNotNone(terms, f"Discoverable referral terms missing: {rel}")
        assert terms is not None
        return visible(terms.group(1))

    def test_referral_math_uses_the_visible_base_rate(self):
        for rel in ["pricing/index.html", "contact/index.html", "legacy/index.html"]:
            with self.subTest(route=rel):
                text = self.referral_text(rel)
                numbers = [Decimal(n.replace(",", "")) for n in re.findall(r"\$([\d,]+)", text)]
                self.assertEqual(numbers, [Decimal("1600"), Decimal("1360"), Decimal("240")])
                percentages = set(re.findall(r"\b(\d+)%", text))
                self.assertEqual(percentages, {"15"})
                base, discounted, saving = numbers
                self.assertEqual(base * Decimal("0.15"), saving)
                self.assertEqual(base - saving, discounted)
                self.assertIn("at the current", text.lower(), "Dollar amounts are not a forever-price guarantee")

    def test_referral_qualification_cap_and_independent_continuity(self):
        for rel in ["pricing/index.html", "contact/index.html", "legacy/index.html"]:
            with self.subTest(route=rel):
                text = self.referral_text(rel).lower()
                for phrase in ["both the referrer and the referred customer", "first payment clears",
                               "next billing cycle", "maximum 15% per account", "does not stack",
                               "each customer’s own uninterrupted subscription",
                               "independently of the other customer",
                               "one customer cancels", "does not end the other customer’s discount",
                               "cancelling and restarting ends that customer’s discount",
                               "recurring monthly service only", "not separately quoted projects or hardware",
                               "identify the referrer at signup", "not payment for reviews",
                               "disclose the benefit when recommending us publicly"]:
                    self.assertIn(phrase, text)
                self.assertNotRegex(text, r"automatically applied|promo code|coupon code|forever price")
        for rel in CARE_ROUTES:
            self.assertIn('href="/pricing/#referrals"', (ROOT / rel).read_text())
        partner = (ROOT / "partners/index.html").read_text()
        self.assertIn('content="0;url=/legacy/"', partner)
        self.assertIn('href="#referrals"', (ROOT / "legacy/index.html").read_text())

    def test_payment_and_professional_coverage_are_distinct(self):
        for rel in ["pricing/index.html", "contact/index.html"]:
            with self.subTest(route=rel):
                text = visible((ROOT / rel).read_text()).lower()
                self.assertIn("client pays kyber directly", text)
                self.assertIn("insurance reimbursement is not required", text)
                self.assertIn("kyber’s own professional coverage", text)
                self.assertIn("not a claim that coverage is in place", text)
                self.assertIn("no public checkout", text)

    def test_no_unapproved_rates_or_stale_primary_offer(self):
        for rel in CARE_ROUTES:
            with self.subTest(route=rel):
                source = (ROOT / rel).read_text()
                text = visible(source).lower()
                self.assertNotRegex(text, r"\$\s*(?:3,?500|595)\b|no fixed security-service fees|not a software plan")
                self.assertNotIn("primary offering is professional security-testing", text)
                self.assertNotIn("kyber’s focus is security testing", text)
                self.assertNotIn("scope a test", text)

    def test_design_and_protected_routes_match_original_baseline(self):
        fixture = ROOT / "tests/monthly_care_preservation.json"
        self.assertTrue(fixture.is_file(), "Original-design preservation manifest is required")
        baseline = json.loads(fixture.read_text())
        self.assertEqual(baseline["baseline_revision"], "25ab776")
        self.assertEqual(len(baseline["sha256"]), 45)
        for rel, expected in baseline["sha256"].items():
            with self.subTest(file=rel):
                self.assertEqual(hashlib.sha256((ROOT / rel).read_bytes()).hexdigest(), expected,
                                 "Protected CSS, logo, product, legal or redirect changed")
        home = (ROOT / "index.html").read_text()
        for pattern, key in [(r'<svg class="boundary-drawing".*?</svg>', "hero_svg_sha256"),
                             (r'<section class="section threat-section".*?</section>', "threat_section_sha256")]:
            match = re.search(pattern, home, re.S)
            assert match is not None
            self.assertEqual(hashlib.sha256(match.group().encode()).hexdigest(), baseline[key])
        for rel in CARE_ROUTES:
            page = Page(ROOT / rel)
            self.assertEqual(page.attrs("section"), baseline["sections"][rel], rel)
            csp = [m["content"] for m in page.attrs("meta") if m.get("http-equiv") == "Content-Security-Policy"]
            self.assertEqual(csp, [baseline["csp"]])
            self.assertNotIn("style=", page.source)
            self.assertTrue(all(s.get("type") == "application/ld+json" for s in page.attrs("script")))


if __name__ == "__main__":
    unittest.main()
