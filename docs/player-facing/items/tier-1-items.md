# All Tier 1 Cybermancy Items

### Weapons

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
{% for w in load_csv('../data/weapons.csv') if w.tier == '1' or w.tier == 'Tier 1'%}
    <tr>
      <td><a href="../weapons/{{ w.slug }}/">{{ w.name }}</a></td>
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

### Weapon Mods

<table id="weapon-mods-table">
  <thead>
    <tr>
      <th>Name</th>
      <th>Description</th>
      <th>Tier</th>
    </tr>
  </thead>
  <tbody>
{% for w in load_csv('../data/mods.csv') if w.tier == '1' or w.tier == 'Tier 1'%}
    <tr>
      <td><a href="../mods/{{ w.slug }}/">{{ w.name }}</a></td>
      <td>{{ w.description }}</td>
      <td>{{ w.tier }}</td>
    </tr>
{% endfor %}
  </tbody>
</table>

---

### Ammo

<table id="ammo-table">
  <thead>
    <tr>
      <th>Name</th>
      <th>Description</th>
      <th>Tier</th>
    </tr>
  </thead>
  <tbody>
{% for w in load_csv('../data/ammo.csv') if w.tier == '1' or w.tier == 'Tier 1'%}
    <tr>
      <td><a href="../ammo/{{ w.slug }}/">{{ w.name }}</a></td>
      <td>{{ w.description }}</td>
      <td>{{ w.tier }}</td>
    </tr>
{% endfor %}
  </tbody>
</table>

---

### Armor

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
{% for w in load_csv('../data/armors.csv')  if w.tier == '1' or w.tier == 'Tier 1'%}
    <tr>
      <td><a href="../armors/{{ w.slug }}/">{{ w.name }}</a></td>
      <td>{{ w.description }}</td>
      <td>{{ w.tier }}</td>
      <td>{{ w.baseScore }}</td>
      <td>{{ w.majorThreshold }} / {{ w.severeThreshold }}</td>
    </tr>
{% endfor %}
  </tbody>
</table>

---

### Consumables

<table id="consumables-table">
  <thead>
    <tr>
      <th>Name</th>
      <th>Description</th>
      <th>Tier</th>
    </tr>
  </thead>
  <tbody>
{% for w in load_csv('../data/consumables.csv')  if w.tier == '1' or w.tier == 'Tier 1'%}
    <tr>
      <td><a href="../consumables/{{ w.slug }}/">{{ w.name }}</a></td>
      <td>{{ w.description }}</td>
      <td>{{ w.tier }}</td>
    </tr>
{% endfor %}
  </tbody>
</table>

---

### Cybernetics

<table id="cybernetics-table">
  <thead>
    <tr>
      <th>Name</th>
      <th>Description</th>
      <th>Tier</th>
    </tr>
  </thead>
  <tbody>
{% for w in load_csv('../data/cybernetics.csv') if w.tier == '1' or w.tier == 'Tier 1'%}
    <tr>
      <td><a href="../cybernetics/{{ w.slug }}/">{{ w.name }}</a></td>
      <td>{{ w.description }}</td>
      <td>{{ w.tier }}</td>
    </tr>
{% endfor %}
  </tbody>
</table>

---

### Drone Mods

<table id="drone-mods-table">
  <thead>
    <tr>
      <th>Name</th>
      <th>Description</th>
      <th>Tier</th>
    </tr>
  </thead>
  <tbody>
{% for w in load_csv('../data/drone-mods.csv') if w.tier == '1' or w.tier == 'Tier 1' %}
    <tr>
      <td><a href="../drone-mods/{{ w.slug }}/">{{ w.slug }}</a></td>
      <td>{{ w.description }}</td>
      <td>{{ w.tier }}</td>
    </tr>
{% endfor %}
  </tbody>
</table>

---

### Loot

<table id="loot-table">
  <thead>
    <tr>
      <th>Name</th>
      <th>Description</th>
      <th>Tier</th>
    </tr>
  </thead>
  <tbody>
{% for w in load_csv('../data/loot.csv') if w.tier == '1' or w.tier == 'Tier 1'%}
    <tr>
      <td><a href="../loot/{{ w.slug }}/">{{ w.name }}</a></td>
      <td>{{ w.description }}</td>
      <td>{{ w.tier }}</td>
    </tr>
{% endfor %}
  </tbody>
</table>

---

> Click any name to view full details.
