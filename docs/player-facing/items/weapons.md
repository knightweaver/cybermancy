# Weapons

Type to filter:
<input id="filter" placeholder="Filter by name, category, domain, rarity" />

<table id="weapons-table">
  <thead>
    <tr>
      <th>Name</th>
      <th>Category</th>
      <th>Damage</th>
      <th>Range</th>
      <th>Rarity</th>
      <th>Domain</th>
    </tr>
  </thead>
  <tbody>
{% for w in load_csv('data/weapons.csv') %}
    <tr>
      <td><a href="./{{ w.slug }}/">{{ w.name }}</a></td>
      <td>{{ w.category }}</td>
      <td>{{ w.damage }}</td>
      <td>{{ w.range }}</td>
      <td>{{ w.rarity }}</td>
      <td>{{ w.domain }}</td>
    </tr>
{% endfor %}
  </tbody>
</table>

---

> Click any name to view full details.
