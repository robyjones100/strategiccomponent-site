(function () {
  // Set FORM_ENDPOINT to your Google Apps Script web app URL. Empty = opens an email draft instead.
  var CONFIG = { FORM_ENDPOINT: "https://script.google.com/macros/s/AKfycbwaoGhhXa61AfJR_bkDOO1aXdvzjHKAI7llOd8IFqcPLzyRKyXikQCLJ8CAQlCre13wQw/exec", FALLBACK_EMAIL: "sales@strategiccomponent.com" };
  var qs = new URLSearchParams(location.search);
  var LIMIT = 200;

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function alnum(s) { return s.toLowerCase().replace(/[^a-z0-9]/g, ""); }

  // ---- quote links: plain /rfq.html in the HTML (one URL for crawlers); the part is added when a person reaches for the link
  function fillQuote(e) {
    var a = e.target.closest && e.target.closest("a.rq");
    if (!a || a.dataset.set) return;
    var u = "/rfq.html?pn=" + encodeURIComponent(a.dataset.pn || "") + (a.dataset.nsn ? "&nsn=" + encodeURIComponent(a.dataset.nsn) : "");
    a.setAttribute("href", u); a.dataset.set = "1";
  }
  ["pointerover", "focusin", "touchstart", "click"].forEach(function (ev) { document.addEventListener(ev, fillQuote, { capture: true, passive: true }); });

  // ---- catalog search (hub page only)
  var results = document.getElementById("results");
  if (results) {
    var input = document.getElementById("q"), browse = document.getElementById("browse");
    var data = null, hay = null, loading = null;
    function load() {
      if (loading) return loading;
      results.innerHTML = "<p>Loading catalog…</p>";
      loading = fetch("/data/search.json").then(function (r) { return r.json(); }).then(function (d) {
        data = d;
        hay = d.map(function (r) {
          return (r.join(" ").toLowerCase()) + "|" + alnum(r[0]) + " " + alnum(r[1]) + " " + alnum(r[2]);
        });
      });
      return loading;
    }
    function row(r) {
      return "<tr><td class=m>" + esc(r[2]) + "</td><td class=m>" + esc(r[0]) + (r[1] ? "<small>Alt: " + esc(r[1]) + "</small>" : "") +
        "</td><td>" + esc(r[4]) + (r[5] ? "<small>CAGE " + esc(r[5]) + "</small>" : "") + "</td><td>" + esc(r[3]) + "</td><td>" + esc(r[6]) +
        '</td><td><a class="rq" href="/rfq.html" data-pn="' + esc(r[0]) + '" data-nsn="' + esc(r[2]) + '" aria-label="Request quote for ' + esc(r[0]) + '">Request quote</a></td></tr>';
    }
    function run() {
      var q = input.value.trim();
      if (!q) { results.innerHTML = ""; browse.hidden = false; return; }
      browse.hidden = true;
      load().then(function () {
        var toks = q.toLowerCase().split(/\s+/).filter(Boolean);
        var first = alnum(toks[0]), hits = [];
        for (var i = 0; i < data.length; i++) {
          var ok = true;
          for (var t = 0; t < toks.length; t++) {
            var tn = alnum(toks[t]);
            if (hay[i].indexOf(toks[t]) < 0 && !(tn.length >= 3 && hay[i].indexOf(tn) >= 0)) { ok = false; break; }
          }
          if (ok) {
            var pn = alnum(data[i][0]), s = 2;
            if (pn === first || alnum(data[i][2]) === first) s = 0; else if (pn.indexOf(first) === 0) s = 1;
            hits.push([s, i]);
          }
        }
        hits.sort(function (a, b) { return a[0] - b[0] || a[1] - b[1]; });
        if (!hits.length) {
          results.innerHTML = '<p>No listings match “' + esc(q) + '”. <a href="/rfq.html">Submit a request for quote</a> and we will source the item.</p>';
          return;
        }
        var shown = hits.slice(0, LIMIT);
        results.innerHTML = "<p>" + hits.length.toLocaleString() + " matching listings" +
          (hits.length > LIMIT ? " (showing the first " + LIMIT + "; add more words to narrow)" : "") +
          '</p><div class="scroll"><table><thead><tr><th>NSN</th><th>Part number</th><th>Manufacturer</th><th>Description</th><th>End use</th><th><span class="sr">Action</span></th></tr></thead><tbody>' +
          shown.map(function (h) { return row(data[h[1]]); }).join("") + "</tbody></table></div>";
      }).catch(function () {
        results.innerHTML = "<p>Search is temporarily unavailable. Use the page links below or email sales@strategiccomponent.com.</p>";
        browse.hidden = false;
      });
    }
    input.value = qs.get("q") || "";
    var form = input.form;
    form.addEventListener("submit", function (e) { e.preventDefault(); history.replaceState(null, "", input.value ? "?q=" + encodeURIComponent(input.value) : location.pathname); run(); });
    var timer;
    input.addEventListener("input", function () { clearTimeout(timer); timer = setTimeout(run, 250); });
    input.addEventListener("focus", load, { once: true });
    if (input.value) run();
  }

  // ---- RFQ form
  var f = document.getElementById("rfq");
  if (f) {
    var pn = qs.get("pn"), nsn = qs.get("nsn");
    if (pn || nsn) f.part.value = pn && nsn ? nsn + " / " + pn : (pn || nsn);
    f.addEventListener("submit", function (e) {
      e.preventDefault();
      var s = document.getElementById("status");
      if (f.website.value) return;
      if (!f.checkValidity()) { f.reportValidity(); return; }
      var d = new FormData(f); d.delete("website");
      var reason = d.getAll("reason").join(", "); d.delete("reason"); d.set("reason", reason);
      if (CONFIG.FORM_ENDPOINT) {
        s.textContent = "Submitting…";
        fetch(CONFIG.FORM_ENDPOINT, { method: "POST", mode: "no-cors", body: new URLSearchParams(d) })
          .then(function () { f.reset(); s.textContent = "Your request has been submitted. We will respond by email."; })
          .catch(function () { s.textContent = "The request could not be submitted. Please email " + CONFIG.FALLBACK_EMAIL + " directly."; });
      } else {
        var t = ""; d.forEach(function (v, k) { t += k + ": " + v + "\n"; });
        location.href = "mailto:" + CONFIG.FALLBACK_EMAIL + "?subject=" + encodeURIComponent("RFQ: " + d.get("part")) + "&body=" + encodeURIComponent(t);
        s.textContent = "Your email application should open with the request completed.";
      }
    });
  }
})();
