(function() {
  "use strict";
  var state = {items:[], filter:"All", search:"", visible:9};
  var ticker = document.getElementById("headline-ticker");
  var tickerSource = document.getElementById("ticker-source");
  var featured = document.getElementById("featured-news");
  var cards = document.getElementById("stories");
  var stamp = document.getElementById("last-checked");
  var more = document.getElementById("show-more");
  var input = document.getElementById("news-search");
  var tabs = document.querySelectorAll("[data-category]");

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (typeof text === "string") node.textContent = text;
    return node;
  }
  function safeLink(url) {
    try {
      var parsed = new URL(url);
      return parsed.protocol === "https:" ? parsed.href : null;
    } catch (e) { return null; }
  }
  function dateLabel(iso) {
    var dt = new Date(iso);
    if (!isFinite(dt.getTime())) return "Date unavailable";
    return dt.toLocaleDateString("en-CA", {year:"numeric",month:"short",day:"numeric",timeZone:"UTC"});
  }
  function externalLink(url, title, klass) {
    var a = el("a", klass, title);
    a.href = safeLink(url) || "#news";
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    return a;
  }
  function byline(item) {
    var p = el("p", "byline");
    p.appendChild(el("span", "", item.source));
    p.appendChild(document.createTextNode(" · " + dateLabel(item.published)));
    return p;
  }
  function article(item, isFeature) {
    var block = el(isFeature ? "div" : "article", isFeature ? "feature-copy" : "story");
    block.appendChild(el("span", "article-tag", item.category));
    var heading = el("h3");
    heading.appendChild(externalLink(item.url, item.title));
    block.appendChild(heading);
    block.appendChild(byline(item));
    block.appendChild(externalLink(item.url, "Read at original source ↗", "source-link"));
    return block;
  }
  function render() {
    var query = state.search.trim().toLowerCase();
    var filtered = state.items.filter(function(item) {
      return (state.filter === "All" || state.filter === item.category) &&
        (!query || [item.title,item.source,item.category].join(" ").toLowerCase().indexOf(query) !== -1);
    });
    featured.replaceChildren();
    cards.replaceChildren();
    if (filtered.length === 0) {
      featured.hidden = true;
      cards.appendChild(el("div", "empty", state.items.length ?
        "No headlines match your filters. Try another category or search." :
        "The automated news feed is not populated yet. You can still read the original sources linked below."));
    } else {
      featured.hidden = false;
      var design = el("div", "feature-design");
      var logo = document.createElement("img");
      logo.src = "assets/pm-emblem.svg";
      logo.alt = "";
      logo.width = 230;
      logo.height = 230;
      logo.style.cssText = "width:230px;opacity:.8";
      design.appendChild(logo);
      featured.appendChild(design);
      featured.appendChild(article(filtered[0], true));
      filtered.slice(1, state.visible + 1).forEach(function(item){ cards.appendChild(article(item, false)); });
    }
    more.hidden = filtered.length <= state.visible + 1;
  }
  tabs.forEach(function(tab) {
    tab.addEventListener("click", function() {
      state.filter = tab.dataset.category;
      state.visible = 9;
      tabs.forEach(function(x){x.setAttribute("aria-pressed", x===tab ? "true" : "false");});
      render();
    });
  });
  input.addEventListener("input", function(){state.search = input.value; state.visible = 9; render();});
  more.addEventListener("click", function(){state.visible += 9; render();});
  async function load() {
    try {
      // Read the current public repository snapshot, even when GitHub Pages has
      // not rebuilt after an automated GITHUB_TOKEN commit. GitHub's public
      // Contents API permits CORS; rate-limited failures fall back to Pages.
      var json;
      try {
        var current = await fetch("https://api.github.com/repos/SoundVerse7/jarvis-news-oauth-info/contents/data/headlines.json?ref=main", {cache:"no-cache",headers:{"Accept":"application/vnd.github+json"}});
        if (!current.ok) throw new Error("GitHub API "+current.status);
        var wrapper = await current.json();
        if (wrapper.encoding !== "base64" || typeof wrapper.content !== "string") throw new Error("Invalid contents response");
        var bytes = Uint8Array.from(atob(wrapper.content.replace(/\s/g, "")), function(c){return c.charCodeAt(0);});
        json = JSON.parse(new TextDecoder("utf-8").decode(bytes));
      } catch(feedApiError) {
        var response = await fetch("data/headlines.json", {cache:"no-cache"});
        if (!response.ok) throw new Error("HTTP "+response.status);
        json = await response.json();
      }
      if (!json || !Array.isArray(json.items)) throw new Error("Unexpected feed format");
      state.items = json.items.filter(function(x) {
        return x && typeof x.title === "string" && typeof x.url === "string" &&
           safeLink(x.url) && typeof x.source === "string" &&
           ["World","Economy","Energy"].indexOf(x.category) !== -1;
      });
      // The feed is refreshed periodically; it is never a live news alert service.
      // Source outages and old cached snapshots must be visible to readers.
      var feedDate = json.updated_at ? new Date(json.updated_at) : null;
      var validDate = feedDate && isFinite(feedDate.getTime());
      var delayed = validDate && (Date.now() - feedDate.getTime()) > 8 * 60 * 60 * 1000;
      var failedSources = Array.isArray(json.sources) ? json.sources
        .filter(function(s){return s && s.status !== "ok" && typeof s.source === "string";})
        .map(function(s){return s.source;}) : [];
      if (validDate) {
        var when = feedDate.toLocaleString("en-CA", {dateStyle:"medium",timeStyle:"short",timeZone:"UTC",timeZoneName:"short"});
        var status = "Last checked " + when;
        if (failedSources.length) status += " · Source delayed: " + failedSources.join(", ");
        if (delayed) status += " · Updates delayed";
        stamp.textContent = status;
      } else {
        stamp.textContent = "Feed update time unavailable — see original publishers";
      }
      if (state.items.length) {
        ticker.textContent = state.items[0].title;
        ticker.href = safeLink(state.items[0].url);
        tickerSource.textContent = state.items[0].source;
      }
      render();
    } catch(err) {
      stamp.textContent = "Feed temporarily unavailable — please visit the original sources";
      render();
    }
  }
  render();
  load();
})();