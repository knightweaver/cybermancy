# Weapons

Type to filter:
<input id="filter" placeholder="Filter by name, category, domain, rarity" />

<table id="weapons-table">
  <thead>
    <tr>
      <th>Name</th>
      <th>Description</th>
      <th>Tier</th>
      <th>attack</th>
      <th>Hands</th>
      <th>Actions</th>
    </tr>
  </thead>
  <tbody>
{% for w in load_csv('data/weapons.csv') %}
    <tr>
      <td><a href="./{{ w.slug }}/">{{ w.name }}</a></td>
      <td>{{ w.description }}</td>
      <td>{{ w.tier }}</td>
      <td>{{ w.attack }}</td>
      <td>{{ w.hands }}</td>
      <td>{{ w.actions }}</td>
    </tr>
{% endfor %}
  </tbody>
</table>

---

> Click any name to view full details.
