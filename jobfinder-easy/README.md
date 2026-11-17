# JobFinder Easy

A free job-search helper that lives in a Google Sheet. Every morning it searches job sites, has a free AI compare each job with your CV and wishes, and emails you the best matches with a tailored CV attached.

- **Free:** you only need a Google account and a free AI key from Google.
- **No installing, no coding:** everything runs on Google's servers, so your computer can stay off.
- **Several job sites:** LinkedIn, Profession.hu, NoFluffJobs and Jooble. Each one is a tick box, so you can switch sites on or off whenever you like.
- **English or Hungarian (magyarul):** the whole app (menu, setup window, tabs, settings, emails, CV file names) works in both languages. 🇭🇺 [Magyar útmutató: README.hu.md](README.hu.md)

This is a simpler version of the n8n workflow in the main folder. The two don't depend on each other.

---

## Part 1: For the helper (one time, about 5 minutes)

Do this once yourself, then send the link to your friend.

1. Open [sheets.new](https://sheets.new) to create a blank Google Sheet. Name it **JobFinder**.
2. Click **Extensions → Apps Script**.
3. Delete everything in the editor, then paste the whole contents of [`Code.gs`](Code.gs). Click the 💾 **Save** icon.
4. Close the Apps Script tab and reload the sheet. After a few seconds a **🔎 JobFinder** menu appears and the tabs are created: *Start here*, *Settings*, *My CV*, *Jobs*.
   - If your Google account is set to Hungarian, the sheet starts in Hungarian instead (*Kezdés*, *Beállítások*, *Önéletrajzom*, *Állások*).
5. **For a Hungarian friend:** in the *Settings* tab, set the first row, **Language / Nyelv**, to **Magyar**. The sheet switches to Hungarian after a few seconds, and your friend's copy will be in Hungarian too.
6. Click **Share → General access → Anyone with the link → Viewer**. Copy the link.
7. In the link, change the ending `/edit?usp=sharing` to `/copy`. Send this link to your friend, together with [README.hu.md](README.hu.md) if they prefer Hungarian.

The `/copy` link makes a separate copy, script included, for each person who opens it. Nobody can see anyone else's CV, jobs or keys.

## Part 2: For your friend (about 10 minutes)

1. **Open the link** you were sent and click **Make a copy**.
2. In your copy, click the menu **🔎 JobFinder** (at the top, next to "Help"), then **▶ Setup**.
   *No menu? Reload the page and wait a few seconds.*
3. Google asks for permission:
   - Pick your Google account.
   - If you see "Google hasn't verified this app", click **Advanced**, then **Go to JobFinder (unsafe)**, then **Allow**.
   - This is safe: the program lives in your own copy and only you run it.
4. A setup window opens. Fill in the 5 steps:
   1. **Free AI key:** click the blue button, sign in, click **Create API key**, copy the key and paste it in.
   2. **About you:** name, email, phone, city.
   3. **What job:** job titles (separate them with commas), where, and how many office days you can do.
   4. **Job sites:** tick the ones you want.
   5. **Your CV:** open your CV, press Ctrl+A, then Ctrl+C, click in the box and press Ctrl+V.
5. Click **✅ Save and start**, then **🔎 Find jobs now** to try it.

From now on it runs by itself every morning around 7:00:
- Good jobs arrive by email.
- Every job it checked appears in the **Jobs** tab. Use the **My status** column to track where you applied.
- Tailored CVs are saved in Google Drive, in the folder **JobFinder CVs**.

## Changing things later

- **The basics** (name, job titles, location, job sites, CV): open **🔎 JobFinder → ▶ Setup** again.
- **Everything else** is in the **Settings** tab. Change the yellow cells; most of them have a dropdown. For example:
  - minimum salary
  - words to skip in job titles
  - companies or industries to avoid
  - other wishes in plain words, e.g. "no night shifts"
  - how strict the scores are
  - CV language
  - cover letters
  - language of the emails
- **Pause it:** **🔎 JobFinder → Stop daily search**. To restart, run **▶ Setup** and click **Save and start**.
- **Switch language:** click **English** or **Magyar** at the top of the setup window, or change the first row of the Settings tab, **Language / Nyelv**. All your answers are kept. Reload the page afterwards so the menu changes too.

## The job sites

| Site | Needs | Notes |
| --- | --- | --- |
| LinkedIn | nothing | Worldwide. Uses LinkedIn's public job pages; LinkedIn sometimes blocks automatic searches for a while. |
| Profession.hu | nothing | Hungary. It searches the whole country, so jobs in other cities show up too; the AI gives those a lower score. |
| NoFluffJobs | nothing | Hungary, Poland, Czechia, Slovakia. Keeps only jobs near your "Where" answer, plus remote jobs. |
| Jooble | a free key | Worldwide, collects jobs from many sites. Request a key at [jooble.org/api/about](https://jooble.org/api/about); it arrives by email. Paste it in the setup window. |

If a site doesn't answer, JobFinder notes it on the *Start here* tab and carries on with the other sites.

**Adding another site (for the helper):** add one entry to the `SITES` list near the top of `Code.gs`. It needs two functions: one that searches and one that fetches the job ad text. Then paste the updated file into Apps Script. The new site's tick box appears in the setup window and the Settings tab by itself.

## Good to know

- **About 10 jobs per day:** Google stops each run after 6 minutes, so it checks about 10 new jobs per day. Any extra jobs are checked the next day.
- **Free AI limits:** the free AI key has a daily limit. If it's used up, JobFinder says so and continues the next day.
- **Privacy:** your keys are stored privately in your Google account, not in the sheet. Don't share your copy of the sheet, because it contains your CV.
- **Morning time zone:** "morning" means the time zone of the Apps Script project. To change it: Extensions → Apps Script → ⚙️ Project Settings → Time zone.

## For developers

`node jobfinder-easy/selftest.js` checks the following without needing Google:
- the site parsers
- switching sites on and off
- the filters and scoring rules
- protection against spreadsheet formulas in job text
- the setup window in both languages
- that the English and Hungarian texts have the same keys
- building the sheet, switching language, and upgrading a sheet made with the earlier English-only version (on an in-memory fake sheet)

All visible text lives in the `TEXT` table at the top of `Code.gs`, one block per language. The AI instructions stay in English; the AI answers in the language chosen in Settings. To add a language:
1. Copy the `en` block and translate it.
2. Add the language to every `opt.lang` list.
3. Add its `label` and `help` to each entry in `SETTINGS`.
