#!/usr/bin/env python3
"""Regenerates the whole Strat Com site from source/inventory.csv.

Usage:  python3 build.py [path/to/inventory.csv]

Public pages only ever show: NSN, part number (+ alternates), manufacturer (+ CAGE),
description and end use. Quantity, serial number, remarks and condition are never
written to any output file.
"""
import csv, datetime, html, json, os, re, shutil, sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "source", "inventory.csv")
BASE = "https://strategiccomponent.com"
PER_PAGE = 1000
esc = html.escape

# ---------------------------------------------------------------- cleaning
def fix(s):
    s = (s or "").replace("‐", "-").replace("‑", "-").replace("–", "-").replace("−", "-")
    s = s.replace(" ", " ").replace("­", "")
    if re.search("[ÂÃâ]", s):
        try:
            s = s.encode("cp1252").decode("utf-8")
        except Exception:
            pass
    s = re.sub(r"[^\x20-\x7e]", "", s)  # keep plain ASCII only
    return re.sub(r"\s+", " ", s).strip()

def fmt_nsn(raw):
    d = re.sub(r"\D", "", (raw or "").split("\n")[0])
    if len(d) == 13:
        return f"{d[:4]}-{d[4:6]}-{d[6:9]}-{d[9:]}"
    return ""

def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())

def natkey(s):
    return re.sub(r"\d+", lambda m: m.group().zfill(12), s)

def load():
    rows = list(csv.reader(open(SRC, encoding="utf-8-sig", newline="")))
    head = [h.strip().upper() for h in rows[0]]
    ix = {h: i for i, h in enumerate(head)}
    get = lambda r, k: r[ix[k]] if k in ix and len(r) > ix[k] else ""
    merged, skipped = {}, 0
    for r in rows[1:]:
        pn = fix(get(r, "PN"))
        if not norm(pn):
            skipped += 1
            continue
        nsn = fmt_nsn(get(r, "NSN/NIIN"))
        desc, mfg, cage = fix(get(r, "DESCR.")), fix(get(r, "MFG")), fix(get(r, "CAGE"))
        app, alt = fix(get(r, "APPLICATION")), fix(get(r, "ALT"))
        key = (norm(pn), nsn, desc.lower(), mfg.lower())
        m = merged.get(key)
        if not m:
            merged[key] = m = dict(pn=pn, alt=[], nsn=nsn, desc=desc, mfg=mfg, cage=cage, app=[])
        if alt and alt not in m["alt"] and norm(alt) != norm(pn): m["alt"].append(alt)
        if app and app not in m["app"]: m["app"].append(app)
        if cage and not m["cage"]: m["cage"] = cage
    items = []
    for m in merged.values():
        items.append(dict(pn=m["pn"], alt=", ".join(m["alt"][:4]), nsn=m["nsn"], desc=m["desc"],
                          mfg=m["mfg"], cage=m["cage"], app=", ".join(m["app"][:6])))
    items.sort(key=lambda x: natkey(x["pn"].lower()))
    return items, skipped, len(rows) - 1

# ---------------------------------------------------------------- layout
def bp_list():
    """Schematic backdrops: every assets/bp/s*.png is picked up automatically (name:width:height)."""
    d = os.path.join(ROOT, "assets", "bp"); out = []
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if f.startswith("s") and f.endswith(".png"):
            with open(os.path.join(d, f), "rb") as fh:
                h = fh.read(24)
            out.append(f"{f}:{int.from_bytes(h[16:20], 'big')}:{int.from_bytes(h[20:24], 'big')}")
    return ",".join(out)

def shell(path, title, desc, body, cur="", extra_head="", bp=True):
    def nav(href, label):
        return f'<a href="{href}"{" aria-current=page" if cur == href else ""}>{label}</a>'
    canon = BASE + path.replace("index.html", "")
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canon}">
<link rel="icon" href="/favicon.ico" sizes="48x48"><link rel="icon" type="image/png" sizes="96x96" href="/assets/favicon-96.png"><link rel="icon" type="image/svg+xml" href="/assets/logo-icon.svg"><link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@500;600&amp;family=IBM+Plex+Sans:wght@400;500;600&amp;family=IBM+Plex+Mono:wght@400;500&amp;display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/style.css">{extra_head}</head><body>
<a class="skip" href="#main">Skip to content</a>
<header class="site"><div class="wrap"><a class="brand" href="/"><img src="/assets/logo.png" alt="Strat Com – Strategic Components, LLC" width="226" height="62"></a>
<nav aria-label="Main">{nav("/","Home")}{nav("/inventory.html","Inventory")}{nav("/quality.html","Quality")}{nav("/terms.html","Terms")}{nav("/contact.html","Contact")}<a class="btn" href="/rfq.html">Request for quote</a></nav></div></header>
<main id="main"{' class="bp"' if bp else ""}>{('<div class="bp-bg" aria-hidden="true" data-bps="' + bp_list() + '"></div>') if bp else ""}{body}</main>
<footer class="site"><div class="wrap"><div class="foot"><a class="foot-home" href="/" aria-label="Strat Com home"><img class="foot-mark" src="/assets/logo-box.svg" alt="SC – Strat Com" width="132" height="132"></a>
<div class="fcol"><p><strong>Strategic Components, LLC</strong><br>Doing business as Strat Com</p><address>2221 St. George Lane, Suite 7<br>Chico, CA 95926</address></div>
<div class="fcol"><p><strong>Contact</strong><br><a href="tel:1-888-888-8888">1-888-888-8888</a><br><a href="mailto:sales@strategiccomponent.com">sales@strategiccomponent.com</a><br><a href="mailto:info@strategiccomponent.com">info@strategiccomponent.com</a></p></div>
<div class="fcol"><p><strong>Site</strong><br><a href="/inventory.html">Inventory</a><br><a href="/quality.html">Quality Assurance</a><br><a href="/terms.html">Terms</a><br><a href="/data-centers.html">Data Centers</a><br><a href="/contact.html">Contact</a></p></div></div>
<p class="fine">&copy; {datetime.date.today().year} Strategic Components, LLC. All rights reserved.</p>
<!-- TODO: add CAGE code and SAM registration here -->
</div></footer><script src="/assets/site.js"></script></body></html>'''

def write(path, content):
    full = os.path.join(ROOT, path.lstrip("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(content)

def jsonld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, separators=(",", ":")) + "</script>"

def row_html(it, rid=""):
    # The quote link points at plain /rfq.html so crawlers see one URL; site.js adds ?pn=&nsn= on hover/tap.
    alt = f'<small>Alt: {esc(it["alt"])}</small>' if it["alt"] else ""
    cage = f'<small>CAGE {esc(it["cage"])}</small>' if it["cage"] else ""
    idattr = f' id="{rid}"' if rid else ""
    return (f'<tr{idattr}><td class="m">{esc(it["nsn"])}</td><td class="m">{esc(it["pn"])}{alt}</td>'
            f'<td>{esc(it["mfg"])}{cage}</td><td>{esc(it["desc"])}</td><td>{esc(it["app"])}</td>'
            f'<td><a class="rq" href="/rfq.html" data-pn="{esc(it["pn"])}" data-nsn="{esc(it["nsn"])}" '
            f'aria-label="Request quote for {esc(it["pn"])}">Request quote</a></td></tr>')

THEAD = ('<thead><tr><th scope="col">NSN</th><th scope="col">Part number</th><th scope="col">Manufacturer</th>'
         '<th scope="col">Description</th><th scope="col">End use</th><th scope="col"><span class="sr">Action</span></th></tr></thead>')

SEARCH_FORM = ('<form class="find" action="/inventory.html" method="get" role="search"><label for="q">Search the catalog</label>'
               '<div><input id="q" name="q" placeholder="NSN, part number, description, end use" autocomplete="off" value="{v}">'
               '<button class="btn">Search</button></div></form>')

def page_url(i):
    return "/inventory.html" if i == 1 else f"/inventory/page-{i}.html"

# ---------------------------------------------------------------- build
def main():
    items, skipped, raw_n = load()
    n = len(items)
    today = datetime.date.today().isoformat()
    print(f"{raw_n} raw rows -> {n} listings ({skipped} without a part number skipped)")
    shutil.rmtree(os.path.join(ROOT, "inventory"), ignore_errors=True)

    pages = [items[i:i + PER_PAGE] for i in range(0, n, PER_PAGE)]
    total = len(pages)

    # Page 1 of the listing IS /inventory.html; pages 2+ live in /inventory/.
    for pi, chunk in enumerate(pages, 1):
        first, last = chunk[0]["pn"], chunk[-1]["pn"]
        path = page_url(pi)
        body_rows = "".join(row_html(it) for it in chunk)
        # unique descriptive text per page: most common item names on this page
        common = [d for d, _ in Counter(i["desc"] for i in chunk if i["desc"] and len(i["desc"]) <= 32).most_common(6)]
        common_txt = ", ".join(d.title() for d in common[:5])
        show = sorted({1, total, *range(max(1, pi - 2), min(total, pi + 2) + 1)})
        links, prev = [], 0
        for p in show:
            if p - prev > 1: links.append("<span>…</span>")
            cur = ' aria-current="page"' if p == pi else ""
            links.append(f'<a href="{page_url(p)}"{cur}>{p}</a>')
            prev = p
        pager = ('<nav class="pager" aria-label="Pages">'
                 + (f'<a rel="prev" href="{page_url(pi-1)}">Previous</a>' if pi > 1 else "")
                 + "".join(links)
                 + (f'<a rel="next" href="{page_url(pi+1)}">Next</a>' if pi < total else "")
                 + "</nav>")
        head_links = ""
        if pi > 1: head_links += f'<link rel="prev" href="{BASE}{page_url(pi-1)}">'
        if pi < total: head_links += f'<link rel="next" href="{BASE}{page_url(pi+1)}">'
        table = (f'<div class="scroll"><table><caption class="sr">Part numbers {esc(first)} to {esc(last)}</caption>'
                 f'{THEAD}<tbody>{body_rows}</tbody></table></div>\n{pager}')
        if pi == 1:
            title = "Inventory Catalog | Strat Com"
            meta = (f"Search and browse {n:,} defense and aerospace parts by NSN, part number, manufacturer, description or end use. "
                    "Submit a request for quote to Strategic Components, LLC.")
            body = f'''<section class="wrap pg"><h1>Inventory catalog</h1>
<p class="lede">{n:,} listings, sorted by part number. This page lists {esc(first)} to {esc(last)}, including {esc(common_txt)}. Pricing and availability are provided by quotation.</p>
{SEARCH_FORM.format(v="")}
<div id="results" aria-live="polite"></div>
<div id="browse">{table}</div></section>
<section class="reel" data-reel="48" aria-hidden="true"></section>'''
        else:
            title = f"Parts {first} to {last} | Strat Com"
            meta = (f"{len(chunk):,} defense and aerospace parts, part numbers {first} through {last}"
                    + (f", including {', '.join(d.title() for d in common[:3])}" if common else "")
                    + ". Submit a request for quote to Strategic Components, LLC.")
            head_links += jsonld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE + "/"},
                {"@type": "ListItem", "position": 2, "name": "Inventory", "item": BASE + "/inventory.html"},
                {"@type": "ListItem", "position": 3, "name": f"Parts {first} to {last}"}]})
            body = f'''<section class="wrap pg"><p class="crumb"><a href="/inventory.html">Inventory</a> / Page {pi} of {total}</p>
<h1>Parts {esc(first)} to {esc(last)}</h1>
<p class="lede">{len(chunk):,} listings, sorted by part number. Items on this page include {esc(common_txt)}. Pricing and availability are provided by quotation.</p>
{SEARCH_FORM.format(v="")}
{table}</section>
<section class="reel" data-reel="48" aria-hidden="true"></section>'''
        write(path, shell(path, title, meta, body, cur="/inventory.html", extra_head=head_links))

    # search index (public fields only)
    idx = [[i["pn"], i["alt"], i["nsn"], i["desc"], i["mfg"], i["cage"], i["app"]] for i in items]
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    with open(os.path.join(ROOT, "data", "search.json"), "w", encoding="utf-8") as f:
        json.dump(idx, f, separators=(",", ":"), ensure_ascii=False)

    # home
    org = jsonld({"@context": "https://schema.org", "@type": "Organization", "name": "Strat Com",
                  "legalName": "Strategic Components, LLC", "url": BASE + "/", "logo": BASE + "/assets/logo-box-512.png",
                  "email": "sales@strategiccomponent.com"})
    write("/index.html", shell("/index.html", "Strat Com | Aerospace and Defense Components",
        "Strategic Components, LLC supplies obsolete and hard-to-find components to the aerospace and defense industries, and continuous-service parts for AI data center applications. Search the catalog by NSN, part number or description and submit a request for quote.", f'''
<section class="hero photo"><div class="wrap"><h1>Obsolete and hard-to-find components for aerospace and defense</h1>
<p class="lede">Strategic Components, LLC supplies obsolete and hard-to-find components to the aerospace and defense industries. <span class="more">We are extending that supply to continuous-service parts for AI data center applications and the quick-start energy demands that follow. Search {n:,} catalog listings by NSN, part number or description, or submit a request for quote for any item not listed.</span></p>
{SEARCH_FORM.format(v="")}</div></section>
<section class="band"><div class="wrap"><h2>Capabilities</h2>
<p class="prose">Capabilities range from nuts and bolts, resistors and transistors, to fire control panels, swash plate assemblies and airframe components, and everything in between.</p>
<details class="fold" open><summary><h2>Markets</h2></summary>
<dl class="ruled"><dt>Aerospace and defense</dt><dd>Obsolete, discontinued and hard-to-find components, drawn from our own spare parts inventory and a network of trusted suppliers worldwide. See <a href="/quality.html">quality assurance</a>.</dd>
<dt>AI data center power</dt><dd>Parts for continuous service and for quick-start generation, including converted jet engines and aeroderivative turbines. See <a href="/data-centers.html">data centers</a>.</dd></dl></details>
<details class="fold" open><summary><h2>Procurement</h2></summary>
<dl class="ruled"><dt>Catalog</dt><dd>Each listing identifies the NSN, part number, manufacturer, description and end use.</dd>
<dt>Pricing</dt><dd>Pricing and availability are provided by quotation. Please submit the NSN or part number and the quantity required.</dd>
<dt>Requirements</dt><dd>Please indicate on the request whether it is for immediate purchase or in support of a government bid.</dd></dl></details></div></section>
<section class="pband"><div class="wrap"><h2>Sustaining American-built systems, legacy fleets to the future of power</h2><p>From the platforms that built the supply chain to the turbines that will power what comes next, we source the parts that keep them in service.</p></div></section>
<section class="cta"><div class="wrap"><h2>Item not listed in the catalog?</h2><a class="btn solid" href="/rfq.html">Request for quote</a></div></section>''',
        cur="/", extra_head=org, bp=False))

    write("/rfq.html", shell("/rfq.html", "Request for Quote | Strat Com",
        "Submit a request for quote to Strategic Components, LLC. Include the NSN or part number and the quantity required.", '''
<section class="wrap pg narrow"><h1>Request for quote</h1><p class="lede">Fields marked * are required. All quotations and sales are subject to our <a href="/terms.html">quote and sales terms</a>.</p>
<form id="rfq" novalidate>
<label>Name *<input name="name" required autocomplete="name"></label>
<label>Business name *<input name="business" required autocomplete="organization"></label>
<label>Email address *<input name="email" type="email" required autocomplete="email"></label>
<label>Phone number<input name="phone" type="tel" autocomplete="tel"></label>
<label>NSN or part number *<input name="part" required></label>
<label>Quantity requested *<input name="quantity" required inputmode="numeric"></label>
<label>Target price<input name="target_price" placeholder="Optional"></label>
<fieldset><legend>Reason for RFQ</legend><label class="chk"><input type="checkbox" name="reason" value="Immediate Purchase"> Immediate purchase</label>
<label class="chk"><input type="checkbox" name="reason" value="Government Bid"> Government bid</label>
<label class="chk"><input type="checkbox" name="reason" value="Other"> Other</label></fieldset>
<label>Additional information<textarea name="notes" rows="4" placeholder="Other reason, delivery requirements, additional part numbers"></textarea></label>
<input type="text" name="website" class="hp" tabindex="-1" autocomplete="off" aria-hidden="true">
<button class="btn solid" type="submit">Submit request</button><p id="status" role="status"></p></form></section>''', cur="/rfq.html"))

    write("/contact.html", shell("/contact.html", "Contact | Strat Com",
        "Contact Strategic Components, LLC (Strat Com) for quotations and general inquiries.", '''
<section class="wrap pg narrow"><h1>Contact</h1><p class="lede">Strategic Components, LLC, doing business as Strat Com.</p>
<dl class="ruled"><dt>Quotations and sales</dt><dd><a href="mailto:sales@strategiccomponent.com">sales@strategiccomponent.com</a></dd>
<dt>General inquiries</dt><dd><a href="mailto:info@strategiccomponent.com">info@strategiccomponent.com</a></dd>
<dt>Procurement</dt><dd><a href="mailto:procurement@strategiccomponent.com">procurement@strategiccomponent.com</a></dd>
<dt>Telephone</dt><dd><a href="tel:1-888-888-8888">1-888-888-8888</a></dd>
<dt>Address</dt><dd>2221 St. George Lane, Suite 7<br>Chico, CA 95926</dd>
</dl><p><a class="btn solid" href="/rfq.html">Request for quote</a></p></section>''', cur="/contact.html"))

    write("/terms.html", shell("/terms.html", "Quote and Sales Terms | Strat Com",
        "Terms for quotes and sales from Strategic Components, LLC: export controls, payment, condition, warranty, returns and repairs.",
        TERMS, cur="/terms.html"))

    write("/quality.html", shell("/quality.html", "Quality Assurance | Strat Com",
        "How Strategic Components, LLC verifies and backs its parts, and the private technical library behind our sourcing of obsolete and hard-to-find components.",
        QUALITY, cur="/quality.html"))

    write("/data-centers.html", shell("/data-centers.html", "AI Data Center Power Parts | Strat Com",
        "Continuous-service and quick-start parts for AI data center power: converted jet engines and aeroderivative turbines, seals, bearings, fuel and fluid components, gear boxes and more. Submit a request for quote.",
        DATACENTERS, cur="/data-centers.html"))

    # housekeeping files
    urls = ["/", "/inventory.html", "/rfq.html", "/quality.html", "/terms.html", "/contact.html", "/data-centers.html"] + [page_url(i) for i in range(2, total + 1)]
    write("/CNAME", "strategiccomponent.com\n")
    write("/.nojekyll", "")
    write("/.gitignore", "source/\n__pycache__/\n")
    write("/robots.txt", f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    write("/sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
          + "".join(f"<url><loc>{BASE}{u}</loc><lastmod>{today}</lastmod></url>" for u in urls) + "</urlset>\n")
    print(f"{len(urls)} URLs, {total} catalog pages of up to {PER_PAGE}")

# ---------------------------------------------------------------- terms page
TERMS = '''
<section class="wrap pg narrow terms"><h1>Quote and sales terms</h1>
<p>All quotes and sales made by Strategic Components, LLC (&ldquo;Strat Com&rdquo;) are subject to the following terms and conditions.</p>

<h2>Terms of sale</h2>
<ol class="clauses">
<li><strong>Orders and payment.</strong> The minimum order is $250. Payment terms are prepayment unless otherwise specified. A convenience fee of 3% applies to all orders paid by credit card. Past-due accounts are subject to a late charge of 1.5% per month.</li>
<li><strong>Delivery.</strong> All items are offered ex works from our shipping location, subject to prior sale and clerical error.</li>
<li><strong>Condition and certification.</strong> Items are offered in commercial New Surplus condition unless otherwise noted. New Surplus condition is certified visually as to kind, count, condition and identification number, and is accompanied by our certificate of conformance. Unless specifically noted, a quote does not include FAA 8130 certification or OEM trace documentation. An item quoted in AR condition has been used and may require repair or overhaul prior to installation. Any label copy furnished with a quote is representative only, and a quoted quantity may include additional contract numbers or manufacturers.</li>
<li><strong>Warranty and returns.</strong> Unless otherwise specified, items carry a 90-day warranty. Items must be examined within seven days of receipt, and an RMA number must be obtained from Strat Com before any return. Strat Com does not issue cash refunds; returns are eligible for exchange or credit only. Unless a return results from our error, a restocking fee of 50% applies to special order items and 25% to all other items.</li>
</ol>

<h2>Export controls</h2>
<p>Unless otherwise noted, a quote may include Munitions List Items (MLI) or Commerce Controlled List Items (CCLI). Such property is controlled by the U.S. Government and, in many cases, may not be transferred (exported, sold or given) to a foreign country, a non-U.S. citizen or national, or a non-permanent U.S. resident without a valid export authorization from the Department of State or the Department of Commerce. The purchaser is responsible for determining the applicable requirements and for obtaining all necessary authorizations, licenses and approvals.</p>
<p>The use, disposition, export and re-export of quoted items are subject to the provisions of law referenced in End-Use Certificate DLA Form 1822 (DEC 2001), including the Arms Export Control Act (22 USC 2751 et seq.); the Export Administration Act of 1979 (50 USC App. 2401 et seq.), as continued under Executive Order 12924; the International Traffic in Arms Regulations (22 CFR 120 et seq.); the Export Administration Regulations (15 CFR 730 et seq.); the Foreign Assets Control Regulations (31 CFR 500 et seq.); and the Espionage Act (18 USC 793 et seq.); together with all other applicable U.S. and international laws, orders, acts, agreements and regulations.</p>
<p>By accepting delivery, the purchaser represents and warrants that it is not an embassy or any agency or subdivision of a foreign government. A purchaser that is an embassy, or an agency or subdivision of a foreign government, must provide Strat Com with a copy of the State or Commerce Department license, or the license number, that permits it to receive and export the material.</p>

<p>Questions regarding a quote may be directed to <a href="mailto:sales@strategiccomponent.com">sales@strategiccomponent.com</a>.</p>
<p><a class="btn solid" href="/rfq.html">Request for quote</a></p></section>
<!-- TODO: replace "our shipping location" with the ship-from city and state once confirmed. -->
'''

DATACENTERS = '''
<section class="wrap pg narrow terms paper"><h1>Continuous-service parts for AI data center power</h1>
<p class="lede">Strat Com supplies obsolete and hard-to-find components to the aerospace and defense industries. We are extending that supply to the continuous-service and quick-start power equipment that AI data centers require, including converted jet engines and aeroderivative turbines. We supply parts and components, not complete engines or turbines.</p>

<h2>Continuous service</h2>
<p>A turbine that generates power often runs for long continuous periods, which brings inspection and overhaul intervals around regularly. We supply the wear items and consumables those events require, including seals, bearings, filters, igniters, fuel and fluid components and sensors.</p>

<h2>Quick-start power</h2>
<p>Aeroderivative units are valued for rapid start and modular installation, which leaves little schedule margin for a missing part. When lead times are long, we search our own spare parts inventory and a network of trusted suppliers around the world for obsolete, discontinued and hard-to-find parts. State the date you need delivery on the request, and we will respond promptly.</p>

<h2>Verification and documentation</h2>
<p>Each part is verified against its NSN and part number and is accompanied by a certificate of conformance. Items carry the warranty set out in our <a href="/terms.html">quote and sales terms</a>, and any documentation beyond the certificate of conformance is stated on each quotation. A mixed list covering engine, gear box, cooling, fluid, electrical and control items may be submitted as one request.</p>

<h2>What we supply</h2>
<dl class="ruled">
<dt>Turbine components</dt><dd>Blades, vanes, nozzles, liners, igniters, compressor and turbine components for gas turbine and aeroderivative engine assemblies.</dd>
<dt>Heat management</dt><dd>Coolers, heat exchangers, fans, blowers, thermostats and ducting for cooling and temperature control.</dd>
<dt>Fluid handling</dt><dd>Pumps, valves, manifolds, hoses, couplings, filters and accumulators for cooling and fuel systems.</dd>
<dt>Gear boxes and drives</dt><dd>Gear boxes, gears, bearings, seals, swash plate assemblies and power transmission components.</dd>
<dt>Electrical power</dt><dd>Transformers, circuit breakers, relays, contactors, generators, motors, converters and inverters.</dd>
<dt>Controls and sensing</dt><dd>Actuators, controllers, sensors, connectors and cable assemblies.</dd>
<dt>Related hardware</dt><dd>Structural components, airframe components, fasteners, electronic parts and control panels.</dd>
</dl>
<p>We will work with you to meet your needs, as they arise.</p>
<!-- TODO: confirm the categories above match the product lines to be advertised. -->

<h2 class="nonum">Request a quote</h2>
<p>We support engine converters and overhaul shops, developers and operators of on-site power, and the contractors who package and maintain it. Submit the part number or NSN, the engine or platform, the quantity and the date you need delivery. If you have only a description or a drawing, send that and we will source the part. You may also <a href="/inventory.html">search the inventory catalog</a>.</p>
<p><a class="btn solid" href="/rfq.html">Request for quote</a></p></section>
'''

# ---------------------------------------------------------------- quality page
QUALITY = '''
<section class="wrap pg narrow terms paper"><h1>Quality assurance</h1>
<p>The Strat Com sourcing department specializes in the procurement of obsolete and discontinued components. We draw on our own spare parts inventory and a network of trusted suppliers around the world, and we support dozens of OEMs. Capabilities range from nuts and bolts, resistors and transistors, to fire control panels, swash plate assemblies and airframe components, and everything in between.</p>

<h2 class="nonum">Verification and quality control</h2>
<p>Each part we supply is covered by a warranty of at least 90 days, as set out in our <a href="/terms.html">quote and sales terms</a>. Before delivery, every part undergoes in-house verification of its NSN and part number against the Federal Logistics Information Service database, at no charge to the purchaser, together with quality assurance review and signature testing. Each part is accompanied by a certificate of conformance.</p>

<h2 class="nonum">Technical library</h2>
<p>Strat Com maintains a private technical library that is among the most extensive in the industry, covering a wide range of aircraft and engines. The library includes prints and drawings, technical orders, overhaul manuals, work scopes, instructional data, Time Compliance Technical Orders and illustrated parts manuals. It also holds kit information, including cure-date kits, overhaul kits and quick engine change kits.</p>
<p>We hold technical support data for McDonnell Douglas and General Electric products, which assists us in resolving engineering questions as they arise, and we maintain resources to remain informed of modifications and new technology.</p>

<p>To request a quotation, submit the NSN or part number.</p>
<p><a class="btn solid" href="/rfq.html">Request for quote</a></p></section>
'''

main()
