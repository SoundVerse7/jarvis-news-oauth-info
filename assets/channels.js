(function() {
  "use strict";
  var container = document.getElementById("latest-video-grid");
  var home = document.getElementById("home-videos");
  if (!container && !home) return;
  var stamp = document.getElementById("video-update-status");
  var tabs = document.querySelectorAll("[data-video-channel]");
  var selected = "All";
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
        choice.slice(0,4).forEach(function(item){home.appendChild(buildCard(item));});
      }
    }
  }
  tabs.forEach(function(btn){
    btn.addEventListener("click",function(){
      selected=btn.dataset.videoChannel;
      tabs.forEach(function(x){x.setAttribute("aria-pressed",x===btn?"true":"false");});
      render();
    });
  });
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
        stamp.textContent="Public video feed checked "+dateLabel(json.updated_at);
      }
      render();
    } catch(err) {
      if (stamp) stamp.textContent="Video preview feed temporarily unavailable";
      render();
    }
  }
  render();load();
})();