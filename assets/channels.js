(function() {
  "use strict";
  var container = document.getElementById("latest-video-grid");
  var home = document.getElementById("home-videos");
  var library = document.getElementById("video-library");
  var search = document.getElementById("video-search");
  var showMore = document.getElementById("video-show-more");
  if (!container && !home && !library) return;
  var stamp = document.getElementById("video-update-status");
  var tabs = document.querySelectorAll("[data-video-channel]");
  var selected = "All";
  var query = "";
  var visible = 12;
  var items = [];
  var names = {original:"PUBLIC MIND REPORT",news:"WORLD NEWS"};
  var ids = {original:"UCAVVVfl6qdT1JZsndhyhetA",news:"UCc3QJDTVAvImoGQSHOHTu3Q"};
  var videoIdPattern = /^[A-Za-z0-9_-]{11}$/;
  function el(tag, klass, text) {
    var node = document.createElement(tag);
    if (klass) node.className = klass;
    if (typeof text === "string") node.textContent = text;
    return node;
  }
  function dateLabel(iso) {
    var n = new Date(iso);
    return isFinite(n.getTime()) ? n.toLocaleDateString("en-CA",{year:"numeric",month:"short",day:"numeric"}) : "";
  }
  function buildCard(item) {
    var videoId = item.video_id;
    var url = "https://www.youtube.com/watch?v=" + encodeURIComponent(videoId);
    var card = el("article","video-item");
    var thumbnailLink = el("a","video-thumb-link");
    thumbnailLink.href = url;
    thumbnailLink.target = "_blank";
    thumbnailLink.rel = "noopener noreferrer";
    thumbnailLink.setAttribute("aria-label","Watch on YouTube: " + item.title);
    var img = el("img");
    img.src = "https://i.ytimg.com/vi/" + videoId + "/hqdefault.jpg";
    img.loading = "lazy";
    img.alt = "YouTube video thumbnail: " + item.title;
    img.width = 480; img.height = 270;
    thumbnailLink.appendChild(img);
    card.appendChild(thumbnailLink);
    var copy = el("div","video-copy");
    copy.appendChild(el("span","article-tag",names[item.channel]));
    var h = el("h3");
    var a = el("a","",item.title);
    a.href = url; a.target = "_blank"; a.rel = "noopener noreferrer";
    h.appendChild(a);
    copy.appendChild(h);
    copy.appendChild(el("p","byline",dateLabel(item.published)+" · YouTube"));
    var actions = el("div", "video-actions");
    var watch = el("a", "video-watch", "Watch on YouTube ↗");
    watch.href = url;
    watch.target = "_blank";
    watch.rel = "noopener noreferrer";
    actions.appendChild(watch);
    var share = el("button", "video-share", "Share video");
    share.type = "button";
    share.setAttribute("aria-label", "Share: " + item.title);
    share.addEventListener("click", async function() {
      try {
        if (navigator.share) {
          await navigator.share({title:item.title,url:url});
        } else if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(url);
          share.textContent = "Link copied";
          window.setTimeout(function() {share.textContent = "Share video";}, 2200);
        } else {
          share.textContent = "Open video to share";
        }
      } catch (err) {
        if (err && err.name === "AbortError") return;
        share.textContent = "Open video to share";
      }
    });
    actions.appendChild(share);
    copy.appendChild(actions);
    card.appendChild(copy);
    return card;
  }
  function showEmpty(root, message) {
    root.replaceChildren(el("p","empty",message));
  }
  function render() {
    if (container) {
      var list = items.filter(function(x){return selected==="All"||x.channel===selected;}).slice(0,12);
      container.replaceChildren();
      if (!list.length) {
        showEmpty(container, "No public videos are available in this feed yet. Open the channel links above to watch directly on YouTube.");
      } else {
        list.forEach(function(item){container.appendChild(buildCard(item));});
      }
    }
    if (library) {
      library.replaceChildren();
      var q = query.trim().toLowerCase();
      var matches = items.filter(function(item) {
        return (selected === "All" || item.channel === selected) &&
          (!q || (item.title + " " + names[item.channel]).toLowerCase().indexOf(q) >= 0);
      });
      if (matches.length === 0) {
        showEmpty(library, items.length ?
          "No videos match your search. Try another word or channel." :
          "YouTube's public feed has no available videos yet. Visit either channel directly to watch.");
      } else {
        matches.slice(0,visible).forEach(function(item) {library.appendChild(buildCard(item));});
      }
      if (showMore) showMore.hidden = matches.length <= visible;
    }
    if (home) {
      home.replaceChildren();
      if (!items.length) {
        showEmpty(home,"Recent-video previews are currently unavailable. Open either YouTube channel using the links above.");
      } else {
        // Promote both channels even if the original channel posts more often.
        var choice = [];
        ["original","news"].forEach(function(channel) {
          var video = items.find(function(item){return item.channel===channel;});
          if (video) choice.push(video);
        });
        items.forEach(function(item) {
          if (choice.length < 4 && !choice.some(function(x){return x.video_id===item.video_id;})) choice.push(item);
        });
        choice.sort(function(a,b){return b.published.localeCompare(a.published);});
        choice.slice(0,4).forEach(function(item){home.appendChild(buildCard(item));});
      }
    }
  }
  tabs.forEach(function(btn){
    btn.addEventListener("click",function(){
      selected=btn.dataset.videoChannel;
      visible=12;
      tabs.forEach(function(x){x.setAttribute("aria-pressed",x===btn?"true":"false");});
      render();
    });
  });
  if (search) search.addEventListener("input",function() {query=search.value;visible=12;render();});
  if (showMore) showMore.addEventListener("click",function() {visible+=12;render();});
  async function load() {
    var json;
    try {
      try {
        var req = await fetch("https://api.github.com/repos/SoundVerse7/jarvis-news-oauth-info/contents/data/videos.json?ref=main", {
          cache:"no-cache",headers:{"Accept":"application/vnd.github+json"}
        });
        if (!req.ok) throw new Error("GitHub feed currently unavailable");
        var wrapper = await req.json();
        if (wrapper.encoding!=="base64"||typeof wrapper.content!=="string") throw new Error("Bad response");
        var binary = atob(wrapper.content.replace(/\s/g,""));
        var bytes = Uint8Array.from(binary,function(c){return c.charCodeAt(0);});
        json=JSON.parse(new TextDecoder("utf-8").decode(bytes));
      } catch(ghError) {
        var response=await fetch("data/videos.json",{cache:"no-cache"});
        if (!response.ok) throw new Error("No video snapshot");
        json=await response.json();
      }
      if (!json||!Array.isArray(json.items)) throw new Error("Bad video data");
      items=json.items.filter(function(v){
        return v && (v.channel==="original"||v.channel==="news") &&
          typeof v.video_id==="string" && videoIdPattern.test(v.video_id) &&
          typeof v.title==="string"&&v.title.length>0 &&
          typeof v.published==="string";
      }).slice(0,24);
      if (stamp && json.updated_at) {
        var checked = new Date(json.updated_at);
        var status = "Public video feed checked " + dateLabel(json.updated_at);
        if (isFinite(checked.getTime()) && Date.now()-checked.getTime() > 6*3600*1000)
          status += " · Updates delayed";
        var failures = Array.isArray(json.status) ? json.status.filter(function(x){return x.status!=="ok";}) : [];
        if (failures.length) {
          var namesOfFailed = failures.map(function(x){return x.channel==="original" ? "Public Mind Report" : x.channel==="news" ? "World News" : "Unknown";});
          status += " · Saved video list shown; update unavailable for: " + namesOfFailed.join(", ");
          var lastTimes = failures.map(function(x){return x.last_success_at ? new Date(x.last_success_at) : null;})
            .filter(function(t){return t && isFinite(t.getTime());});
          if (lastTimes.length) {
            var earliest = new Date(Math.min.apply(null,lastTimes.map(function(t){return t.getTime();})));
            status += " · Last confirmed " + dateLabel(earliest.toISOString());
          }
        }
        stamp.textContent=status;
      }
      render();
    } catch(err) {
      if (stamp) stamp.textContent="Video preview feed temporarily unavailable";
      render();
    }
  }
  render();load();
})();