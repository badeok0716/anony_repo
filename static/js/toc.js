/* Left-rail contents: highlight the section currently at the top of the viewport. */
(function () {
  "use strict";
  const links = Array.from(document.querySelectorAll(".page-toc a"));
  if (!links.length || !("IntersectionObserver" in window)) return;
  const byId = {};
  links.forEach((a) => { byId[a.getAttribute("href").slice(1)] = a; });
  const setActive = (id) => links.forEach((a) => a.classList.toggle("is-active", a === byId[id]));
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => { if (e.isIntersecting) setActive(e.target.id); });
  }, { rootMargin: "0px 0px -85% 0px", threshold: 0 });
  Object.keys(byId).forEach((id) => { const el = document.getElementById(id); if (el) io.observe(el); });
})();
