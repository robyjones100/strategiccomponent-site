# Strat Com website (Strategic Components, LLC)

Static site for GitHub Pages. The inventory catalog is generated from your spreadsheet.

## Go live
1. Create a GitHub repo and upload everything in this folder. Settings > Pages > deploy from the `main` branch, `/ (root)`.
2. Pages > Custom domain: `strategiccomponent.com` (CNAME file included). Turn on Enforce HTTPS.
3. Cloudflare DNS for strategiccomponent.com: four A records for `@` to 185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153, and a CNAME `www` to `<your-github-username>.github.io`. Use "DNS only" (grey cloud) at first. Leave the Zoho MX, SPF and DKIM records alone.
4. Redirect strategic-components.com: add it to Cloudflare, create proxied (orange cloud) A records for `@` and `www` pointing to 192.0.2.1, then Rules > Redirect Rules: for this hostname, redirect to `https://strategiccomponent.com` (301, preserve path).

## Updating the inventory
1. Put your full spreadsheet export at `source/inventory.csv`. This folder is in `.gitignore`, so it is never uploaded. **Do not commit it**: it contains quantities, serial numbers and remarks that must stay private.
2. Run `python3 build.py` (Python 3 only, no packages needed).
3. Commit and push the changed files (`inventory/`, `data/`, `inventory.html`, `index.html`, `sitemap.xml`).

The build keeps only NSN, part number, alternate part numbers, manufacturer, CAGE, description and end use. It merges duplicate rows, repairs garbled characters, and skips rows with no part number.

## How the catalog is organized
- `inventory.html`: search box on top, then page 1 of the listing (about 1,000 parts sorted by part number) with page links at the bottom. Typing in the search box replaces the listing with results.
- `inventory/page-2.html` to `page-56.html`: the rest of the listing, about 1,000 per page, each with its own title and description built from its part number range and most common items. All pages are in `sitemap.xml`.
- Quote links in the tables point to plain `/rfq.html`, so Google sees one URL instead of thousands. The part number is added in the browser when a visitor hovers or taps the link.
- `data/search.json`: loaded only when someone searches (about 0.6 MB compressed).
- `quality.html` and `terms.html`: quality assurance and quote and sales terms.

After you push, add the site in Google Search Console and submit `https://strategiccomponent.com/sitemap.xml`.

## RFQ form to Google Sheets
1. Create a Google Sheet. Rename the first tab `RFQs`. In row 1 type these headers: Timestamp, Name, Business, Email, Phone, NSN / Part Number, Quantity, Target Price, Reason, Additional Information.
2. Select columns B to J, then Format > Number > Plain text. This stops Sheets from turning part numbers such as 3-1-02 into dates and from running anything that begins with `=`.
3. Extensions > Apps Script. Replace the contents with:
```js
const SHEET_NAME = 'RFQs';
const NOTIFY_TO = 'sales@strategiccomponent.com';

function doPost(e) {
  const p = e.parameter || {};
  const v = k => String(p[k] || '').trim().slice(0, 2000);
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  sheet.appendRow([new Date(), v('name'), v('business'), v('email'), v('phone'),
                   v('part'), v('quantity'), v('target_price'), v('reason'), v('notes')]);
  const mail = {
    to: NOTIFY_TO,
    subject: 'New RFQ: ' + v('part') + ' (' + v('business') + ')',
    body: ['Name: ' + v('name'), 'Business: ' + v('business'), 'Email: ' + v('email'), 'Phone: ' + v('phone'),
           'NSN / Part number: ' + v('part'), 'Quantity: ' + v('quantity'), 'Target price: ' + v('target_price'),
           'Reason: ' + v('reason'), '', v('notes')].join('\n')
  };
  if (/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v('email'))) mail.replyTo = v('email');
  MailApp.sendEmail(mail);
  return ContentService.createTextOutput('ok');
}
```
4. Deploy > New deployment > type Web app. Execute as: Me. Who has access: Anyone. Deploy, approve the permissions, and copy the Web app URL (it ends in `/exec`).
5. Paste that URL into `FORM_ENDPOINT` at the top of `assets/site.js`, commit and push.
6. If you later edit the script, use Deploy > Manage deployments > Edit > New version, or the live URL keeps running the old code.
Until `FORM_ENDPOINT` is set, the form opens a pre-filled email to sales@ instead.

## Still to add
CAGE code and SAM registration, plus the real phone number and address (the current ones are placeholders). Search for `TODO` in `build.py`, and for `1-888-888-888` and `1234 Front Street` to replace the placeholders, then run `python3 build.py`.
