(function () {
  function normalize(s) { return (s || "").toString().toLowerCase(); }

  document.addEventListener("DOMContentLoaded", function () {
    var input = document.getElementById("filter");
    var table = document.getElementById("weapons-table");
    if (!input || !table) return;

    input.addEventListener("input", function () {
      var q = normalize(input.value);
      Array.from(table.tBodies[0].rows).forEach(function (tr) {
        var text = normalize(tr.innerText);
        tr.style.display = text.indexOf(q) >= 0 ? "" : "none";
      });
    });
  });
})();
