# Cybermancy Descriptor & Foundry Import Architecture

This document preserves the principal engineering conclusions developed during the early investigation of generating and importing Cybermancy content into the Daggerheart system for Foundry VTT. These conclusions led to the **Portable Descriptor Pipeline (PDP)** and **Action/Effect Corpus Normalization (AECN)** approaches used by Cybermancy.

## 1. Why Cybermancy Uses Portable Descriptors

Several approaches to programmatically generating Foundry/Daggerheart content were investigated.

### Approaches that proved unreliable

**Direct manipulation of Foundry `.ldb` files**

Generating apparently valid JSON records directly inside the LevelDB files underlying Foundry compendia did not reliably cause those documents to appear within Foundry. The persistence layer therefore should not be treated as the Cybermancy content-authoring API.

**Foundry Export Data / Import Data**

Even exporting a working Item from Foundry and immediately importing that same JSON did not reliably preserve custom Actions and Effects. Foundry's exported representation should therefore not be assumed to be a lossless interchange format for Daggerheart documents.

**Arbitrary modification of Daggerheart schema values**

Daggerheart validates many fields against its DataModels. For example, adding an arbitrary custom value to `system.weaponFeatures` produces a `DataModelValidationError` rather than creating a new feature type. Structurally valid JSON is not necessarily valid Daggerheart data.

### Reliable approach

The Foundry document-import macros developed for Cybermancy successfully create documents through Foundry's own document APIs.

This led to the architecture:

```text
Human-editable descriptor
        ↓
Cybermancy compiler
        ↓
Known-good Daggerheart JSON structures
        ↓
Foundry document-import macro/API
        ↓
Foundry Item/Actor/etc.
```

The human-authored source therefore contains **semantic information** such as name, tier, damage, feature names, descriptions, and action references rather than attempting to reproduce the entire Foundry DataModel.

This approach became the **Portable Descriptor Pipeline (PDP)**.

---

## 2. Action/Effect Corpus Normalization (AECN)

Daggerheart itself provides a large corpus of working examples of Actions and Effects. Rather than manually reconstructing these structures, Cybermancy developed a process for extracting and normalizing them into reusable components.

This process is called **Action/Effect Corpus Normalization (AECN)**.

The basic transformation is:

```text
Daggerheart JSON corpus
        ↓
Extract system.actions and system.effects
        ↓
Discard irrelevant/empty entries
        ↓
Remove document-specific _id values
        ↓
Derive semantic identifiers from source filenames
        ↓
Replace opaque/random identifiers with semantic keys
        ↓
Categorize by source/document type
        ↓
Deduplicate equivalent structures
        ↓
Produce reusable Action/Effect catalog
```

For example, a source such as:

```text
packs/ancestries/feature_Adaptability_BNofV1UC4ZbdFTkb.json
```

with an opaque Action identifier can be normalized into a semantic catalog entry such as:

```json
{
  "features": {
    "Adaptability": {
      "actions": {
        "Adaptability": {
          "...": "known-good Daggerheart action structure"
        }
      }
    }
  }
}
```

The resulting catalog provides **canonical, experimentally validated Daggerheart JSON fragments** that PDP compilers can reference when constructing new Cybermancy documents.

This separates two concerns:

- **Descriptors specify what a Cybermancy object does.**
- **AECN catalogs specify how Daggerheart/Foundry represents that behavior.**

That distinction is central to keeping Cybermancy content portable and maintainable.

---

## 3. Features and Domain Cards Require Action-Aware Compilation

Weapons demonstrated that relatively simple descriptor fields could be compiled into complete Daggerheart Items. Class features, subclass features, and Domain Cards introduced an additional requirement: their mechanical behavior often needs to be represented by configured Foundry Actions.

The feature-authoring work therefore extended the descriptor concept to include Action semantics such as:

```text
action.name
action.kind
action.actionType
action.description
action.img
action.range
action.target.type
action.target.amount
action.cost
action.uses.*
action.damage
action.damage.type
action.damage.applyTo
action.roll.*
action.save.*
```

The compiler is responsible for translating those relatively compact fields into the much more verbose Daggerheart Action structure.

The descriptor source can consequently remain a flat table suitable for:

- CSV
- JSON
- Excel worksheets

while the compiler generates the nested Foundry JSON.

Excel support is particularly useful for bulk content authoring because individual worksheets can represent related sets of Features or Domain Cards while retaining the same underlying descriptor model.

The important architectural principle is that **Actions are generated structures, not blobs of JSON that authors should normally edit manually**.

Where possible, the compiler should either:

1. construct the Action from well-defined descriptor fields, or
2. reference a known-good Action/Effect structure from the AECN-derived catalog.

This allows the same descriptor/compiler architecture to expand beyond weapons into Features, Domain Cards, classes, subclasses, adversaries, environments, and other Daggerheart document types.

---

## 4. Foundry/Daggerheart Implementation Lessons

Several smaller technical discoveries from this investigation are worth retaining.

### Localization is separate from CSS

Adding a new Cybermancy Domain such as `netrunner` to Daggerheart's CSS can make the Domain available visually without providing its human-readable name.

A displayed string such as:

```text
DAGGERHEART.GENERAL.Domain.netrunner.label
```

indicates that Foundry/Daggerheart is attempting to resolve a localization key.

Custom Domains therefore require appropriate localization entries in addition to CSS and configuration changes.

### Daggerheart DataModels are authoritative

Foundry accepting syntactically correct JSON does not mean the Daggerheart system will accept its contents.

Fields can be:

- enumerated,
- type constrained,
- normalized,
- discarded,
- or rejected during DataModel validation.

A generated Cybermancy document should therefore be based on **known-working Daggerheart structures**, not merely inferred JSON schemas.

### Actions and Effects are especially sensitive to import behavior

Actions and Effects proved to be among the least portable parts of ordinary Foundry exports. Their persistence depends on the Daggerheart DataModel and the document-creation path.

This is the principal reason Cybermancy moved toward:

```text
Descriptor → Compiler → Known-good structure → Foundry API
```

rather than treating exported Foundry JSON as the canonical authoring format.

### Keep semantic source separate from implementation representation

The long-term source of truth should describe Cybermancy concepts in human-meaningful terms.

Foundry-specific structures are **compiled artifacts**.

This means that a field such as:

```text
actions = Legendary_Whip
```

can represent a semantic reference to a catalog entry rather than forcing the author to maintain dozens of nested Foundry properties.

That separation makes it possible to update the compiler when Daggerheart's internal schema changes without manually rewriting every Cybermancy content object.

---

## Architectural Summary

The experiments documented here ultimately established three layers:

```text
┌─────────────────────────────────────────────┐
│ AUTHORING                                   │
│ Portable descriptors                       │
│ CSV / Excel / compact JSON                  │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│ COMPILATION                                 │
│ Portable Descriptor Pipeline (PDP)          │
│                                             │
│ Uses normalized Daggerheart components from │
│ Action/Effect Corpus Normalization (AECN)   │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│ RUNTIME / DISTRIBUTION                      │
│ Full Daggerheart JSON                       │
│ → Foundry document APIs/import macros       │
│ → Cybermancy Items, Features, Actors, etc.  │
└─────────────────────────────────────────────┘
```

The central design rule is:

> **Author Cybermancy semantics; compile Foundry implementation details.**

Foundry JSON is therefore best treated as a **build artifact**, while portable descriptors and reusable canonical Daggerheart structures remain the maintainable source material.