# Domain Cards

Type to filter:
<input id="filter" placeholder="Filter by name, category, domain, rarity" />

<table id="weapons-table">
  <thead>
    <tr>
      <th>Name</th>
      <th>Description</th>
      <th>Domain</th>
      <th>Level</th>
      <th>Recall Cost</th>
    </tr>
  </thead>
  <tbody>
{% for w in load_csv('../data/domains.csv') %}
    <tr>
      <td><a href="./{{ w.slug }}/">{{ w.name }}</a></td>
      <td>{{ w.description }}</td>
      <td>{{ w.domain }}</td>
      <td>{{ w.level }}</td>
      <td>{{ w.recallCost }}</td>
    </tr>
{% endfor %}
  </tbody>
</table>

---

> Click any name to view full details.
