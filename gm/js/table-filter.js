(function () {
  function normalize(s) { return (s || "").toString().toLowerCase(); }

  document.addEventListener("DOMContentLoaded", function () {
    var inputs = Array.from(document.querySelectorAll("input[data-filter-table]"));

    // Backward compatibility for older pages that use #filter without data-filter-table.
    if (!inputs.length) {
      var legacyInput = document.getElementById("filter");
      if (legacyInput) inputs = [legacyInput];
    }

    inputs.forEach(function (input) {
      var tableId = input.getAttribute("data-filter-table") || "adversaries-features-table";
      var table = document.getElementById(tableId);
      if (!table || !table.tBodies || !table.tBodies.length) return;

      input.addEventListener("input", function () {
        var q = normalize(input.value);
        Array.from(table.tBodies[0].rows).forEach(function (tr) {
          var text = normalize(tr.innerText);
          tr.style.display = text.indexOf(q) >= 0 ? "" : "none";
        });
      });
    });
  });
})();
