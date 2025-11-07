# Armors

Type to filter:
<input id="filter" placeholder="Filter by name, category, domain, rarity" />

<table id="armors-table">
  <thead>
    <tr>
      <th>Name</th>
      <th>Description</th>
      <th>Tier</th>
      <th>Base Score</th>
      <th>Base Thresholds</th>
    </tr>
  </thead>
  <tbody>
{% for w in load_csv('../data/armors.csv') %}
    <tr>
      <td><a href="./{{ w.slug }}/">{{ w.name }}</a></td>
      <td>{{ w.description }}</td>
      <td>{{ w.tier }}</td>
      <td>{{ w.baseScore }}</td>
      <td>{{ w.majorThreshold }} / {{ w.severeThreshold }}</td>
    </tr>
{% endfor %}
  </tbody>
</table>

---

> Click any name to view full details.
