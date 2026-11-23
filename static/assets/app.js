// Lite YouTube player: shows the thumbnail and loads YouTube only when clicked.
// Chapter / timestamp links jump the player to that time.
(function () {
  function src(id, start, autoplay) {
    return "https://www.youtube-nocookie.com/embed/" + id +
      "?enablejsapi=1&rel=0&modestbranding=1&playsinline=1" +
      (autoplay ? "&autoplay=1" : "") + (start ? "&start=" + start : "");
  }
  function load(p, start) {
    var f = p.querySelector("iframe");
    if (f) {
      f.contentWindow.postMessage(JSON.stringify({ event: "command", func: "seekTo", args: [start || 0, true] }), "*");
      f.contentWindow.postMessage(JSON.stringify({ event: "command", func: "playVideo", args: [] }), "*");
      return;
    }
    f = document.createElement("iframe");
    f.src = src(p.dataset.id, start, true);
    f.title = (p.querySelector("img") || {}).alt || "YouTube video";
    f.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
    f.allowFullscreen = true;
    p.appendChild(f);
  }
  document.querySelectorAll(".player").forEach(function (p) {
    p.addEventListener("click", function () { if (!p.querySelector("iframe")) load(p, 0); });
  });
  document.addEventListener("click", function (e) {
    var a = e.target.closest("a.ts");
    if (!a) return;
    var p = document.querySelector(".player");
    if (!p) return;
    e.preventDefault();
    load(p, parseInt(a.dataset.t, 10));
    p.scrollIntoView({ behavior: "smooth", block: "center" });
  });
  // Deep link: page#t=90 starts at 1:30
  var m = location.hash.match(/^#t=(\d+)$/);
  if (m) { var p = document.querySelector(".player"); if (p) load(p, parseInt(m[1], 10)); }
})();
