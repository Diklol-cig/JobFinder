// Self-test for Code.gs outside Google: node jobfinder-easy/selftest.js
// Fakes only the network (UrlFetchApp) and checks the job-site parsers, site switching, filters, scoring,
// the English/Hungarian texts and the setup window.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const responses = []; // [urlPart, body] pairs the fake network answers with
const res = (body, code = 200) => ({ getResponseCode: () => code, getContentText: () => body, getAllHeaders: () => ({ 'Set-Cookie': ['a=1; Path=/', 'b=2'] }) });
const answer = req => { const hit = responses.find(([part]) => req.url.includes(part)); return hit && hit[1] !== null ? res(hit[1]) : res('', 500); };
const ctx = { console, UrlFetchApp: { fetchAll: reqs => reqs.map(answer), fetch: (url, o) => answer(Object.assign({ url }, o)) } };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname, 'Code.gs'), 'utf8') + '\nthis.T = { TEXT, SITES, SETTINGS, searchAll_, toKey_, display_, wizardHtml_, buildSheet_, readSettings_, writeSetting_, onEdit, prefilter_, interleave_, decide_, wordsRegex_, near_, cell_, link_, pageText_, describe_ };', ctx);
const T = ctx.T;
const setLang = l => vm.runInContext(`LANG_CACHE = '${l}'`, ctx); // there is no sheet here, so pick the language directly
setLang('en');
// Values from the sandbox have their own Array/Object, so compare plain copies.
const eq = (actual, expected, msg) => assert.deepStrictEqual(JSON.parse(JSON.stringify(actual)), expected, msg);

const today = new Date().toUTCString();
const LINKEDIN = `<li><div data-entity-urn="urn:li:jobPosting:111"><a class="base-card__full-link x" href="https://hu.linkedin.com/jobs/view/receptionist-111?trk=a">
  <h3 class="base-search-card__title">Receptionist &amp; Office Assistant</h3><h4 class="base-search-card__subtitle"><a>Hotel Kft.</a></h4>
  <span class="job-search-card__location">Budapest, Hungary</span></div></li>
  <li><div data-entity-urn="urn:li:jobPosting:222"><h3 class="base-search-card__title">Sales Intern</h3><h4 class="base-search-card__subtitle">Shop</h4></div></li>`;
const PROFESSION = `<?xml version="1.0"?><rss><channel><title>x</title>
  <item><title>Ügyfélszolgálati munkatárs</title><guid>https://www.profession.hu/allas/ugyfelszolgalati-munkatars-optesz-miskolc-3051303</guid><pubDate>${today}</pubDate></item>
  <item><title>Old job</title><guid>https://www.profession.hu/allas/old-job-123</guid><pubDate>Mon, 01 Jan 2024 00:00:00 +0000</pubDate></item>
  </channel></rss>`;
const NFJ = JSON.stringify({ postings: [
  { id: 'a-hu', title: 'Office Admin', name: 'Acme', url: 'office-admin-acme', posted: Date.now(), location: { places: [{ city: 'Budapest', country: { name: 'Hungary' } }] } },
  { id: 'b-pl', title: 'Office Admin', name: 'Polska', posted: Date.now(), location: { places: [{ city: 'Warszawa', country: { name: 'Poland' } }] } },
  { id: 'c-rem', title: 'Support Agent', name: 'Remote Co', fullyRemote: true, posted: Date.now(), location: { places: [{ city: 'Remote' }] } },
] });
const JOOBLE = JSON.stringify({ jobs: [{ id: 99, title: 'Receptionist &amp; Office Assistant', company: 'Hotel Kft.', location: 'Budapest', link: 'https://jooble.org/desc/99', snippet: '<b>Front desk</b> work', updated: new Date().toISOString() }] });
responses.push(['linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings', LINKEDIN], ['profession.hu/allasok/', PROFESSION],
  ['https://www.profession.hu/', '<html>home</html>'], ['nofluffjobs.com/api/search', NFJ], ['jooble.org/api/', JOOBLE]);

const settings = (sites, extra) => Object.assign({ titles: 'Receptionist', where: 'Budapest, Hungary', workplace: 'hybrid', maxOffice: 2, since: 'week',
  avoidTitle: 'intern', avoid: '', joobleKey: 'k', strongScore: 70, maybeScore: 50 }, ...Object.keys(T.SITES).map(n => ({ ['site:' + n]: sites.includes(n) })), extra);

// Every site gets its own tick box in Settings, so switching sites needs no code.
Object.keys(T.SITES).forEach(n => assert(T.SETTINGS.some(d => d.key === 'site:' + n && d.checkbox), 'no tick box for ' + n));

// Each site parses into the same job shape, and only ticked sites are searched.
const li = T.searchAll_(settings(['LinkedIn'])).jobs;
eq(li.map(j => [j.id, j.title, j.company, j.location, j.url, j.source]), [
  ['li_111', 'Receptionist & Office Assistant', 'Hotel Kft.', 'Budapest, Hungary', 'https://hu.linkedin.com/jobs/view/receptionist-111', 'LinkedIn'],
  ['li_222', 'Sales Intern', 'Shop', '', 'https://www.linkedin.com/jobs/view/222', 'LinkedIn']]);
const prof = T.searchAll_(settings(['Profession.hu'])).jobs;
eq(prof.map(j => [j.id, j.title, j.cookie, j.source]), [
  ['prof_3051303', 'Ügyfélszolgálati munkatárs', 'a=1; b=2', 'Profession.hu'], ['prof_123', 'Old job', 'a=1; b=2', 'Profession.hu']]);
eq(T.searchAll_(settings(['NoFluffJobs'])).jobs.map(j => j.id), ['nfj_a-hu', 'nfj_c-rem'], 'NFJ keeps nearby + remote, drops Poland');
eq(T.searchAll_(settings(['NoFluffJobs'], { workplace: 'remote' })).jobs.map(j => j.id), ['nfj_c-rem'], 'remote-only drops office jobs');
const jb = T.searchAll_(settings(['Jooble'])).jobs;
eq(jb.map(j => [j.id, j.snippet]), [['jb_99', 'Front desk work']]);
assert.match(T.describe_(jb[0]), /^Job title: Receptionist & Office Assistant at Hotel Kft\. \(Budapest\)/, 'too-short ad text falls back to the title');
const all = T.searchAll_(settings(Object.keys(T.SITES)));
eq([...new Set(all.jobs.map(j => j.source))], ['LinkedIn', 'Profession.hu', 'NoFluffJobs', 'Jooble']);
assert.throws(() => T.searchAll_(settings([])), /No job site is ticked/);

// A broken site is reported but doesn't stop the others; Jooble without a key explains itself.
responses.unshift(['profession.hu/allasok/', null]); // Profession.hu is down
const partial = T.searchAll_(settings(['LinkedIn', 'Profession.hu', 'Jooble'], { joobleKey: '' }));
responses.shift();
eq(partial.jobs.map(j => j.source), ['LinkedIn', 'LinkedIn']);
eq(partial.problems, ['Profession.hu: the site did not answer (error 500), will try again next time',
  'Jooble: needs a free Jooble key (🔎 JobFinder > ▶ Setup, step 4)']);

// Filtering: seen, too old, unwanted title words (whole words only), avoided companies, cross-site duplicates.
const s = settings([], { avoidTitle: 'intern', avoid: 'Casino' });
const kept = T.prefilter_(all.jobs.concat([{ id: 'x1', title: 'Internal Auditor', company: 'Bank', source: 'LinkedIn' },
  { id: 'x2', title: 'Host', company: 'Grand Casino', source: 'LinkedIn' }]), new Set(['nfj_c-rem']), s).map(j => j.id);
eq(kept, ['li_111', 'prof_3051303', 'nfj_a-hu', 'x1'],
  'drops intern, old, seen, casino, and the Jooble copy of the LinkedIn job');
assert.strictEqual(T.wordsRegex_(''), null);
assert(T.wordsRegex_('c++, ügyfél').test('Senior C++ dev') && T.wordsRegex_('ügyfél').test('Ügyfél munkatárs'));
assert(T.near_('Debrecen Hungary', 'Budapest, Hungary') && !T.near_('Kraków Poland', 'Budapest, Hungary') && T.near_('Pécs', 'pecs'));

// Interleave: one busy site can't use up the daily limit.
const mix = T.interleave_([1, 2, 3].map(i => ({ id: 'a' + i, source: 'A' })).concat([{ id: 'b1', source: 'B' }]));
eq(mix.map(j => j.id), ['a1', 'b1', 'a2', 'a3']);

// Scoring rules the AI can't override.
const r = (o) => Object.assign({ skills_fit: 35, experience_fit: 18, location_fit: 18, conditions_fit: 15, work_mode: 'Hybrid', office_days_per_week: 2 }, o);
const sd = settings([]);
eq(T.decide_(r(), sd), { score: 86, verdict: 'great', note: '' });
assert.strictEqual(T.decide_(r({ office_days_per_week: 3 }), sd).verdict, 'skip');
assert.strictEqual(T.decide_(r({ work_mode: 'Onsite' }), sd).verdict, 'skip');
assert.strictEqual(T.decide_(r({ work_mode: 'Hybrid' }), settings([], { workplace: 'remote' })).verdict, 'skip');
assert.strictEqual(T.decide_(r({ work_mode: 'Onsite' }), settings([], { workplace: 'any' })).verdict, 'great');
assert.strictEqual(T.decide_(r({ breaks_dealbreaker: true, dealbreaker_reason: 'Night shifts' }), sd).note, 'Night shifts');
eq(T.decide_(r({ office_days_per_week: -1, skills_fit: 22 }), sd), { score: 68, verdict: 'maybe', note: '⚠️ Check how many office days they expect' });
assert.strictEqual(T.decide_(r({ skills_fit: 999, experience_fit: 'x' }), sd).score, 73, 'sub-scores are clamped');
assert.strictEqual(T.decide_(r({ skills_fit: 0, experience_fit: 0 }), sd).verdict, 'low');

// Text from job sites can't become a spreadsheet formula.
assert.strictEqual(T.cell_('=IMPORTXML("x")'), '\'=IMPORTXML("x")');
assert.strictEqual(T.cell_('Receptionist'), 'Receptionist');
assert.strictEqual(T.link_('https://a.b/"x', 'Open'), '=HYPERLINK("https://a.b/%22x","Open")');
assert.strictEqual(T.pageText_('<nav>menu</nav><main><h1>Job</h1><script>x()</script><p>Tasks</p></main><footer>f</footer>'), 'Job Tasks');

// Hungarian: rule notes and site errors are translated.
setLang('hu');
assert.strictEqual(T.decide_(r({ office_days_per_week: 3 }), sd).note, 'Heti 3 irodai nap (a határod 2)');
assert.strictEqual(T.decide_(r({ work_mode: 'Hybrid' }), settings([], { workplace: 'remote' })).note, 'Hibrid munka, de te csak otthonról dolgoznál');
assert.throws(() => T.searchAll_(settings([])), /Egy állásportál sincs bejelölve/);
setLang('en');

// Both languages have exactly the same texts (no missing translation), and every setting has a label and help in both.
const shape = o => typeof o === 'function' ? 'fn' + o.length : Array.isArray(o) ? 'list' + o.length
  : o && typeof o === 'object' ? '{' + Object.keys(o).sort().map(k => k + ':' + shape(o[k])).join(',') + '}' : typeof o;
assert.strictEqual(shape(T.TEXT.hu), shape(T.TEXT.en));
T.SETTINGS.forEach(d => Object.keys(T.TEXT).forEach(l => assert(typeof d.label[l] === 'string' && typeof d.help[l] === 'string', d.key + ' ' + l)));
assert.strictEqual(new Set(T.SETTINGS.map(d => d.key)).size, T.SETTINGS.length, 'setting keys are unique');

// Switching language keeps answers: shown text in either language maps to the same key, free text stays.
const byKey = k => T.SETTINGS.find(d => d.key === k);
assert.strictEqual(T.toKey_(byKey('workplace'), 'Otthonról vagy hibrid'), 'hybrid');
assert.strictEqual(T.display_(byKey('workplace'), 'Otthonról vagy hibrid', 'en'), 'Remote or hybrid');
assert.strictEqual(T.display_(byKey('since'), 'month', 'hu'), '1 hónap');
assert.strictEqual(T.toKey_(byKey('cvLanguage'), 'A hirdetés nyelvén'), 'same');
assert.strictEqual(T.toKey_(byKey('myLanguage'), 'magyar'), 'Hungarian', 'case does not matter');
assert.strictEqual(T.toKey_(byKey('myLanguage'), 'Ukrán'), 'Ukrán', 'free text stays');
assert.strictEqual(T.toKey_(byKey('lang'), 'Magyar'), 'hu');
assert.strictEqual(T.toKey_(byKey('titles'), 'Recepciós'), 'Recepciós');

// Setup window in both languages: every {{text}} is filled in, user data is injected safely
// (a "$'" or "</script>" in the CV can't break the page), and its script parses.
Object.keys(T.TEXT).forEach(l => {
  const page = T.wizardHtml_({ lang: l, values: { cv: "Saved $' 500 </script>" } }, T.TEXT[l]);
  assert(!/\{\{|__DATA__|undefined/.test(page), 'unfilled text in the ' + l + ' setup window');
  assert(page.includes("Saved $' 500 \\u003c/script>"));
  new vm.Script(page.match(/<script>([\s\S]*)<\/script>/)[1]);
});
assert(T.wizardHtml_({ lang: 'hu', values: {} }, T.TEXT.hu).includes('Mentés és indítás'));

// ---------- The sheet itself, on a small in-memory fake of Google Sheets ----------
// Unknown formatting calls (setWrap, setFontColor, ...) are accepted and ignored.
const chain = t => new Proxy(t, { get: (o, k) => (k in o ? o[k] : () => chain(o)) });
function fakeSheets(locale, preset) {
  const tabs = [];
  const sheet = name => {
    const grid = [], sh = { name };
    const cell = (r, c) => { const v = (grid[r - 1] || [])[c - 1]; return v === undefined ? '' : v; };
    const range = (r, c, nr = 1, nc = 1) => chain({
      getSheet: () => sh.p, getRow: () => r, getColumn: () => c,
      getValues: () => Array.from({ length: nr }, (_, i) => Array.from({ length: nc }, (_, j) => cell(r + i, c + j))),
      getValue: () => cell(r, c),
      setValues: vals => { vals.forEach((row, i) => row.forEach((v, j) => { (grid[r - 1 + i] = grid[r - 1 + i] || [])[c - 1 + j] = v; })); return range(r, c, nr, nc); },
      setValue: v => range(r, c).setValues([[v]]),
      clearContent: () => range(r, c, nr, nc).setValues(Array.from({ length: nr }, () => Array(nc).fill(''))),
    });
    Object.assign(sh, {
      getName: () => sh.name, setName: n => { sh.name = n; return sh.p; },
      getLastRow: () => { for (let i = grid.length; i > 0; i--) if ((grid[i - 1] || []).some(v => v !== '' && v !== undefined)) return i; return 0; },
      clear: () => { grid.length = 0; return sh.p; },
      getRange: (a, c, nr, nc) => {
        if (typeof a !== 'string') return range(a, c, nr, nc);
        const m = a.match(/^([A-Z])(\d+)(:[A-Z](\d*))?$/), r = +m[2];
        return range(r, m[1].charCodeAt(0) - 64, m[3] ? (m[4] ? +m[4] - r + 1 : Math.max(sh.getLastRow() - r + 1, 1)) : 1, 1);
      },
    });
    sh.p = chain(sh);
    return sh;
  };
  Object.keys(preset || {}).forEach(n => { const s = sheet(n); s.getRange(1, 1, preset[n].length, preset[n][0].length).setValues(preset[n]); tabs.push(s); });
  const ss = chain({
    getSpreadsheetLocale: () => locale,
    getSheetByName: n => { const s = tabs.find(x => x.name === n); return s ? s.p : null; },
    insertSheet: (n, i) => { const s = sheet(n); tabs.splice(i, 0, s); return s.p; },
    getSheets: () => tabs.map(s => s.p),
    deleteSheet: p => tabs.splice(tabs.findIndex(s => s.p === p), 1),
  });
  ctx.SpreadsheetApp = { getActive: () => ss, newDataValidation: () => chain({ build: () => ({}) }) };
  vm.runInContext('LANG_CACHE = null', ctx);
  return { names: () => tabs.map(s => s.name), tab: n => ss.getSheetByName(n) };
}
const rowOf = (sh, key) => sh.getRange(1, 4, sh.getLastRow(), 1).getValues().findIndex(r => r[0] === key) + 1;
const shown = (sh, key) => sh.getRange(rowOf(sh, key), 1, 1, 2).getValues()[0];

// English sheet: tabs and settings appear, answers are stored as shown text and read back as keys.
let book = fakeSheets('en_US');
T.buildSheet_();
eq(book.names(), ['Start here', 'Settings', 'My CV', 'Jobs']);
T.writeSetting_('workplace', 'remote');
T.writeSetting_('name', 'Anna');
book.tab('Start here').getRange('A3').setValue('Last run: 2026-11-17 07:00: Checked 3 new job(s)');
eq(shown(book.tab('Settings'), 'workplace'), ['Work from', 'Remote only']);
assert.strictEqual(T.readSettings_().workplace, 'remote');

// Switching "Language / Nyelv" to Magyar in the sheet (onEdit) translates everything and keeps every answer.
const st = book.tab('Settings');
st.getRange(rowOf(st, 'lang'), 2).setValue('Magyar');
T.onEdit({ range: st.getRange(rowOf(st, 'lang'), 2) });
eq(book.names(), ['Kezdés', 'Beállítások', 'Önéletrajzom', 'Állások']);
const hu = book.tab('Beállítások');
eq(shown(hu, 'workplace'), ['Munkavégzés helye', 'Csak otthonról']);
eq(shown(hu, 'name'), ['Teljes neved', 'Anna']);
eq(shown(hu, 'since'), ['Ennyi időn belül feladott állások', '1 hét']);
const sHu = T.readSettings_();
eq([sHu.lang, sHu.workplace, sHu.since, sHu.name], ['hu', 'remote', 'week', 'Anna']);
assert.strictEqual(book.tab('Kezdés').getRange('A3').getValue(), 'Last run: 2026-11-17 07:00: Checked 3 new job(s)', 'last run status is kept');
assert.strictEqual(book.tab('Kezdés').getRange('A1').getValue(), T.TEXT.hu.start[0]);
assert.strictEqual(book.tab('Állások').getRange(1, 4).getValue(), 'Munkakör');

// A new sheet in a Hungarian Google account starts in Hungarian, with Hungarian defaults.
book = fakeSheets('hu_HU');
T.buildSheet_();
eq(book.names(), ['Kezdés', 'Beállítások', 'Önéletrajzom', 'Állások']);
eq(shown(book.tab('Beállítások'), 'myLanguage'), ['Az összefoglalók és e-mailek nyelve', 'Magyar']);
assert.strictEqual(T.readSettings_().myLanguage, 'Hungarian');

// A sheet made with the earlier English-only version (no hidden key column) is upgraded without losing answers.
book = fakeSheets('en_US', { Settings: [['Setting', 'Your answer', 'Help'], ['Work from', 'Remote only', ''], ['Your full name', 'Bob', ''], ['Search Jooble', true, '']] });
T.buildSheet_();
const old = T.readSettings_();
eq([old.workplace, old.name, old['site:Jooble'], old.lang], ['remote', 'Bob', true, 'en']);
eq(book.names(), ['Start here', 'Settings', 'My CV', 'Jobs']);
setLang('en');

console.log('All JobFinder Easy self-tests passed.');
