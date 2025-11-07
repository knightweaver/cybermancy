# Weapons

Type to filter:
<input id="filter" placeholder="Filter by name, category, domain, rarity" />

<table id="weapons-table">
  <thead>
    <tr>
      <th>Name</th>
      <th>Description</th>
      <th>Tier</th>
      <th>Trait</th>
      <th>Range</th>
      <th>Burden</th>
      <th>Damage</th>
    </tr>
  </thead>
  <tbody>
{% for w in load_csv('../data/weapons.csv') %}
    <tr>
      <td><a href="./{{ w.slug }}/">{{ w.name }}</a></td>
      <td>{{ w.description }}</td>
      <td>{{ w.tier }}</td>
      <td>{{ w.trait }}</td>
      <td>{{ w.range }}</td>
      <td>{{ w.burden }}</td>
      <td>{{ w.damage }}</td>
    </tr>
{% endfor %}
  </tbody>
</table>

---

> Click any name to view full details.
