# drones-devices

Type to filter:
<input id="filter" placeholder="Filter by name, category, domain, rarity" />

<table id="weapons-table">
  <thead>
    <tr>
      <th>Name</th>
      <th>Description</th>
      <th>Tier</th>
    </tr>
  </thead>
  <tbody>
{% for w in load_csv('../data/drones-devices.csv') %}
    <tr>
      <td><a href="./{{ w.slug }}/">{{ w.name }}</a></td>
      <td>{{ w.description }}</td>
      <td>{{ w.tier }}</td>
    </tr>
{% endfor %}
  </tbody>
</table>

---

> Click any name to view full details.