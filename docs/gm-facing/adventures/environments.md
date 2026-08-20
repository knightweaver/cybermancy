# Environments

Type to filter:
<input id="filter" data-filter-table="environments-table" placeholder="Filter by name, tier, type, difficulty" />

<table id="environments-table" class="filterable-table">
  <thead>
    <tr>
      <th>Name</th>
      <th>Tier</th>
      <th>Type</th>
      <th>Difficulty</th>
      <th>Description</th>
    </tr>
  </thead>
  <tbody>
{% for w in load_csv('../data/environments.csv') %}
    <tr>
      <td><a href="./{{ w.slug }}/">{{ w.name }}</a></td>
      <td>{{ w.tier }}</td>
      <td>{{ w.type }}</td>
      <td>{{ w.difficulty }}</td>
      <td>{{ w.description }}</td>
    </tr>
{% endfor %}
  </tbody>
</table>

---

> Click any name to view full environment details.
