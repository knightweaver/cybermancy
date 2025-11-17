# Features

Type to filter:
<input id="filter" placeholder="Filter by name, category, domain, rarity" />

<table id="adversaries-features-table">
  <thead>
    <tr>
      <th>Name</th>
      <th>Type</th>
      <th>Description</th>
    </tr>
  </thead>
  <tbody>
{% for w in load_csv('../data/adversaries-features.csv') %}
    <tr>
      <td><a href="./{{ w.slug }}/">{{ w.name }}</a></td>
      <td>{{ w.tier }}</td>
      <td>{{ w.description }}</td>
    </tr>
{% endfor %}
  </tbody>
</table>

---

> Click any name to view full details.
