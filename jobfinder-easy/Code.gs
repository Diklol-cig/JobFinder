// JobFinder Easy: a free daily job search that lives inside a Google Sheet. In English or Hungarian (magyarul).
// Paste this whole file into Extensions > Apps Script, save, and reload the sheet. See README.md.

const LANGS = ['English', 'Hungarian', 'German', 'Polish', 'Romanian', 'Slovak', 'Czech', 'Spanish', 'French', 'Italian', 'Dutch', 'Portuguese'];
const COL_STATUS = 12, COL_ID = 13; // columns in the Jobs tab
const BUDGET_MS = 4 * 60 * 1000; // Google stops scripts at 6 min; leave room for the last CV + email
const HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
  'Accept-Language': 'en-US,en;q=0.9,hu;q=0.8',
};

// ---------- Texts ----------
// Every language has exactly the same keys (selftest.js checks this).
// "opt" lists map the value the script works with (left) to the text shown in the sheet (right).
const TEXT = {
  en: {
    tabs: { start: 'Start here', settings: 'Settings', cv: 'My CV', jobs: 'Jobs' },
    menu: { setup: '▶ Setup (start here)', findNow: 'Find jobs now', stop: 'Stop daily search' },
    opt: {
      lang: { en: 'English', hu: 'Magyar' },
      workplace: { remote: 'Remote only', hybrid: 'Remote or hybrid', any: 'Any (remote, hybrid or office)' },
      level: { entry: 'Entry level', mid: 'Mid level', senior: 'Senior', any: 'Any' },
      coverLetter: { asked: 'Only if the job asks for one', always: 'Always', never: 'Never' },
      since: { day: 'day', week: 'week', month: 'month' },
      langs: LANGS.reduce((o, k) => Object.assign(o, { [k]: k }), {}),
    },
    sameAsAd: 'Same as the job ad',
    modes: { Remote: 'Remote', Hybrid: 'Hybrid', Onsite: 'Onsite', Unknown: 'Unknown' },
    verdict: { great: '⭐ Great match', maybe: '🤔 Maybe', low: '▫️ Low match', skip: '⛔ Skipped' },
    status: ['New', 'Applied', 'Interview', 'Offer', 'Rejected', 'Not interested'],
    jobHeaders: ['Found on', 'Score', 'Verdict', 'Job title', 'Company', 'Location', 'Site', 'Work mode', 'Why (AI summary)', 'Job ad', 'Tailored CV', 'My status', 'Job ID'],
    settingsHeader: ['Setting', 'Your answer', 'Help', 'key'],
    cvTab: 'Your CV goes into cell A3 (the setup window puts it there for you). Plain text is fine.',
    start: [
      '🔎 JobFinder: your free daily job search helper',
      'Every morning it searches job sites, lets a free AI compare each job with your CV and wishes, and emails you the best ones with a ready-made CV.',
      'Last run: not yet',
      '🇭🇺 Magyarul? Kattints a „Magyar” linkre a beállító ablak tetején, vagy a „Settings” fülön a „Language / Nyelv” sorban válaszd a „Magyar” lehetőséget.',
      'FIRST TIME (about 10 minutes):',
      '1. Click the menu "🔎 JobFinder" at the top of the page (next to "Help") and choose "▶ Setup". No menu? Reload this page and wait a few seconds.',
      '2. Google asks for permission. Pick your account. If you see "Google hasn\'t verified this app", click "Advanced", then "Go to JobFinder (unsafe)", then "Allow". This is safe: the program lives in your own copy of this sheet and only you run it.',
      '3. A setup window opens. Answer the 5 short questions and click "Save and start".',
      '4. Click "Find jobs now" in that window to try it. It takes a few minutes.',
      '',
      'EVERY DAY: nothing to do. Around 7:00 each morning it searches by itself and emails you when it finds good jobs.',
      'New jobs appear at the top of the "Jobs" tab (bottom of the screen). Use the "My status" column to keep track of where you applied.',
      'Your tailored CVs are saved in Google Drive, in the folder "JobFinder CVs".',
      '',
      'CHANGE SOMETHING? Run "🔎 JobFinder" > "▶ Setup" again, or change the yellow cells in the "Settings" tab (more options there).',
      'Too many bad matches? Add words to "Skip jobs with these words in the title", or raise "Great match from score".',
      'Nothing found? Add more job titles, tick more job sites, or set "Look at jobs posted in the last" to "month".',
      'To pause: "🔎 JobFinder" > "Stop daily search". To start again: run "▶ Setup" and click "Save and start".',
      'Everything here is free. Do not share this sheet: it contains your CV.',
    ],
    msg: {
      searching: 'Searching... this can take up to 5 minutes.',
      stopped: 'Daily search stopped. To start again: 🔎 JobFinder > ▶ Setup > Save and start.',
      lastRun: 'Last run: ',
      langChanged: 'Language changed. Reload the page to update the menu too.',
      dialogTitle: '🔎 JobFinder setup',
    },
    err: {
      noKey: 'No AI key yet. Click 🔎 JobFinder > ▶ Setup.',
      noName: 'Fill in your full name: 🔎 JobFinder > ▶ Setup.',
      noTitles: 'Type at least one job title: 🔎 JobFinder > ▶ Setup.',
      noCv: 'Your CV is empty: 🔎 JobFinder > ▶ Setup.',
      noSite: 'No job site is ticked. Tick at least one: 🔎 JobFinder > ▶ Setup.',
      wKey: 'Please paste your free AI key (step 1).',
      wName: 'Please fill in your full name (step 2).',
      wTitles: 'Please type at least one job title (step 3).',
      wSite: 'Please tick at least one job site (step 4).',
      wJooble: 'Jooble needs a free key (step 4), or untick Jooble.',
      wCv: 'Please paste your CV (step 5).',
      siteDown: code => `the site did not answer (error ${code}), will try again next time`,
      joobleMissing: 'needs a free Jooble key (🔎 JobFinder > ▶ Setup, step 4)',
      keyBad: 'Your AI key does not work. Copy it again from aistudio.google.com/apikey and paste it in 🔎 JobFinder > ▶ Setup.',
      model: m => `The AI model "${m}" was not found. Fix "AI model" at the bottom of the Settings tab.`,
      aiError: 'The AI returned an error: ',
      aiBusy: 'The AI is busy or the free limit for today is used up. JobFinder will continue next time.',
      aiEmpty: 'The AI gave an empty answer.',
      cvFailed: 'CV could not be made: ',
    },
    run: {
      noNew: n => `No new jobs today (${n} found, all already seen or filtered out).`,
      checked: (n, g, m) => `Checked ${n} new job(s): ${g} great, ${m} maybe.`,
      left: n => ` ${n} more will be checked next time.`,
      stoppedEarly: ' Stopped early: ',
      couldNot: 'Could not search ',
    },
    rule: {
      remoteOnly: mode => `${mode} job, but you want remote only`,
      officeOnly: 'Office-only job',
      tooMany: (o, m) => `${o} office days a week (your limit is ${m})`,
      wish: 'Goes against one of your wishes',
      checkDays: '⚠️ Check how many office days they expect',
    },
    mail: {
      subject: (g, m) => `JobFinder: ${g} great match(es), ${m} maybe`,
      great: '⭐ Great matches', maybe: '🤔 Maybe', at: ' at ', foundOn: 'found on ', score: 'Score',
      openCv: 'Open your tailored CV', attached: '(PDF attached)', seeAll: 'See all jobs in your JobFinder sheet',
      openAd: 'Open job ad', cvLink: 'Open CV',
    },
    docs: { cv: 'CV - ', letter: 'Cover letter - ', folder: 'JobFinder CVs' },
    wiz: {
      k1Title: '1. Your free AI key',
      k1Hint: 'The AI reads the job ads for you. Getting the key is free and takes 2 minutes: click the button, sign in with Google, click "Create API key", copy the key, and paste it below.',
      k1Button: '👉 Get my free AI key (opens a new tab)',
      keyPh: 'Paste your AI key here',
      k2Title: '2. About you',
      name: 'Full name', email: 'Email', emailHint: '(job alerts are sent here)',
      phone: 'Phone', phoneHint: '(optional, printed on your CV)', city: 'City', cityHint: '(printed on your CV)',
      k3Title: '3. What job are you looking for?',
      titles: 'Job titles', titlesHint: '(separate with commas, e.g. "Receptionist, Office assistant, Customer service")',
      where: 'Where', whereHint: '(city and country, e.g. "Budapest, Hungary")',
      workplace: 'Work from', maxOffice: 'Most office days per week', maxOfficeHint: '(only matters for hybrid jobs)',
      k4Title: '4. Which job sites to search', k4Hint: 'Tick as many as you like.',
      jooble: 'Jooble key', joobleHint: 'Free: fill in the short form on this page and Jooble emails you a key:',
      k5Title: '5. Your CV',
      k5Hint: 'Open your CV (Word or PDF), select everything (Ctrl+A), copy (Ctrl+C), then click in the box below and paste (Ctrl+V).',
      save: '✅ Save and start',
      more: 'More options (salary, words to avoid, CV language, cover letters...) are in the "Settings" tab. You can open this window again any time: 🔎 JobFinder > ▶ Setup.',
    },
    js: {
      keySaved: 'Already saved. Leave empty to keep it.',
      saving: '⏳ Checking and saving... (a few seconds)',
      saved: '✅ Saved! JobFinder will now search every morning around 7:00 and email you good jobs.',
      tryBtn: '🔎 Find jobs now',
      searching: '⏳ Searching... please keep this window open. It takes up to 5 minutes.',
      seeJobs: 'Close this window and open the "Jobs" tab (bottom of the screen) to see them.',
      switching: '⏳ One moment...',
    },
  },

  hu: {
    tabs: { start: 'Kezdés', settings: 'Beállítások', cv: 'Önéletrajzom', jobs: 'Állások' },
    menu: { setup: '▶ Beállítás (kezdd itt)', findNow: 'Állások keresése most', stop: 'Napi keresés leállítása' },
    opt: {
      lang: { en: 'English', hu: 'Magyar' },
      workplace: { remote: 'Csak otthonról', hybrid: 'Otthonról vagy hibrid', any: 'Bármilyen (otthoni, hibrid vagy irodai)' },
      level: { entry: 'Pályakezdő / junior', mid: 'Tapasztalt (medior)', senior: 'Szenior', any: 'Bármilyen' },
      coverLetter: { asked: 'Csak ha a hirdetés kéri', always: 'Mindig', never: 'Soha' },
      since: { day: '1 nap', week: '1 hét', month: '1 hónap' },
      langs: {
        English: 'Angol', Hungarian: 'Magyar', German: 'Német', Polish: 'Lengyel', Romanian: 'Román', Slovak: 'Szlovák',
        Czech: 'Cseh', Spanish: 'Spanyol', French: 'Francia', Italian: 'Olasz', Dutch: 'Holland', Portuguese: 'Portugál',
      },
    },
    sameAsAd: 'A hirdetés nyelvén',
    modes: { Remote: 'Otthoni', Hybrid: 'Hibrid', Onsite: 'Irodai', Unknown: 'Nem derül ki' },
    verdict: { great: '⭐ Nagyon jó', maybe: '🤔 Talán', low: '▫️ Gyenge', skip: '⛔ Kihagyva' },
    status: ['Új', 'Jelentkeztem', 'Interjú', 'Ajánlat', 'Elutasítva', 'Nem érdekel'],
    jobHeaders: ['Dátum', 'Pontszám', 'Értékelés', 'Munkakör', 'Cég', 'Helyszín', 'Oldal', 'Munkavégzés', 'Miért (MI összefoglaló)', 'Hirdetés', 'Igazított önéletrajz', 'Státuszom', 'Állás azonosító'],
    settingsHeader: ['Beállítás', 'Válaszod', 'Segítség', 'key'],
    cvTab: 'Az önéletrajzod az A3-as cellába kerül (a beállító ablak teszi ide). Sima szöveg is jó.',
    start: [
      '🔎 JobFinder: ingyenes napi álláskereső segéd',
      'Minden reggel átnézi az állásportálokat, egy ingyenes mesterséges intelligencia (MI) összeveti a hirdetéseket az önéletrajzoddal és a kívánságaiddal, és e-mailben elküldi a legjobbakat egy hozzájuk igazított önéletrajzzal.',
      'Utolsó futás: még nem volt',
      '🇬🇧 In English? Click "English" at the top of the setup window, or in the "Beállítások" tab set "Nyelv / Language" to "English".',
      'ELSŐ ALKALOMMAL (kb. 10 perc):',
      '1. Kattints fent a „🔎 JobFinder” menüre (a „Súgó” mellett), és válaszd a „▶ Beállítás” pontot. Nincs ilyen menü? Töltsd újra az oldalt, és várj néhány másodpercet.',
      '2. A Google engedélyt kér. Válaszd ki a fiókodat. Ha azt írja, hogy a Google nem ellenőrizte az alkalmazást, kattints a „Speciális” (Advanced) linkre, majd a „JobFinder megnyitása (nem biztonságos)” linkre, végül az „Engedélyezés” (Allow) gombra. Ez biztonságos: a program a táblázatod saját példányában van, és csak te futtatod.',
      '3. Megnyílik egy beállító ablak. Válaszolj az 5 rövid kérdésre, és kattints a „Mentés és indítás” gombra.',
      '4. Próbáld ki: kattints az ablakban az „Állások keresése most” gombra. Néhány percig tart.',
      '',
      'MINDEN NAP: nincs teendőd. Reggel 7 óra körül magától keres, és e-mailt küld, ha jó állást talál.',
      'Az új állások az „Állások” fül tetején jelennek meg (a füleket a képernyő alján találod). A „Státuszom” oszlopban követheted, hova jelentkeztél.',
      'A hozzád igazított önéletrajzokat a Google Drive-ban, a „JobFinder önéletrajzok” mappában találod.',
      '',
      'VÁLTOZTATNÁL? Futtasd újra: „🔎 JobFinder” > „▶ Beállítás”, vagy írd át a sárga cellákat a „Beállítások” fülön (ott több lehetőség is van).',
      'Túl sok rossz találat? Írj több szót az „Ezeket a szavakat tartalmazó állások kihagyása” sorba, vagy emeld a „Nagyon jó találat ettől a pontszámtól” értéket.',
      'Nincs találat? Adj meg több munkakört, jelölj be több állásportált, vagy az „Ennyi időn belül feladott állások” sorban válaszd az „1 hónap” lehetőséget.',
      'Szüneteltetés: „🔎 JobFinder” > „Napi keresés leállítása”. Újraindítás: „▶ Beállítás”, majd „Mentés és indítás”.',
      'Minden teljesen ingyenes. Ne oszd meg ezt a táblázatot, mert benne van az önéletrajzod.',
    ],
    msg: {
      searching: 'Keresés... akár 5 percig is tarthat.',
      stopped: 'A napi keresés leállt. Újraindítás: 🔎 JobFinder > ▶ Beállítás > Mentés és indítás.',
      lastRun: 'Utolsó futás: ',
      langChanged: 'Nyelv átállítva. Töltsd újra az oldalt, hogy a menü is magyar legyen.',
      dialogTitle: '🔎 JobFinder beállítás',
    },
    err: {
      noKey: 'Még nincs MI-kulcs. Kattints: 🔎 JobFinder > ▶ Beállítás.',
      noName: 'Add meg a teljes neved: 🔎 JobFinder > ▶ Beállítás.',
      noTitles: 'Adj meg legalább egy munkakört: 🔎 JobFinder > ▶ Beállítás.',
      noCv: 'Üres az önéletrajzod: 🔎 JobFinder > ▶ Beállítás.',
      noSite: 'Egy állásportál sincs bejelölve. Jelölj be legalább egyet: 🔎 JobFinder > ▶ Beállítás.',
      wKey: 'Másold be az ingyenes MI-kulcsodat (1. lépés).',
      wName: 'Add meg a teljes neved (2. lépés).',
      wTitles: 'Adj meg legalább egy munkakört (3. lépés).',
      wSite: 'Jelölj be legalább egy állásportált (4. lépés).',
      wJooble: 'A Jooble-höz ingyenes kulcs kell (4. lépés), vagy vedd ki a pipát a Jooble elől.',
      wCv: 'Másold be az önéletrajzodat (5. lépés).',
      siteDown: code => `az oldal nem válaszolt (hibakód: ${code}), legközelebb újra próbálja`,
      joobleMissing: 'ingyenes Jooble kulcs kell hozzá (🔎 JobFinder > ▶ Beállítás, 4. lépés)',
      keyBad: 'Az MI-kulcsod nem működik. Másold ki újra az aistudio.google.com/apikey oldalról, és illeszd be: 🔎 JobFinder > ▶ Beállítás.',
      model: m => `Nem található a(z) „${m}” MI-modell. Javítsd az „MI-modell” sort a Beállítások fül alján.`,
      aiError: 'Az MI hibát jelzett: ',
      aiBusy: 'Az MI most foglalt, vagy elfogyott a mai ingyenes keret. A JobFinder legközelebb folytatja.',
      aiEmpty: 'Az MI üres választ adott.',
      cvFailed: 'Nem sikerült önéletrajzot készíteni: ',
    },
    run: {
      noNew: n => `Ma nincs új állás (${n} találat, mind ismert vagy kiszűrve).`,
      checked: (n, g, m) => `${n} új állás átnézve: ${g} nagyon jó, ${m} talán.`,
      left: n => ` További ${n} legközelebb kerül sorra.`,
      stoppedEarly: ' Korábban leállt: ',
      couldNot: 'Nem sikerült keresni: ',
    },
    rule: {
      remoteOnly: mode => `${mode} munka, de te csak otthonról dolgoznál`,
      officeOnly: 'Csak irodai munka',
      tooMany: (o, m) => `Heti ${o} irodai nap (a határod ${m})`,
      wish: 'Ellentmond valamelyik kívánságodnak',
      checkDays: '⚠️ Nézd meg, hány irodai napot várnak',
    },
    mail: {
      subject: (g, m) => `JobFinder: ${g} nagyon jó, ${m} talán`,
      great: '⭐ Nagyon jó találatok', maybe: '🤔 Talán', at: ' – ', foundOn: 'forrás: ', score: 'Pontszám',
      openCv: 'Igazított önéletrajz megnyitása', attached: '(PDF csatolva)', seeAll: 'Az összes állás a JobFinder táblázatodban',
      openAd: 'Hirdetés megnyitása', cvLink: 'Önéletrajz',
    },
    docs: { cv: 'Önéletrajz - ', letter: 'Motivációs levél - ', folder: 'JobFinder önéletrajzok' },
    wiz: {
      k1Title: '1. Ingyenes MI-kulcsod',
      k1Hint: 'Az MI (mesterséges intelligencia) olvassa el helyetted a hirdetéseket. A kulcs ingyenes, és 2 perc alatt megvan: kattints a gombra, jelentkezz be a Google-fiókoddal, kattints a „Create API key” gombra, másold ki a kulcsot, és illeszd be lent.',
      k1Button: '👉 Ingyenes MI-kulcs kérése (új lapon nyílik meg)',
      keyPh: 'Ide illeszd be az MI-kulcsot',
      k2Title: '2. Rólad',
      name: 'Teljes név', email: 'E-mail cím', emailHint: '(ide jönnek az állásértesítők)',
      phone: 'Telefonszám', phoneHint: '(nem kötelező, az önéletrajzra kerül)', city: 'Város', cityHint: '(az önéletrajzra kerül)',
      k3Title: '3. Milyen munkát keresel?',
      titles: 'Munkakörök', titlesHint: '(vesszővel elválasztva, pl. „Recepciós, Irodai asszisztens, Ügyfélszolgálati munkatárs”)',
      where: 'Hol', whereHint: '(város és ország angolul, pl. „Budapest, Hungary”)',
      workplace: 'Munkavégzés helye', maxOffice: 'Legfeljebb ennyi irodai nap hetente', maxOfficeHint: '(csak hibrid állásoknál számít)',
      k4Title: '4. Melyik állásportálokon keressen', k4Hint: 'Annyit jelölj be, amennyit szeretnél.',
      jooble: 'Jooble kulcs', joobleHint: 'Ingyenes: töltsd ki a rövid űrlapot ezen az oldalon, és a Jooble e-mailben küld egy kulcsot:',
      k5Title: '5. Önéletrajzod',
      k5Hint: 'Nyisd meg az önéletrajzodat (Word vagy PDF), jelölj ki mindent (Ctrl+A), másold ki (Ctrl+C), majd kattints a lenti mezőbe, és illeszd be (Ctrl+V).',
      save: '✅ Mentés és indítás',
      more: 'További lehetőségek (fizetés, kerülendő szavak, önéletrajz nyelve, motivációs levél...) a „Beállítások” fülön vannak. Ezt az ablakot bármikor újra megnyithatod: 🔎 JobFinder > ▶ Beállítás.',
    },
    js: {
      keySaved: 'Már elmentve. Hagyd üresen, ha nem változtatsz rajta.',
      saving: '⏳ Ellenőrzés és mentés... (pár másodperc)',
      saved: '✅ Elmentve! A JobFinder mostantól minden reggel 7 óra körül keres, és e-mailben küldi a jó állásokat.',
      tryBtn: '🔎 Állások keresése most',
      searching: '⏳ Keresés... hagyd nyitva ezt az ablakot. Akár 5 percig is tarthat.',
      seeJobs: 'Zárd be ezt az ablakot, és nyisd meg az „Állások” fület (a képernyő alján).',
      switching: '⏳ Egy pillanat...',
    },
  },
};
Object.keys(TEXT).forEach(l => { TEXT[l].opt.cvLangs = Object.assign({ same: TEXT[l].sameAsAd }, TEXT[l].opt.langs); });

// ---------- Job sites ----------
// To add a site, add one entry here: search(settings, titles) returns jobs, details(job) returns the job ad text.
// It then shows up automatically as a tick box in the Settings tab and in the setup window.
const SITES = {
  'LinkedIn': {
    on: true, search: linkedinSearch_, details: linkedinDetails_,
    note: { en: 'Worldwide. No account needed.', hu: 'Világszerte. Nem kell hozzá fiók.' },
  },
  'Profession.hu': {
    on: true, search: professionSearch_, details: professionDetails_,
    note: { en: 'The biggest job site in Hungary.', hu: 'Magyarország legnagyobb állásportálja.' },
  },
  'NoFluffJobs': {
    on: false, search: nfjSearch_, details: nfjDetails_,
    note: { en: 'Office and IT jobs in Hungary, Poland, Czechia and Slovakia.', hu: 'Irodai és IT állások Magyarországon, Lengyelországban, Csehországban és Szlovákiában.' },
  },
  'Jooble': {
    on: false, search: joobleSearch_, details: job => job.snippet,
    note: { en: 'Collects jobs from many sites, worldwide. Needs a free Jooble key.', hu: 'Sok oldal állásait gyűjti össze, világszerte. Ingyenes Jooble kulcs kell hozzá.' },
  },
};

// ---------- Settings tab ----------
// Column A shows the label, column D (hidden) holds the key the script uses, so switching language keeps every answer.
const SETTINGS = [
  { key: 'lang', opts: 'lang', def: { en: 'en', hu: 'hu' },
    label: { en: 'Language / Nyelv', hu: 'Nyelv / Language' },
    help: { en: 'Choose "Magyar" for Hungarian. The sheet changes after a few seconds.', hu: 'Angolhoz válaszd az „English” lehetőséget. Pár másodperc múlva átvált a táblázat.' } },
  { key: 'name', def: '', label: { en: 'Your full name', hu: 'Teljes neved' },
    help: { en: 'As it should appear on your CV.', hu: 'Ahogy az önéletrajzodon szerepeljen.' } },
  { key: 'email', def: '', label: { en: 'Your email', hu: 'E-mail címed' },
    help: { en: 'Job alerts are sent here. Also printed on your CV.', hu: 'Ide érkeznek az állásértesítők. Az önéletrajzodra is rákerül.' } },
  { key: 'phone', def: '', label: { en: 'Your phone number (optional)', hu: 'Telefonszámod (nem kötelező)' },
    help: { en: 'Printed on your CV.', hu: 'Az önéletrajzodra kerül.' } },
  { key: 'city', def: '', label: { en: 'Your city', hu: 'Városod' },
    help: { en: 'Printed on your CV, e.g. "Budapest, Hungary".', hu: 'Az önéletrajzodra kerül, pl. „Budapest”.' } },
  { key: 'linkedin', def: '', label: { en: 'Your LinkedIn link (optional)', hu: 'LinkedIn profilod linkje (nem kötelező)' },
    help: { en: 'Printed on your CV.', hu: 'Az önéletrajzodra kerül.' } },
  { key: 'myLanguage', opts: 'langs', free: true, def: { en: 'English', hu: 'Hungarian' },
    label: { en: 'Language for summaries and emails', hu: 'Az összefoglalók és e-mailek nyelve' },
    help: { en: 'Pick one, or type another language.', hu: 'Válassz egyet, vagy írj be másik nyelvet.' } },
  { key: 'titles', def: { en: 'Customer Service, Office Administrator', hu: 'Ügyfélszolgálati munkatárs, Irodai asszisztens' },
    label: { en: 'Job titles to search for', hu: 'Keresett munkakörök' },
    help: { en: 'Separate with commas. Each one is a separate search; 3 to 6 works best.', hu: 'Vesszővel elválasztva. Mindegyik külön keresés; 3-6 a legjobb.' } },
  { key: 'where', def: 'Budapest, Hungary', label: { en: 'Where', hu: 'Hol' },
    help: { en: 'A city and country, e.g. "Budapest, Hungary".', hu: 'Város és ország angolul, pl. „Budapest, Hungary”.' } },
  { key: 'workplace', opts: 'workplace', def: 'hybrid', label: { en: 'Work from', hu: 'Munkavégzés helye' },
    help: { en: 'Where you are willing to work.', hu: 'Hol vállalsz munkát.' } },
  { key: 'maxOffice', list: ['0', '1', '2', '3', '4', '5'], def: 2,
    label: { en: 'Most office days per week', hu: 'Legfeljebb ennyi irodai nap hetente' },
    help: { en: 'For hybrid jobs. Jobs asking for more are skipped.', hu: 'Hibrid állásoknál. Ha ennél többet kérnek, kihagyja.' } },
].concat(Object.keys(SITES).map(n => (
  { key: 'site:' + n, checkbox: true, def: SITES[n].on, label: { en: 'Search ' + n, hu: 'Keresés itt: ' + n }, help: SITES[n].note }
)), [
  { key: 'level', opts: 'level', def: 'any', label: { en: 'Experience level', hu: 'Tapasztalati szint' },
    help: { en: 'Used by LinkedIn and by the AI.', hu: 'A LinkedIn és az MI is figyelembe veszi.' } },
  { key: 'salary', def: '', label: { en: 'Minimum salary (optional)', hu: 'Minimális fizetés (nem kötelező)' },
    help: { en: 'In your own words, e.g. "600 000 HUF gross per month". The AI uses it when scoring.', hu: 'Saját szavaiddal, pl. „bruttó 600 000 Ft havonta”. Az MI a pontozásnál figyelembe veszi.' } },
  { key: 'avoidTitle', def: { en: 'intern, trainee', hu: 'gyakornok, diákmunka, intern, trainee' },
    label: { en: 'Skip jobs with these words in the title', hu: 'Ezeket a szavakat tartalmazó állások kihagyása' },
    help: { en: 'Separate with commas. These jobs are dropped before the AI even looks at them.', hu: 'Vesszővel elválasztva. Ezeket az állásokat az MI meg sem nézi.' } },
  { key: 'avoid', def: { en: 'gambling, crypto', hu: 'szerencsejáték, kaszinó, kripto, gambling, crypto' },
    label: { en: 'Companies or industries to avoid', hu: 'Kerülendő cégek vagy iparágak' },
    help: { en: 'Separate with commas, e.g. a company name, "call center", "betting".', hu: 'Vesszővel elválasztva, pl. egy cégnév, „call center”, „fogadás”.' } },
  { key: 'wishes', def: '', label: { en: 'Anything else important to you', hu: 'Ami még fontos neked' },
    help: { en: 'Plain words, e.g. "no night shifts, I do not speak German, permanent contract only".', hu: 'Egyszerű szavakkal, pl. „nincs éjszakai műszak, nem beszélek németül, csak határozatlan idejű szerződés”.' } },
  { key: 'since', opts: 'since', def: 'week', label: { en: 'Look at jobs posted in the last', hu: 'Ennyi időn belül feladott állások' },
    help: { en: 'Choose "month" if you get too few jobs.', hu: 'Válaszd az „1 hónap” lehetőséget, ha túl kevés állást találsz.' } },
  { key: 'strongScore', list: ['50', '55', '60', '65', '70', '75', '80', '85', '90'], def: 70,
    label: { en: 'Great match from score', hu: 'Nagyon jó találat ettől a pontszámtól' },
    help: { en: 'Great matches get a tailored CV and an email. Raise it if you get too many.', hu: 'A nagyon jó találatokhoz önéletrajz készül és e-mail jön. Emeld meg, ha túl sok jön.' } },
  { key: 'maybeScore', list: ['30', '35', '40', '45', '50', '55', '60', '65', '70'], def: 50,
    label: { en: 'Maybe from score', hu: '„Talán” ettől a pontszámtól' },
    help: { en: 'Maybe matches are listed in the email, without a CV.', hu: 'A „talán” találatok is benne lesznek az e-mailben, de önéletrajz nélkül.' } },
  { key: 'makeCv', checkbox: true, def: true,
    label: { en: 'Make a tailored CV for great matches', hu: 'Igazított önéletrajz a nagyon jó találatokhoz' },
    help: { en: 'Saved in Google Drive (folder "JobFinder CVs") and attached to the email as a PDF.', hu: 'A Google Drive-ba menti („JobFinder önéletrajzok” mappa), és PDF-ként csatolja az e-mailhez.' } },
  { key: 'cvLanguage', opts: 'cvLangs', free: true, def: 'same', label: { en: 'CV language', hu: 'Az önéletrajz nyelve' },
    help: { en: 'Pick one, or type another language.', hu: 'Válassz egyet, vagy írj be másik nyelvet.' } },
  { key: 'coverLetter', opts: 'coverLetter', def: 'asked', label: { en: 'Write a cover letter', hu: 'Motivációs levél írása' },
    help: { en: '', hu: '' } },
  { key: 'maxJobs', list: ['5', '10', '15', '20'], def: 10,
    label: { en: 'Most new jobs to check per day', hu: 'Naponta legfeljebb ennyi új állás átnézése' },
    help: { en: 'Google allows about 10 per run; extra ones are checked the next day.', hu: 'A Google futásonként kb. 10-et enged; a többit másnap nézi meg.' } },
  { key: 'model', def: 'gemini-3.5-flash-lite', label: { en: 'AI model (advanced: leave as is)', hu: 'MI-modell (haladó: hagyd így)' },
    help: { en: 'Only change this if an error message tells you to.', hu: 'Csak akkor változtasd, ha egy hibaüzenet erre kér.' } },
]);

// ---------- Language ----------

let LANG_CACHE = null;

// The "Language / Nyelv" setting wins; before it exists, a Hungarian spreadsheet locale means Hungarian.
function lang_() {
  if (LANG_CACHE) return LANG_CACHE;
  let l = 'en';
  try {
    const v = settingsRaw_().lang;
    l = v ? toKey_(SETTINGS[0], v) : (/^hu/i.test(SpreadsheetApp.getActive().getSpreadsheetLocale()) ? 'hu' : 'en');
  } catch (e) { /* not inside a sheet (tests) */ }
  return (LANG_CACHE = TEXT[l] ? l : 'en');
}

function tr_() { return TEXT[lang_()]; }

// Shown text (in any language) or key -> key. Free text the user typed stays as it is.
function toKey_(d, v) {
  if (!d.opts) return v;
  const want = String(v).trim().toLowerCase();
  for (const l of Object.keys(TEXT)) {
    const o = TEXT[l].opt[d.opts];
    const k = Object.keys(o).find(k => k.toLowerCase() === want || String(o[k]).toLowerCase() === want);
    if (k) return k;
  }
  return v;
}

function display_(d, v, l) {
  if (!d.opts || v === '') return v;
  const label = TEXT[l].opt[d.opts][toKey_(d, v)];
  return label === undefined ? v : label;
}

function def_(d, l) { return d.def !== null && typeof d.def === 'object' ? d.def[l] : d.def; }

// Called from the language links at the top of the setup window.
function setLanguage(l) {
  writeSetting_('lang', l);
  LANG_CACHE = null;
  setup();
}

// Changing "Language / Nyelv" in the Settings tab translates the whole sheet straight away.
function onEdit(e) {
  const sh = e.range.getSheet();
  if (e.range.getColumn() !== 2 || !Object.keys(TEXT).some(l => TEXT[l].tabs.settings === sh.getName())) return;
  if (sh.getRange(e.range.getRow(), 4).getValue() !== 'lang') return;
  LANG_CACHE = null;
  buildSheet_();
  SpreadsheetApp.getActive().toast(tr_().msg.langChanged, 'JobFinder', 10);
}

// ---------- Menu ----------

function onOpen() {
  try { buildSheet_(); } catch (e) { console.warn(e); }
  const M = tr_().menu;
  SpreadsheetApp.getUi().createMenu('🔎 JobFinder')
    .addItem(M.setup, 'setup')
    .addItem(M.findNow, 'findJobsNow')
    .addSeparator()
    .addItem(M.stop, 'stopDaily')
    .addToUi();
}

function setup() {
  buildSheet_();
  const l = lang_(), L = TEXT[l], s = readSettings_();
  const props = PropertiesService.getUserProperties();
  const data = {
    lang: l,
    t: L.js,
    values: Object.assign({}, s, { email: s.email || Session.getEffectiveUser().getEmail(), cv: readCv_() }),
    hasKey: Boolean(props.getProperty('GEMINI_KEY')),
    hasJoobleKey: Boolean(props.getProperty('JOOBLE_KEY')),
    workplaces: Object.keys(L.opt.workplace).map(k => ({ key: k, label: L.opt.workplace[k] })),
    sites: Object.keys(SITES).map(name => ({ name, note: SITES[name].note[l], on: yes_(s['site:' + name]) })),
  };
  SpreadsheetApp.getUi().showModalDialog(HtmlService.createHtmlOutput(wizardHtml_(data, L)).setWidth(660).setHeight(760), L.msg.dialogTitle);
}

function wizardHtml_(data, L) {
  const esc = t => String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const json = JSON.stringify(data).replace(/</g, '\\u003c');
  // function form: a "$" in a CV must not be read as a replacement pattern
  return WIZARD_HTML.replace(/\{\{(\w+)\}\}/g, (m, k) => esc(L.wiz[k])).replace('__DATA__', () => json);
}

// Called by the setup window.
function saveWizard(f) {
  buildSheet_();
  const E = tr_().err;
  const props = PropertiesService.getUserProperties();
  if (!f.key && !props.getProperty('GEMINI_KEY')) throw new Error(E.wKey);
  if (!f.name) throw new Error(E.wName);
  if (!f.titles) throw new Error(E.wTitles);
  if (!Object.keys(f.sites).some(n => f.sites[n])) throw new Error(E.wSite);
  if (f.sites.Jooble && !f.joobleKey && !props.getProperty('JOOBLE_KEY')) throw new Error(E.wJooble);
  if (!f.cv) throw new Error(E.wCv);
  if (f.key) {
    gemini_(f.key, readSettings_().model, 'Reply with ok=true.', 'Test', obj_({ ok: BOOL }), 0);
    props.setProperty('GEMINI_KEY', f.key);
  }
  if (f.joobleKey) props.setProperty('JOOBLE_KEY', f.joobleKey);
  ['name', 'email', 'phone', 'city', 'titles', 'where', 'workplace', 'maxOffice'].forEach(k => writeSetting_(k, f[k]));
  Object.keys(SITES).forEach(n => writeSetting_('site:' + n, Boolean(f.sites[n])));
  const cvSheet = sheetById_('cv');
  cvSheet.getRange('A3:A').clearContent();
  cvSheet.getRange('A3').setValue(f.cv);
  installDaily_();
}

function stopDaily() {
  ScriptApp.getProjectTriggers().filter(t => t.getHandlerFunction() === 'findJobs').forEach(t => ScriptApp.deleteTrigger(t));
  SpreadsheetApp.getUi().alert(tr_().msg.stopped);
}

function findJobsNow() {
  SpreadsheetApp.getActive().toast(tr_().msg.searching, 'JobFinder', 15);
  SpreadsheetApp.getUi().alert(findJobs());
}

// Runs every morning (installed by setup), from the menu and from the setup window.
function findJobs() {
  let msg;
  try { msg = run_(Date.now()); } catch (e) { msg = '⚠️ ' + e.message; }
  sheetById_('start').getRange('A3')
    .setValue(tr_().msg.lastRun + Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm') + ': ' + msg);
  return msg;
}

// ---------- Main flow ----------

function run_(started) {
  const L = tr_();
  const s = readSettings_();
  const cv = readCv_();
  const key = getKey_();
  s.joobleKey = PropertiesService.getUserProperties().getProperty('JOOBLE_KEY') || '';
  if (!key) throw new Error(L.err.noKey);
  if (!s.name) throw new Error(L.err.noName);
  if (!list_(s.titles).length) throw new Error(L.err.noTitles);
  if (!cv) throw new Error(L.err.noCv);

  const sheet = sheetById_('jobs');
  const seen = new Set(sheet.getRange(2, COL_ID, Math.max(sheet.getLastRow() - 1, 1), 1).getValues().map(r => String(r[0])).filter(Boolean));
  const found = searchAll_(s);
  const problems = found.problems.length ? ` (${L.run.couldNot}${found.problems.join('; ')})` : '';
  const fresh = interleave_(prefilter_(found.jobs, seen, s)).slice(0, Number(s.maxJobs) || 10);
  if (!fresh.length) return L.run.noNew(found.jobs.length) + problems;

  const great = [], maybe = [];
  let checked = 0, stopReason = '';
  for (const job of fresh) {
    if (Date.now() - started > BUDGET_MS) break;
    let r;
    try {
      job.description = describe_(job);
      Utilities.sleep(4000); // stay under the free AI limit (about 15 requests per minute)
      r = gemini_(key, s.model, scoringPrompt_(s, cv), jobText_(job), SCORE_SCHEMA, 0.15);
    } catch (e) {
      stopReason = e.message;
      break;
    }
    job.company = job.company || r.company || '';
    job.location = job.location || r.location || '';
    const d = decide_(r, s);
    let docs = { url: '', pdfs: [] };
    if (d.verdict === 'great' && yes_(s.makeCv)) {
      try { docs = makeDocs_(key, s, cv, job, r); } catch (e) { d.note = [d.note, L.err.cvFailed + e.message].filter(Boolean).join('. '); }
    }
    addJobRow_(sheet, job, r, d, docs.url);
    checked++;
    if (d.verdict === 'great') great.push({ job, r, d, docs });
    else if (d.verdict === 'maybe') maybe.push({ job, r, d, docs });
  }
  if (great.length || maybe.length) sendEmail_(s, great, maybe);

  const left = fresh.length - checked;
  return L.run.checked(checked, great.length, maybe.length)
    + (left ? L.run.left(left) : '')
    + (stopReason ? L.run.stoppedEarly + stopReason : '')
    + problems;
}

function searchAll_(s) {
  const titles = list_(s.titles);
  const names = Object.keys(SITES).filter(n => yes_(s['site:' + n]));
  if (!names.length) throw new Error(tr_().err.noSite);
  const jobs = [], problems = [];
  names.forEach(name => {
    try {
      SITES[name].search(s, titles).forEach(j => jobs.push(Object.assign(j, { source: name })));
    } catch (e) {
      problems.push(`${name}: ${e.message}`);
    }
  });
  if (!jobs.length && problems.length) throw new Error(tr_().run.couldNot + problems.join('; '));
  return { jobs, problems };
}

function describe_(job) {
  let text = '';
  try { text = SITES[job.source].details(job) || ''; } catch (e) { /* use the title only */ }
  return (text.length > 30 ? text : `Job title: ${job.title} at ${job.company || 'unknown company'} (${job.location}). Full description not available.`).slice(0, 9000);
}

// ---------- Site: LinkedIn (public guest pages) ----------

function linkedinSearch_(s, titles) {
  const extra = { f_TPR: { day: 'r86400', week: 'r604800', month: 'r2592000' }[s.since] || 'r604800' };
  if (s.workplace === 'remote') extra.f_WT = '2';
  if (s.workplace === 'hybrid') extra.f_WT = '2,3';
  const level = { entry: '1,2', mid: '3,4', senior: '4,5' }[s.level];
  if (level) extra.f_E = level;
  const pages = fetchTexts_(titles.map(t => ({
    url: 'https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?' + query_(Object.assign({ keywords: t, location: s.where, start: '0' }, extra)),
  })));
  return [].concat(...pages.map(parseLinkedInCards_));
}

function parseLinkedInCards_(html) {
  const out = [];
  for (const part of String(html || '').split('<li')) {
    const id = part.match(/data-entity-urn="urn:li:jobPosting:(\d+)"/);
    const title = part.match(/class="base-search-card__title"[^>]*>([\s\S]*?)<\/h3>/);
    if (!id || !title) continue;
    const company = part.match(/class="base-search-card__subtitle"[^>]*>([\s\S]*?)<\/h4>/);
    const location = part.match(/class="job-search-card__location"[^>]*>([\s\S]*?)<\/span>/);
    const link = part.match(/class="base-card__full-link[^"]*"[^>]*href="([^"]+)"/);
    out.push({
      id: 'li_' + id[1], // prefix keeps Sheets from turning the id into a number
      rawId: id[1],
      title: stripHtml_(title[1]),
      company: stripHtml_(company ? company[1] : ''),
      location: stripHtml_(location ? location[1] : ''),
      url: link ? link[1].split('?')[0] : 'https://www.linkedin.com/jobs/view/' + id[1],
    });
  }
  return out.filter(j => j.title);
}

function linkedinDetails_(job) {
  const html = fetchText_('https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/' + job.rawId);
  const body = html.match(/show-more-less-html__markup[^>]*>([\s\S]*?)<\/div>/i);
  const criteria = Array.from(html.matchAll(/description__job-criteria-subheader[^>]*>([\s\S]*?)<\/h3>[\s\S]*?description__job-criteria-text[^>]*>([\s\S]*?)<\/span>/gi))
    .map(m => stripHtml_(m[1]) + ': ' + stripHtml_(m[2])).join(' | ');
  return [body ? stripHtml_(body[1]) : '', criteria].filter(Boolean).join('\n\n');
}

// ---------- Site: Profession.hu (its RSS feed; needs the cookie from the home page) ----------

function professionSearch_(s, titles) {
  const cookie = cookies_(UrlFetchApp.fetch('https://www.profession.hu/', { headers: HEADERS, muteHttpExceptions: true }));
  const feeds = fetchTexts_(titles.map(t => ({ url: 'https://www.profession.hu/allasok/1,0,0,' + encodeURIComponent(t) + '?rss', headers: { Cookie: cookie } })));
  return [].concat(...feeds.map(parseProfessionRss_)).map(j => Object.assign(j, { cookie }));
}

function parseProfessionRss_(xml) {
  return String(xml || '').split('<item>').slice(1).map(item => {
    const tag = name => { const m = item.match(new RegExp('<' + name + '>([\\s\\S]*?)</' + name + '>')); return m ? m[1].trim() : ''; };
    const url = tag('guid');
    const id = (url.match(/-(\d+)$/) || [])[1];
    const posted = new Date(tag('pubDate'));
    return id ? { id: 'prof_' + id, title: stripHtml_(tag('title')), company: '', location: '', url, posted: isNaN(posted) ? null : posted } : null;
  }).filter(Boolean);
}

function professionDetails_(job) {
  const html = fetchText_(job.url, { headers: { Cookie: job.cookie } });
  // og:title looks like "<title> állás, munka: <company>, <city>"
  const og = (html.match(/<meta property="og:title" content="([^"]*)"/) || [])[1];
  const m = og && stripHtml_(og).match(/:\s*(.+),\s*([^,]+)$/);
  if (m) { job.company = m[1].trim(); job.location = m[2].trim(); }
  return pageText_(html);
}

// ---------- Site: NoFluffJobs (public JSON API) ----------

function nfjSearch_(s, titles) {
  const pages = fetchTexts_(titles.map(t => ({
    url: 'https://nofluffjobs.com/api/search/posting?pageTo=1&pageSize=20&salaryCurrency=EUR&salaryPeriod=month&region=hu&language=en-GB',
    method: 'post', contentType: 'application/json', payload: JSON.stringify({ rawSearch: t, page: 1 }),
  })));
  return [].concat(...pages.map(p => parseNfj_(p, s)));
}

function parseNfj_(text, s) {
  const out = [];
  for (const p of JSON.parse(text).postings || []) {
    if (!p || !p.id || !p.title) continue;
    const places = (p.location && p.location.places) || [];
    const cities = places.map(x => x.city).filter(Boolean);
    const remote = Boolean(p.fullyRemote) || cities.some(c => /remote/i.test(c));
    const nearby = near_(places.map(x => [x.city, x.country && x.country.name].join(' ')).join(' '), s.where);
    if (!(remote || (nearby && s.workplace !== 'remote'))) continue;
    out.push({
      id: 'nfj_' + p.id,
      rawId: p.id,
      title: p.title.trim(),
      company: (p.name || '').trim(),
      location: [remote ? 'Remote' : ''].concat(cities.filter(c => !/remote/i.test(c)).slice(0, 3)).filter(Boolean).join(', '),
      url: 'https://nofluffjobs.com/job/' + (p.url || p.id),
      posted: p.posted ? new Date(p.posted) : null,
    });
  }
  return out;
}

function nfjDetails_(job) {
  const p = JSON.parse(fetchText_('https://nofluffjobs.com/api/posting/' + encodeURIComponent(job.rawId)) || '{}');
  const req = p.requirements || {};
  const values = list => (list || []).map(x => x.value).filter(Boolean).join(', ');
  return [
    p.details && stripHtml_(p.details.description),
    values(req.musts) && 'Must have: ' + values(req.musts),
    values(req.nices) && 'Nice to have: ' + values(req.nices),
    req.description && stripHtml_(req.description),
    p.specs && p.specs.dailyTasks && 'Daily tasks:\n• ' + p.specs.dailyTasks.map(stripHtml_).join('\n• '),
  ].filter(Boolean).join('\n\n');
}

// ---------- Site: Jooble (official free API; key from jooble.org/api/about) ----------

function joobleSearch_(s, titles) {
  if (!s.joobleKey) throw new Error(tr_().err.joobleMissing);
  const pages = fetchTexts_(titles.map(t => ({
    url: 'https://jooble.org/api/' + encodeURIComponent(s.joobleKey),
    method: 'post', contentType: 'application/json', payload: JSON.stringify({ keywords: t, location: s.where }),
  })));
  return [].concat(...pages.map(parseJooble_));
}

function parseJooble_(text) {
  return (JSON.parse(text).jobs || []).filter(j => j.id && j.title).map(j => {
    const posted = new Date(j.updated);
    return {
      id: 'jb_' + j.id,
      title: stripHtml_(j.title),
      company: j.company || '',
      location: j.location || '',
      url: j.link,
      posted: isNaN(posted) ? null : posted,
      snippet: [stripHtml_(j.snippet), j.salary && 'Salary: ' + j.salary, j.type].filter(Boolean).join('\n'),
    };
  });
}

// ---------- Web helpers ----------

function fetchTexts_(requests) {
  const responses = UrlFetchApp.fetchAll(requests.map(r => Object.assign({ muteHttpExceptions: true }, r, { headers: Object.assign({}, HEADERS, r.headers) })));
  const ok = responses.filter(r => r.getResponseCode() === 200);
  if (responses.length && !ok.length) throw new Error(tr_().err.siteDown(responses[0].getResponseCode()));
  return ok.map(r => r.getContentText());
}

function fetchText_(url, options) {
  try {
    const res = UrlFetchApp.fetch(url, Object.assign({ muteHttpExceptions: true }, options, { headers: Object.assign({}, HEADERS, options && options.headers) }));
    return res.getResponseCode() === 200 ? res.getContentText() : '';
  } catch (e) {
    return '';
  }
}

function cookies_(res) {
  return [].concat(res.getAllHeaders()['Set-Cookie'] || []).map(c => c.split(';')[0]).join('; ');
}

function query_(params) {
  return Object.keys(params).map(k => k + '=' + encodeURIComponent(params[k])).join('&');
}

function pageText_(html) {
  const start = html.search(/<main[\s>]/i), end = html.search(/<footer[\s>]/i);
  const part = html.slice(Math.max(0, start), end > start ? end : undefined);
  return stripHtml_(part.replace(/<(script|style|svg|noscript)[^>]*>[\s\S]*?<\/\1>/gi, ' '));
}

function stripHtml_(html) {
  return String(html || '')
    .replace(/<br\s*\/?>/gi, '\n').replace(/<\/p>/gi, '\n\n').replace(/<\/li>/gi, '\n').replace(/<li[^>]*>/gi, '• ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#0?39;/g, "'").replace(/&nbsp;/g, ' ')
    .replace(/[ \t]+/g, ' ').replace(/ *\n */g, '\n').replace(/\n{3,}/g, '\n\n')
    .trim();
}

// ---------- Filtering and scoring ----------

function list_(csv) {
  return String(csv || '').split(',').map(w => w.trim()).filter(Boolean);
}

function plain_(text) {
  return String(text || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

// True if any part of "where" (e.g. "Budapest" or "Hungary") appears in the text, ignoring accents.
function near_(text, where) {
  const t = plain_(text);
  return list_(where).some(w => plain_(w).length > 2 && t.includes(plain_(w)));
}

// Whole words only, so "intern" does not block "internal".
function wordsRegex_(csv) {
  const words = list_(csv).map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  return words.length ? new RegExp('(^|[^\\p{L}\\p{N}])(' + words.join('|') + ')(?=$|[^\\p{L}\\p{N}])', 'iu') : null;
}

function prefilter_(jobs, seen, s) {
  const badTitle = wordsRegex_(s.avoidTitle), bad = wordsRegex_(s.avoid);
  const cutoff = Date.now() - ({ day: 1, week: 7, month: 30 }[s.since] || 7) * 864e5;
  const ids = new Set(), keys = new Set();
  return jobs.filter(j => {
    const key = j.company ? (j.company + '|' + j.title).toLowerCase() : j.id; // same job posted on two sites
    if (seen.has(j.id) || ids.has(j.id) || keys.has(key)) return false;
    if (j.posted && j.posted.getTime() < cutoff) return false;
    if (badTitle && badTitle.test(j.title)) return false;
    if (bad && bad.test(j.title + ' ' + j.company)) return false;
    ids.add(j.id);
    keys.add(key);
    return true;
  });
}

// Take jobs from each site in turn, so one busy site can't use up the daily limit.
function interleave_(jobs) {
  const bySite = {};
  jobs.forEach(j => (bySite[j.source] = bySite[j.source] || []).push(j));
  const lists = Object.keys(bySite).map(k => bySite[k]), out = [];
  for (let i = 0; out.length < jobs.length; i++) lists.forEach(l => { if (l[i]) out.push(l[i]); });
  return out;
}

// The AI gives sub-scores; the hard rules are enforced here so the AI can't talk past them.
// Returns verdict great | maybe | low | skip.
function decide_(r, s) {
  const L = tr_();
  const clamp = (v, max) => Math.max(0, Math.min(max, Math.round(Number(v) || 0)));
  let score = clamp(r.skills_fit, 40) + clamp(r.experience_fit, 20) + clamp(r.location_fit, 20) + clamp(r.conditions_fit, 20);
  const mode = r.work_mode || 'Unknown';
  const office = Number.isFinite(Number(r.office_days_per_week)) ? Number(r.office_days_per_week) : -1;
  const maxOffice = Number(s.maxOffice);
  let skip = '';
  if (s.workplace === 'remote' && (mode === 'Hybrid' || mode === 'Onsite')) skip = L.rule.remoteOnly(L.modes[mode]);
  else if (s.workplace === 'hybrid' && mode === 'Onsite') skip = L.rule.officeOnly;
  else if (s.workplace !== 'any' && mode === 'Hybrid' && office > maxOffice) skip = L.rule.tooMany(office, maxOffice);
  else if (r.breaks_dealbreaker === true) skip = r.dealbreaker_reason || L.rule.wish;
  if (skip) return { score: Math.min(score, 30), verdict: 'skip', note: skip };

  let note = '';
  if (s.workplace !== 'any' && (mode === 'Unknown' || (mode === 'Hybrid' && office < 0))) {
    score -= 5;
    note = L.rule.checkDays;
  }
  score = Math.max(0, score);
  const verdict = score >= Number(s.strongScore) ? 'great' : score >= Number(s.maybeScore) ? 'maybe' : 'low';
  return { score, verdict, note };
}

// The AI instructions stay in English; its answers come back in the candidate's chosen language.
function scoringPrompt_(s, cv) {
  const E = TEXT.en.opt;
  const office = s.workplace === 'any' ? '' : ` (at most ${s.maxOffice} office days per week)`;
  return `You are a friendly but strict job-matching assistant. Compare the job ad with the candidate's CV and wishes and score the fit honestly. Never assume skills or experience that are not in the CV.

CANDIDATE CV:
${cv}

CANDIDATE WISHES:
- Wants jobs like: ${s.titles}
- Location: ${s.where}
- Work from: ${E.workplace[s.workplace] || s.workplace}${office}
- Experience level: ${E.level[s.level] || s.level}
- Minimum salary: ${s.salary || 'not given'}
- Avoid these companies / industries: ${s.avoid || 'none'}
- Other important things: ${s.wishes || 'none'}

SCORING (whole numbers):
- skills_fit 0-40: how well the CV's skills and experience match what the job needs.
- experience_fit 0-20: does the required seniority / years of experience fit the candidate?
- location_fit 0-20: 20 = matches where and how they want to work; lower if far away or unclear.
- conditions_fit 0-20: salary vs their minimum (give 12 if no salary is shown), contract type, and their other wishes.
- breaks_dealbreaker: true ONLY if the job clearly goes against something they want to avoid or an important wish, or strictly requires something the CV clearly lacks (e.g. a language they don't speak, a mandatory licence). Then explain in dealbreaker_reason (short, in ${s.myLanguage}).
- work_mode: Remote, Hybrid, Onsite or Unknown. office_days_per_week: office days required per week, or -1 if not stated.
- requires_cover_letter: true only if the ad explicitly asks for a cover letter or motivation letter.
- posting_language: the language the job ad is written in, in English (e.g. "English", "Hungarian").
- company / location: the employer and the job's city, from the ad (empty if unknown).
- summary: 1-2 short, simple sentences in ${s.myLanguage}, speaking directly to the candidate ("You ..."). No jargon.
- matching_skills / missing_skills: short lists (max 6 each) in ${s.myLanguage}.`;
}

function jobText_(job) {
  return `Job title: ${job.title}\nCompany: ${job.company || 'see the ad'}\nLocation: ${job.location || 'see the ad'}\nFound on: ${job.source}\n\nJob ad:\n${job.description}`;
}

// ---------- Gemini (free Google AI) ----------

const STR = { type: 'STRING' }, INT = { type: 'INTEGER' }, BOOL = { type: 'BOOLEAN' }, STRS = { type: 'ARRAY', items: STR };
function obj_(props) { return { type: 'OBJECT', properties: props, required: Object.keys(props) }; }

const SCORE_SCHEMA = obj_({
  skills_fit: INT, experience_fit: INT, location_fit: INT, conditions_fit: INT,
  breaks_dealbreaker: BOOL, dealbreaker_reason: STR,
  work_mode: { type: 'STRING', enum: ['Remote', 'Hybrid', 'Onsite', 'Unknown'] },
  office_days_per_week: INT, requires_cover_letter: BOOL, posting_language: STR,
  company: STR, location: STR,
  summary: STR, matching_skills: STRS, missing_skills: STRS,
});

const CV_SCHEMA = obj_({
  labels: obj_({ summary: STR, skills: STR, experience: STR, education: STR, certifications: STR, languages: STR }),
  headline: STR, summary: STR,
  skill_groups: { type: 'ARRAY', items: obj_({ category: STR, skills: STRS }) },
  experience: { type: 'ARRAY', items: obj_({ role: STR, company: STR, period: STR, location: STR, bullets: STRS }) },
  education: { type: 'ARRAY', items: obj_({ degree: STR, institution: STR, period: STR, details: STR }) },
  certifications: STRS, languages: STRS, cover_letter: STR,
});

function gemini_(key, model, system, user, schema, temperature) {
  const E = tr_().err;
  const url = 'https://generativelanguage.googleapis.com/v1beta/models/' + encodeURIComponent(model) + ':generateContent';
  const payload = JSON.stringify({
    systemInstruction: { parts: [{ text: system }] },
    contents: [{ role: 'user', parts: [{ text: user }] }],
    generationConfig: { temperature, responseMimeType: 'application/json', responseSchema: schema },
  });
  for (let attempt = 1; attempt <= 3; attempt++) {
    const res = UrlFetchApp.fetch(url, { method: 'post', contentType: 'application/json', headers: { 'x-goog-api-key': key }, payload, muteHttpExceptions: true });
    const code = res.getResponseCode(), body = res.getContentText();
    if (code === 200) return parseGemini_(body);
    if (code === 429 || code >= 500) { Utilities.sleep(8000 * attempt); continue; }
    if (code === 401 || code === 403 || /API_KEY_INVALID|API key not valid/i.test(body)) throw new Error(E.keyBad);
    if (code === 404) throw new Error(E.model(model));
    throw new Error(E.aiError + body.slice(0, 300));
  }
  throw new Error(E.aiBusy);
}

function parseGemini_(body) {
  const data = JSON.parse(body);
  const parts = (((data.candidates || [])[0] || {}).content || {}).parts || [];
  const answer = parts.filter(p => !p.thought && typeof p.text === 'string').pop();
  if (!answer) throw new Error(tr_().err.aiEmpty);
  return JSON.parse(answer.text.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, ''));
}

// ---------- Tailored CV and cover letter (Google Docs + PDF) ----------

function makeDocs_(key, s, cv, job, r) {
  const D = tr_().docs;
  const lang = s.cvLanguage === 'same' ? (r.posting_language || 'English') : s.cvLanguage;
  const wantLetter = s.coverLetter === 'always' || (s.coverLetter === 'asked' && r.requires_cover_letter === true);
  const system = `You write tailored, honest, ATS-friendly CVs. Write everything in ${lang}.
${wantLetter ? `Also write a short cover letter (max 250 words) in ${lang} in "cover_letter", including greeting and sign-off with the candidate's name.` : 'Set "cover_letter" to an empty string.'}
RULES:
1. Use ONLY facts from the candidate's CV below. Never invent employers, job titles, dates, degrees, certificates or numbers.
2. Reorder and reword so the experience and skills most relevant to this job come first. Use the job ad's keywords only where they are true for the candidate.
3. Keep it to 1-2 pages: 3-6 bullets for recent jobs, 2-4 for older ones. Leave lists empty if the CV has nothing for them.
4. "labels" are the CV section headings, written in ${lang}.

CANDIDATE CV:
${cv}`;
  const user = jobText_(job).slice(0, 6000) + `\n\nSkills that match: ${(r.matching_skills || []).join(', ')}\nGaps to frame honestly: ${(r.missing_skills || []).join(', ')}`;
  Utilities.sleep(4000);
  const g = gemini_(key, s.model, system, user, CV_SCHEMA, 0.2);

  const folder = folder_();
  const base = [s.name, job.company, job.title].filter(Boolean).join(' - ').replace(/[\\/:*?"<>|]/g, ' ').slice(0, 100);
  const cvDoc = saveAsPdf_(writeCv_(DocumentApp.create(D.cv + base), s, g), folder);
  const pdfs = [cvDoc.pdf];
  if (wantLetter && g.cover_letter) pdfs.push(saveAsPdf_(writeLetter_(DocumentApp.create(D.letter + base), s, g), folder).pdf);
  return { url: cvDoc.url, pdfs };
}

function writeCv_(doc, s, g) {
  const b = doc.getBody().setMarginTop(36).setMarginBottom(36).setMarginLeft(48).setMarginRight(48);
  const H = DocumentApp.ParagraphHeading;
  const L = g.labels || {};
  const has = a => Array.isArray(a) && a.length > 0;
  const heading = t => b.appendParagraph(t || '').setHeading(H.HEADING2);
  const bullet = t => b.appendListItem(t).setGlyphType(DocumentApp.GlyphType.BULLET);
  const small = t => { if (t) b.appendParagraph(t).setItalic(true); };

  b.getParagraphs()[0].setText(s.name).setHeading(H.TITLE);
  if (g.headline) b.appendParagraph(g.headline).setBold(true);
  b.appendParagraph([s.city, s.email, s.phone, s.linkedin].filter(String).join('  |  ')).setBold(false);
  if (g.summary) { heading(L.summary); b.appendParagraph(g.summary); }
  if (has(g.skill_groups)) {
    heading(L.skills);
    g.skill_groups.forEach(x => {
      const p = b.appendParagraph(`${x.category}: ${(x.skills || []).join(', ')}`);
      if (x.category) p.editAsText().setBold(0, x.category.length, true);
    });
  }
  if (has(g.experience)) {
    heading(L.experience);
    g.experience.forEach(e => {
      b.appendParagraph([e.role, e.company].filter(Boolean).join(' - ')).setHeading(H.HEADING3);
      small([e.period, e.location].filter(Boolean).join('  |  '));
      (e.bullets || []).forEach(bullet);
    });
  }
  if (has(g.education)) {
    heading(L.education);
    g.education.forEach(e => {
      b.appendParagraph([e.degree, e.institution].filter(Boolean).join(' - ')).setHeading(H.HEADING3);
      small(e.period);
      if (e.details) b.appendParagraph(e.details);
    });
  }
  if (has(g.certifications)) { heading(L.certifications); g.certifications.forEach(bullet); }
  if (has(g.languages)) { heading(L.languages); g.languages.forEach(bullet); }
  return doc;
}

function writeLetter_(doc, s, g) {
  const b = doc.getBody().setMarginTop(48).setMarginBottom(48).setMarginLeft(60).setMarginRight(60);
  b.getParagraphs()[0].setText(s.name).setBold(true);
  b.appendParagraph([s.city, s.email, s.phone].filter(String).join('  |  ')).setBold(false);
  b.appendParagraph('');
  String(g.cover_letter).split(/\n\s*\n/).forEach(p => b.appendParagraph(p.trim()));
  return doc;
}

function saveAsPdf_(doc, folder) {
  const url = doc.getUrl();
  doc.saveAndClose();
  const file = DriveApp.getFileById(doc.getId());
  file.moveTo(folder);
  const pdf = file.getAs(MimeType.PDF);
  folder.createFile(pdf);
  return { url, pdf };
}

function folder_() {
  const props = PropertiesService.getDocumentProperties();
  const id = props.getProperty('FOLDER_ID');
  if (id) {
    try { const f = DriveApp.getFolderById(id); if (!f.isTrashed()) return f; } catch (e) { /* deleted or not ours: make a new one */ }
  }
  const f = DriveApp.createFolder(tr_().docs.folder);
  props.setProperty('FOLDER_ID', f.getId());
  return f;
}

// ---------- Output: sheet row + email ----------

// Text from job sites must never be run as a spreadsheet formula.
function cell_(v) { return /^[=+\-@]/.test(String(v)) ? "'" + v : v; }
function link_(url, label) { return url ? `=HYPERLINK("${String(url).replace(/"/g, '%22')}","${label}")` : ''; }

function addJobRow_(sheet, job, r, d, cvUrl) {
  const L = tr_();
  const why = [d.note, r.summary].filter(Boolean).join('. ');
  sheet.insertRowBefore(2);
  sheet.getRange(2, 1, 1, L.jobHeaders.length)
    .setValues([[new Date(), d.score, L.verdict[d.verdict], cell_(job.title), cell_(job.company), cell_(job.location), job.source,
      L.modes[r.work_mode] || r.work_mode, cell_(why), link_(job.url, L.mail.openAd), link_(cvUrl, L.mail.cvLink), L.status[0], job.id]])
    .setFontWeight('normal')
    .setFontColor(d.verdict === 'great' || d.verdict === 'maybe' ? '#000000' : '#999999')
    .setBackground({ great: '#d9f2d9', maybe: '#fff4cc' }[d.verdict] || null);
  sheet.getRange(2, 1).setNumberFormat('yyyy-mm-dd');
  sheet.getRange(2, COL_STATUS).setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(L.status, true).build());
}

function sendEmail_(s, great, maybe) {
  const M = tr_().mail;
  const esc = t => String(t || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const item = x => `<li style="margin-bottom:12px"><b><a href="${esc(x.job.url)}">${esc(x.job.title)}</a></b>`
    + (x.job.company ? esc(M.at) + esc(x.job.company) : '') + ` (${esc([x.job.location, M.foundOn + x.job.source].filter(Boolean).join(', '))})<br>`
    + `${M.score} ${x.d.score}/100. ${esc([x.d.note, x.r.summary].filter(Boolean).join('. '))}`
    + (x.docs.url ? `<br><a href="${esc(x.docs.url)}">${M.openCv}</a> ${M.attached}` : '') + '</li>';
  const html = (great.length ? `<h3>${M.great}</h3><ul>${great.map(item).join('')}</ul>` : '')
    + (maybe.length ? `<h3>${M.maybe}</h3><ul>${maybe.map(item).join('')}</ul>` : '')
    + `<p><a href="${esc(SpreadsheetApp.getActive().getUrl())}">${M.seeAll}</a></p>`;
  MailApp.sendEmail({
    to: s.email || Session.getEffectiveUser().getEmail(),
    subject: M.subject(great.length, maybe.length),
    htmlBody: html,
    attachments: [].concat(...great.map(x => x.docs.pdfs)),
  });
}

// ---------- Sheet setup and settings ----------

// Finds a tab by its name in any language.
function sheetById_(id) {
  const ss = SpreadsheetApp.getActive();
  for (const l of Object.keys(TEXT)) {
    const sh = ss.getSheetByName(TEXT[l].tabs[id]);
    if (sh) return sh;
  }
  return null;
}

// Creates any missing tab and (re)writes every label in the current language. Safe to run any time.
function buildSheet_() {
  const ss = SpreadsheetApp.getActive(), l = lang_(), L = TEXT[l];
  const tab = {};
  Object.keys(L.tabs).forEach((id, i) => {
    tab[id] = sheetById_(id) || ss.insertSheet(L.tabs[id], i);
    if (tab[id].getName() !== L.tabs[id]) tab[id].setName(L.tabs[id]);
  });

  const start = tab.start, status = start.getRange('A3').getValue();
  start.clear();
  start.getRange(1, 1, L.start.length, 1).setValues(L.start.map(t => [t])).setWrap(true).setVerticalAlignment('top');
  if (status && !Object.keys(TEXT).some(k => TEXT[k].start[2] === status)) start.getRange('A3').setValue(status);
  start.getRange('A1').setFontSize(18).setFontWeight('bold');
  start.getRange('A3').setFontColor('#1a73e8').setFontWeight('bold');
  start.getRange('A4').setFontColor('#5f6368');
  start.setColumnWidth(1, 900);
  start.setHiddenGridlines(true);

  const st = tab.settings, old = settingsRaw_(), n = SETTINGS.length, last = st.getLastRow();
  st.getRange(1, 1, 1, 4).setValues([L.settingsHeader]).setFontWeight('bold');
  st.getRange(2, 1, n, 4).setValues(SETTINGS.map(d => [d.label[l], display_(d, d.key in old ? old[d.key] : def_(d, l), l), d.help[l], d.key]));
  st.getRange(2, 2, n, 1).setDataValidations(SETTINGS.map(d => [validation_(d, l)])).setBackground('#fff8c5').setWrap(true);
  st.getRange(2, 3, n, 1).setFontColor('#666666').setWrap(true);
  if (last > n + 1) st.getRange(n + 2, 1, last - n - 1, 4).clearContent().clearDataValidations();
  st.setFrozenRows(1);
  st.setColumnWidth(1, 300).setColumnWidth(2, 380).setColumnWidth(3, 560);
  st.hideColumns(4);

  const cv = tab.cv;
  cv.getRange('A1').setValue(L.cvTab).setFontWeight('bold').setWrap(true);
  cv.getRange('A3:A200').setWrap(true).setBackground('#fff8c5');
  cv.setColumnWidth(1, 900);

  const jobs = tab.jobs;
  if (jobs.getLastRow() === 0) [90, 55, 120, 260, 180, 160, 100, 90, 420, 130, 110, 120].forEach((w, i) => jobs.setColumnWidth(i + 1, w));
  jobs.getRange(1, 1, 1, L.jobHeaders.length).setValues([L.jobHeaders]).setFontWeight('bold').setBackground('#e8eaed');
  jobs.setFrozenRows(1);
  jobs.hideColumns(COL_ID);

  ss.getSheets().filter(sh => !Object.values(L.tabs).includes(sh.getName()) && sh.getLastRow() === 0).forEach(sh => ss.deleteSheet(sh));
}

function validation_(d, l) {
  const v = SpreadsheetApp.newDataValidation();
  if (d.checkbox) return v.requireCheckbox().build();
  const list = d.opts ? Object.values(TEXT[l].opt[d.opts]) : d.list;
  return list ? v.requireValueInList(list.map(String), true).setAllowInvalid(Boolean(d.free)).build() : null;
}

// A row belongs to a setting by its hidden key, or by its label in any language (sheets made before the key column).
function findSetting_(row) {
  return SETTINGS.find(d => d.key === row[3]) || SETTINGS.find(d => Object.values(d.label).includes(String(row[0]).trim()));
}

// key -> value exactly as it is in the sheet
function settingsRaw_() {
  const st = sheetById_('settings'), out = {};
  if (!st || st.getLastRow() < 2) return out;
  st.getRange(2, 1, st.getLastRow() - 1, 4).getValues().forEach(r => {
    const d = findSetting_(r);
    if (d && !(d.key in out)) out[d.key] = r[1];
  });
  return out;
}

function readSettings_() {
  const l = lang_(), raw = settingsRaw_(), s = {};
  SETTINGS.forEach(d => {
    const v = raw[d.key];
    s[d.key] = v === '' || v === undefined || v === null ? def_(d, l) : toKey_(d, typeof v === 'string' ? v.trim() : v);
  });
  return s;
}

function writeSetting_(key, value) {
  const d = SETTINGS.find(x => x.key === key), st = sheetById_('settings');
  const i = st.getRange(1, 1, st.getLastRow(), 4).getValues().findIndex(r => findSetting_(r) === d);
  if (i >= 0) st.getRange(i + 1, 2).setValue(display_(d, value, lang_()));
}

function readCv_() {
  const sh = sheetById_('cv');
  if (!sh || sh.getLastRow() < 3) return '';
  return sh.getRange(3, 1, sh.getLastRow() - 2, 1).getValues().map(r => String(r[0]).trim()).filter(Boolean).join('\n');
}

function yes_(v) { return v === true || String(v).toUpperCase() === 'TRUE'; }

// Keys are stored privately for this Google account, not in the sheet, so copies of the sheet never leak them.
function getKey_() { return PropertiesService.getUserProperties().getProperty('GEMINI_KEY'); }

function installDaily_() {
  ScriptApp.getProjectTriggers().filter(t => t.getHandlerFunction() === 'findJobs').forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('findJobs').timeBased().everyDays(1).atHour(7).create();
}

// ---------- Setup window ----------
// {{name}} is replaced with the text from TEXT[language].wiz, __DATA__ with the current values.

const WIZARD_HTML = `<!DOCTYPE html>
<html><head><base target="_blank"><style>
body{font-family:Arial,sans-serif;font-size:15px;color:#202124;margin:0;padding:0 18px 18px}
h2{font-size:17px;margin:24px 0 6px;color:#1a73e8}
label{display:block;margin:12px 0 4px;font-weight:bold}
.hint{font-weight:normal;color:#5f6368;font-size:13px}
input[type=text],select,textarea{width:100%;box-sizing:border-box;padding:10px;font-size:15px;border:1px solid #dadce0;border-radius:6px}
textarea{height:180px}
.site{display:flex;gap:10px;align-items:flex-start;margin:8px 0;font-weight:normal;cursor:pointer}
.site input{margin-top:4px;transform:scale(1.4)}
.big{display:inline-block;margin:8px 0;padding:10px 14px;background:#e8f0fe;border-radius:6px;text-decoration:none;font-weight:bold}
.lang{text-align:right;margin-top:10px;font-size:15px}
.lang a{margin-left:8px;padding:4px 10px;border-radius:12px;text-decoration:none;border:1px solid #dadce0;color:#1a73e8}
.lang a.on{background:#1a73e8;color:#fff;border-color:#1a73e8}
button{font-size:16px;padding:13px 24px;border:0;border-radius:6px;background:#1a73e8;color:#fff;cursor:pointer;margin:18px 10px 0 0}
button:disabled{background:#9aa0a6}
button.second{background:#188038}
#msg{margin-top:14px;font-size:15px;white-space:pre-wrap}
.err{color:#c5221f;font-weight:bold}.ok{color:#188038;font-weight:bold}
</style></head><body>
<div class="lang">🌐<a href="#" id="lang-en" onclick="return lang('en')">English</a><a href="#" id="lang-hu" onclick="return lang('hu')">Magyar</a></div>
<h2>{{k1Title}}</h2>
<div class="hint">{{k1Hint}}</div>
<a class="big" href="https://aistudio.google.com/apikey">{{k1Button}}</a>
<input type="text" id="key" placeholder="{{keyPh}}" autocomplete="off">

<h2>{{k2Title}}</h2>
<label>{{name}}</label><input type="text" id="name">
<label>{{email}} <span class="hint">{{emailHint}}</span></label><input type="text" id="email">
<label>{{phone}} <span class="hint">{{phoneHint}}</span></label><input type="text" id="phone">
<label>{{city}} <span class="hint">{{cityHint}}</span></label><input type="text" id="city">

<h2>{{k3Title}}</h2>
<label>{{titles}} <span class="hint">{{titlesHint}}</span></label><input type="text" id="titles">
<label>{{where}} <span class="hint">{{whereHint}}</span></label><input type="text" id="where">
<label>{{workplace}}</label><select id="workplace"></select>
<label>{{maxOffice}} <span class="hint">{{maxOfficeHint}}</span></label><select id="maxOffice"></select>

<h2>{{k4Title}}</h2>
<div class="hint">{{k4Hint}}</div>
<div id="sites"></div>
<div id="joobleBox" style="display:none">
<label>{{jooble}} <span class="hint">{{joobleHint}} <a href="https://jooble.org/api/about">jooble.org/api/about</a></span></label>
<input type="text" id="joobleKey" autocomplete="off">
</div>

<h2>{{k5Title}}</h2>
<div class="hint">{{k5Hint}}</div>
<textarea id="cv"></textarea>

<button id="save" onclick="save()">{{save}}</button>
<div id="msg"></div>
<div class="hint" style="margin-top:18px">{{more}}</div>
<script>
var D = __DATA__;
function el(id) { return document.getElementById(id); }
function show(text, cls) { el('msg').className = cls || ''; el('msg').textContent = text; }
el('lang-' + D.lang).className = 'on';
['name', 'email', 'phone', 'city', 'titles', 'where', 'cv'].forEach(function (k) { el(k).value = D.values[k] || ''; });
D.workplaces.forEach(function (w) { var op = document.createElement('option'); op.value = w.key; op.textContent = w.label; op.selected = (w.key === D.values.workplace); el('workplace').appendChild(op); });
['0', '1', '2', '3', '4', '5'].forEach(function (n) { var op = document.createElement('option'); op.textContent = n; op.selected = (n === String(D.values.maxOffice)); el('maxOffice').appendChild(op); });
if (D.hasKey) el('key').placeholder = D.t.keySaved;
if (D.hasJoobleKey) el('joobleKey').placeholder = D.t.keySaved;
D.sites.forEach(function (x) {
  var row = document.createElement('label'); row.className = 'site';
  var box = document.createElement('input'); box.type = 'checkbox'; box.checked = x.on; box.setAttribute('data-site', x.name);
  var text = document.createElement('span'); text.innerHTML = '<b></b><br><span class="hint"></span>';
  text.firstChild.textContent = x.name; text.lastChild.textContent = x.note;
  row.appendChild(box); row.appendChild(text); el('sites').appendChild(row);
});
function toggleJooble() { var j = document.querySelector('[data-site="Jooble"]'); el('joobleBox').style.display = j && j.checked ? 'block' : 'none'; }
el('sites').addEventListener('change', toggleJooble); toggleJooble();

function lang(l) {
  if (l !== D.lang) {
    show(D.t.switching);
    google.script.run.withFailureHandler(function (e) { show('⚠️ ' + e.message, 'err'); }).setLanguage(l);
  }
  return false;
}
function save() {
  var f = { sites: {} };
  ['key', 'name', 'email', 'phone', 'city', 'titles', 'where', 'workplace', 'maxOffice', 'cv', 'joobleKey'].forEach(function (k) { f[k] = el(k).value.trim(); });
  document.querySelectorAll('[data-site]').forEach(function (c) { f.sites[c.getAttribute('data-site')] = c.checked; });
  el('save').disabled = true;
  show(D.t.saving);
  google.script.run
    .withSuccessHandler(function () { el('save').disabled = false; show(D.t.saved, 'ok'); addTryButton(); })
    .withFailureHandler(function (e) { el('save').disabled = false; show('⚠️ ' + e.message, 'err'); })
    .saveWizard(f);
}
function addTryButton() {
  if (el('try')) return;
  var b = document.createElement('button'); b.id = 'try'; b.className = 'second'; b.textContent = D.t.tryBtn;
  b.onclick = function () {
    b.disabled = true;
    show(D.t.searching);
    google.script.run
      .withSuccessHandler(function (m) { b.disabled = false; show(m + '\\n\\n' + D.t.seeJobs, 'ok'); })
      .withFailureHandler(function (e) { b.disabled = false; show('⚠️ ' + e.message, 'err'); })
      .findJobs();
  };
  el('save').after(b);
}
</script>
</body></html>`;
