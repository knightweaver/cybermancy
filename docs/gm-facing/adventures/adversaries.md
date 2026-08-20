# Adversaries

Type to filter:
<input id="filter" data-filter-table="adversaries-table" placeholder="Filter by name, tier, role, difficulty" />

<table id="adversaries-table" class="filterable-table">
  <thead>
    <tr>
      <th>Name</th>
      <th>Tier</th>
      <th>Role</th>
      <th>Difficulty</th>
      <th>Description</th>
    </tr>
  </thead>
  <tbody>
{% for w in load_csv('../data/adversaries.csv') %}
    <tr>
      <td><a href="./{{ w.slug }}/">{{ w.name }}</a></td>
      <td>{{ w.tier }}</td>
      <td>{{ w.role }}</td>
      <td>{{ w.difficulty }}</td>
      <td>{{ w.description }}</td>
    </tr>
{% endfor %}
  </tbody>
</table>

---

> Click any name to view full adversary details.
