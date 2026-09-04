/* Read-only browser geometry assertion. Evaluate in a loaded Kyber page.
 * Home: stacked CTA/email >=16px apart. All routes: no overflow, links
 * retained, and contact-panel controls remain separated and contained.
 * This does not submit an email or click an external destination.
 */
(() => {
  const checks = [];
  const rect = el => el.getBoundingClientRect();
  const box = el => rect(el).toJSON();
  const add = (name, pass, detail = {}) => checks.push({name, pass, ...detail});
  add('no-page-overflow', document.documentElement.scrollWidth <= innerWidth + 1);
  add('email-not-obfuscated', !document.querySelector('a[href^="/cdn-cgi/l/email-protection"]'));
  if (location.pathname === '/') {
    const group = document.querySelector('.contact-actions');
    add('home-contact-group-present', Boolean(group));
    if (group) {
      const button = group.querySelector('.button');
      const email = group.querySelector('.email-link');
      add('home-contact-pair-present', Boolean(button && email));
      if (button && email) {
        const b = rect(button), e = rect(email);
        add('home-contact-stacked-gap', e.top - b.bottom >= 15.9,
            {gap: e.top - b.bottom, button: box(button), email: box(email)});
        add('home-contact-left-aligned', Math.abs(b.left - e.left) < 1);
        add('home-email-correct', email.textContent.trim() === 'harley@kyber-llc.com' &&
            email.getAttribute('href') === 'mailto:harley@kyber-llc.com');
      }
    }
  }
  for (const [i, panel] of [...document.querySelectorAll('.contact-panel')].entries()) {
    const b = panel.querySelector('.button'), e = panel.querySelector('.email-link');
    if (!b || !e) continue;
    const br = rect(b), er = rect(e), pr = rect(panel);
    const separation = Math.max(er.top-br.bottom, br.top-er.bottom, er.left-br.right, br.left-er.right);
    add(`panel-${i}-links-separated`, separation >= 15.9, {separation});
    add(`panel-${i}-controls-contained`, [br, er].every(r => r.left >= pr.left - 1 && r.right <= pr.right + 1));
  }
  return JSON.stringify({url: location.href, width: innerWidth, height: innerHeight,
    checks, passed: checks.every(c => c.pass)});
})()
