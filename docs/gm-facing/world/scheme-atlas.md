# Scheme Atlas — GM

Explore the Council, Cabal, and corporate schemes. Select an identifier to expand its immediate neighborhood and read its objectives, mission hooks, rumors, and player knowledge. This atlas is read-only; update its repository data through the campaign conversation.

<div id="scheme-atlas" data-source="../../assets/schemes/schemes.json">
  <div class="sa-toolbar">
    <label>Search <input type="search" data-sa="search" placeholder="Identifier, title, or details" /></label>
    <label>Entity <select data-sa="entity"><option value="">All entities</option></select></label>
    <label>Location <select data-sa="location"><option value="">All locations</option><option value="unassigned">No specific location recorded</option></select></label>
    <label>Awareness <select data-sa="awareness"><option value="">All schemes</option><option value="queued">Queued for introduction</option><option value="revealed">Revealed to players</option><option value="unrevealed">Not revealed</option></select></label>
    <label>Approval <select data-sa="approval"><option value="">All approvals</option><option value="approved">Approved</option><option value="proposed">Proposed</option><option value="retired">Retired</option></select></label>
    <fieldset data-sa="types"><legend>Relationships</legend></fieldset>
    <div class="sa-actions">
      <button type="button" data-sa="overview">Overview</button>
      <button type="button" data-sa="neighbors" aria-pressed="false">Selected + neighbors</button>
      <button type="button" data-sa="all-related">Show all related</button>
      <button type="button" data-sa="fit">Fit view</button>
      <button type="button" data-sa="minus" aria-label="Zoom out">−</button>
      <button type="button" data-sa="plus" aria-label="Zoom in">+</button>
      <button type="button" data-sa="panel" aria-expanded="true">Hide details</button>
      <button type="button" data-sa="fullscreen" aria-pressed="false">Full screen</button>
    </div>
  </div>
  <div class="sa-layout">
    <div class="sa-graph-column">
      <div class="sa-graph" data-sa="graph">
        <svg data-sa="svg" role="group" aria-label="Scheme relationship graph. Tab to nodes; Enter selects; Escape clears selection." tabindex="0"><g data-sa="scene"></g></svg>
      </div>
      <p class="sa-status" data-sa="status" role="status">Loading scheme atlas…</p>
    </div>
    <div class="sa-divider" data-sa="resize" role="separator" tabindex="0" aria-orientation="vertical" aria-label="Resize details panel" title="Drag to resize details; Left widens, Right narrows"></div>
    <aside id="sa-details" class="sa-panel" data-sa="details" aria-label="Selected scheme details" aria-live="polite"><h2>Select a scheme</h2><p>Colored identifiers represent entities. Select a node to expand it and its immediate neighbors. Drag the background to pan; scroll to zoom.</p></aside>
  </div>
  <div class="sa-legend" data-sa="legend"></div>
  <p class="sa-help">→ Directs/supports · ⇢ Exploits · ⊣ Opposes · blocking bars at both ends: Competes. Dashed links distinguish exploitation and competition; hover or focus a link for its label and conditions. ◆ Queued · ● Revealed. Drag the divider beside Details to adjust its width, or focus it and use Left/Right arrows (Shift for larger steps).</p>
  <noscript>The scheme atlas requires JavaScript. Its canonical data is in the GM scheme data file.</noscript>
</div>

[Scheme data and editing guide](scheme-atlas-workflow.md)
