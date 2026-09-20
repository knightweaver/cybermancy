# Seattle Atlas

<p class="atlas-intro">
  A player-safe orientation map of the surviving Puget Sound corridor. Its borders represent
  Cybermancy geography rather than contemporary administrative boundaries.
</p>

<div
  id="cybermancy-atlas"
  class="cybermancy-atlas"
  data-regions="../../assets/atlas/regions.geojson"
  data-districts="../../assets/atlas/districts.geojson"
  data-context="../../assets/atlas/context.geojson"
  data-atlas-mode="player"
>
  <div class="atlas-toolbar" aria-label="Map view controls">
    <div>
      <span class="atlas-eyebrow">PUBLIC CARTOGRAPHY // REV 1</span>
      <h2>Puget Sound Survival Atlas</h2>
    </div>
    <div class="atlas-toolbar-actions">
      <a
        class="atlas-popout"
        href="?atlas=fullscreen"
        target="_blank"
        rel="noopener"
        aria-label="Open the Seattle Atlas in a full-sized new tab"
      >Open full atlas <span aria-hidden="true">↗</span></a>
      <div class="atlas-view-switcher" role="group" aria-label="Select map extent">
        <button type="button" data-atlas-view="regional" aria-pressed="true">Regional</button>
        <button type="button" data-atlas-view="seattle" aria-pressed="false">Seattle</button>
      </div>
    </div>
  </div>

  <div class="atlas-layout">
    <div class="atlas-map-column">
      <div id="cybermancy-atlas-map" class="atlas-map" aria-label="Interactive map of Cybermancy Seattle"></div>
      <p class="atlas-map-note">
        Draft fictional boundaries. Select a colored region or use the legend for details.
      </p>
    </div>

    <aside id="cybermancy-atlas-panel" class="atlas-panel" aria-live="polite">
      <div class="atlas-hero" aria-hidden="true">
        <span id="atlas-hero-code">SEA // 01</span>
      </div>
      <div class="atlas-panel-copy">
        <span id="atlas-category" class="atlas-eyebrow">REGIONAL OVERVIEW</span>
        <h2 id="atlas-name">The Puget Sound Corridor</h2>
        <p id="atlas-description">
          Three surviving city-states and their contested approaches are linked by guarded roads,
          ferries, maritime trade, and corporate necessity.
        </p>
        <dl id="atlas-facts" class="atlas-facts"></dl>
        <div id="cybermancy-atlas-inset" class="atlas-inset" aria-label="Selected area detail map"></div>
      </div>
    </aside>
  </div>

  <section class="atlas-legend-section" aria-labelledby="atlas-legend-title">
    <div>
      <span class="atlas-eyebrow">VISIBLE TERRITORIES</span>
      <h2 id="atlas-legend-title">Map legend</h2>
    </div>
    <div class="atlas-legend-stack">
      <div id="cybermancy-atlas-legend" class="atlas-legend"></div>
      <div
        id="cybermancy-atlas-poi-key"
        class="atlas-poi-key"
        aria-label="Map context categories"
      ></div>
    </div>
  </section>

  <noscript>This interactive atlas requires JavaScript.</noscript>
</div>

[OpenFreeMap](https://openfreemap.org/) © OpenMapTiles; map data © OpenStreetMap contributors. Cybermancy boundaries and setting descriptions are fictional.
