"""Kyber emblem identity, safe SVG, and cache/version regressions."""
from pathlib import Path
from html.parser import HTMLParser
import unittest
import xml.etree.ElementTree as ET
from test_security_site import ROOT, PUBLIC_PAGES

class Images(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.images=[]; self.region=None; self.home_link=False; self.feed(text)
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag in ['header','footer']: self.region=tag
        if tag=='a': self.home_link=a.get('href')=='/'
        if tag=='img' and a.get('class')=='brand-mark':
            self.images.append(dict(a,region=self.region,home_link=self.home_link))
    def handle_endtag(self,tag):
        if tag in ['header','footer']: self.region=None
        if tag=='a': self.home_link=False

class LogoTests(unittest.TestCase):
    def test_three_shape_monochrome_svg_masters_are_safe(self):
        for rel in ['assets/kyber-emblem.svg','assets/kyber-emblem-ink.svg','assets/kyber-mark.svg']:
            raw=(ROOT/rel).read_text(); svg=ET.fromstring(raw)
            self.assertEqual(svg.get('viewBox'),'0 0 100 100')
            self.assertEqual(len(svg.findall('.//{http://www.w3.org/2000/svg}path')),3)
            self.assertLess(len(raw.encode()),1024)
            for node in svg.iter():
                self.assertIn(node.tag.rsplit('}',1)[-1],['svg','g','path','circle'])
                self.assertTrue(set(node.attrib).issubset({'viewBox','fill','d','transform','cx','cy','r'}))
                self.assertFalse(any('url(' in v.lower() for v in node.attrib.values()))
            self.assertNotIn('<!DOCTYPE',raw.upper())
            self.assertNotIn('<!ENTITY',raw.upper())
            self.assertNotIn('<rect',raw)
            self.assertNotIn('<text',raw)
    def test_every_public_header_and_footer_uses_emblem(self):
        for rel in PUBLIC_PAGES:
            source=(ROOT/rel).read_text(); images=Images(source).images
            self.assertEqual(len(images),2,rel)
            self.assertEqual([i['region'] for i in images],['header','footer'])
            for image in images:
                self.assertTrue(image['home_link'])
                self.assertEqual(image['src'],'/assets/kyber-emblem.svg')
                self.assertEqual(image['alt'],'')
                self.assertEqual(image['aria-hidden'],'true')
                self.assertEqual((image['width'],image['height']),('43','45'))
            self.assertNotIn('<span class="brand-mark"',source)
            self.assertIn('href="/assets/kyber-mark.svg?v=2"',source)
            self.assertIn('security-services.css?v=4',source)
    def test_old_box_styling_removed_and_footer_remains_flex(self):
        css=(ROOT/'assets/security-services.css').read_text()
        mark=css.split('.brand-mark {',1)[1].split('}',1)[0]
        self.assertNotIn('border',mark)
        self.assertIn('object-fit: contain',mark)
        self.assertIn('.footer-brand { display: flex;',css)

if __name__=='__main__': unittest.main()
