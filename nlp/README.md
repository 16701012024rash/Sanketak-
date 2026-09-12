# Sentinel: SIF Fingerprint & Safety NLP

**Module 3 of the SIH26165 build**
**Oil India: SIF Precursor Detection**

---

## Read this if you read nothing else

1. **Never rename a taxonomy `id`.** Add new ones, deprecate old ones. A rename
   silently breaks every record already stored.
2. **Don't add taxonomy ids without telling Modules 3 and 4.** A barrier Module 4
   doesn't know about is a pattern that never groups.
3. **`null` means "not stated". It never means "applies everywhere"** —
   cross-cutting barriers use `CROSS_CUTTING`.

Everything below explains why.

---

## 1. What this module does

Safety reports are usually written as free text.

For example:

> "Technician repaired the pump without confirming isolation."

A human can immediately understand what happened. A machine cannot. The sentence needs to be converted into a structured form before the rest of the system can reliably use it.

**Module 3 takes a free-text safety report and extracts the safety information hidden inside it.**

It identifies:

* what the worker was doing
* what hazard was present
* how the worker was exposed
* which safety barrier failed
* how that barrier failed
* what could have happened
* which IOGP Life-Saving Rule applies
* the exact words in the report that support each decision

In simple terms:

> **Member 2 answers: "Is this report dangerous?"**
> **Module 3 answers: "Why is it dangerous, and what evidence in the report supports that conclusion?"**

The structured output from Module 3 is then used by the other modules for pattern detection, ranking, dashboards, and investigation.

---

## 2. The SIF Fingerprint

The main output of this module is called a **SIF Fingerprint**.

A SIF Fingerprint reduces every safety report into the same basic chain:

```text
Activity
    ↓
Hazard
    ↓
Exposure
    ↓
Barrier Failure
    ↓
Potential Consequence
    ↓
Life-Saving Rule
```

This gives different reports a common structure.

For example, these two reports may use completely different wording:

> "Worker entered the area while the equipment was still energized."

> "Technician began maintenance without verifying isolation."

A human can see that both involve an **energy isolation failure**.

A structured SIF Fingerprint allows the system to represent both reports using the same vocabulary and therefore group them together later.

---

## 3. Example

### Input report

> "Technician repaired pump without confirming isolation."

### Extracted SIF Fingerprint

```json
{
  "activity": "ACT_MECH_MAINTENANCE",
  "hazard": "HAZ_MECHANICAL",
  "exposure": "EXP_DIRECT_CONTACT",
  "barrier_failures": [
    {
      "barrier": "BAR_ISOLATION_VERIFIED",
      "failure_mode": "FM_NOT_COMPLIED",
      "primary": true,
      "evidence_span": "without confirming isolation"
    }
  ],
  "potential_consequence": "CON_CAUGHT_BETWEEN",
  "life_saving_rules": [
    "LSR_ENERGY"
  ]
}
```

The important part is that the system is **not simply guessing labels**.

It should be able to show where each extracted piece came from.

For example:

```text
Barrier failure:
BAR_ISOLATION_VERIFIED

Evidence:
"without confirming isolation"
```

This makes the result easier for a safety officer to verify.

---

## 4. Why evidence matters

This is a safety system, so a prediction without an explanation is not enough.

The system should follow one basic rule:

> **If we cannot point to the report text that supports an extracted field, we should not confidently output that field.**

For example, if the report says:

> "Technician repaired the pump without confirming isolation."

We can extract:

```text
Barrier:
BAR_ISOLATION_VERIFIED

Evidence:
"without confirming isolation"
```

But if the report never mentions a location, we should **not** guess one from other information.

Instead:

```json
{
  "location": null
}
```

This is intentional.

A missing value is safer than a fabricated value.

---

## 5. `taxonomy.yaml`

The taxonomy is the **fixed vocabulary used by the system**.

It contains the things we already know the system may need to identify:

* Life-Saving Rules
* barriers
* failure modes
* hazards
* activities
* exposures
* potential consequences
* severity bands
* context flags
* location levels

The taxonomy is a **contract between modules**.

Module 3 uses it to know what it is allowed to extract.

Module 4 uses it to group reports and detect patterns.

Module 6 uses it for dashboard filters and labels.

Because multiple modules depend on these IDs, they must remain stable.

---

### 5.1 IDs are permanent

Every taxonomy item has an ID.

For example:

```text
BAR_ISOLATION_VERIFIED
HAZ_MECHANICAL
LSR_ENERGY
FM_NOT_COMPLIED
```

Once an ID is being used by the system, **do not rename it**.

For example, changing:

```text
BAR_ISOLATION_VERIFIED
```

to:

```text
BAR_ENERGY_ISOLATION
```

may look harmless, but existing records would still contain the old ID.

The system would then treat them as different values.

#### Rule

> **Never rename an existing ID.**

If something genuinely needs to change:

* keep the existing ID
* mark it as `deprecated: true`
* introduce a new ID if necessary
* discuss the change with the relevant modules first

---

### 5.2 Labels can change

The human-readable label is different from the ID.

For example:

```yaml
id: BAR_ISOLATION_VERIFIED
label: "Isolation verified / zero-energy confirmed"
```

The label can later become:

```yaml
label: "Verification of energy isolation"
```

without breaking existing records.

So:

```text
ID    = permanent system identity
Label = human-readable description
```

---

### 5.3 Do not change IDs independently

The taxonomy is shared infrastructure.

If Module 3 adds a new barrier without informing Module 4, Module 4 may not know how to group or analyse reports containing that barrier.

Therefore:

> **Any new taxonomy ID should be discussed with the modules that depend on it before being added.**

This keeps all modules working from the same vocabulary.

---

## 6. `locations.yaml`

Locations are different from everything else in the taxonomy.

Barriers, hazards, failure modes, activities, and LSRs are **closed vocabularies**.

We can define them in advance.

Locations are an **open vocabulary**.

OIL can:

* drill new wells
* commission new installations
* create new areas
* rename or reorganise locations

Therefore, locations should not be stored as a permanent list inside `taxonomy.yaml`.

Instead, we separate the two:

```text
taxonomy.yaml
    ↓
defines the allowed LOCATION LEVELS

locations.yaml
    ↓
contains the current LOCATION VALUES
```

For example:

```text
taxonomy.yaml

region
field
installation
area
```

while:

```text
locations.yaml

Baghewala
Dandewala
Oil Collecting Station
Tank farm
```

This means adding a new well does **not** require a taxonomy version change.

The location registry can eventually be replaced with OIL's official site master.

---

## 7. Location hierarchy

For the current version, we use a normalised four-level structure:

```text
Region
   ↓
Field
   ↓
Installation
   ↓
Area
```

These levels are a structure chosen for our system.

They are **not a claim that this is OIL's official organisational hierarchy**.

The actual OIL site master should eventually become the source of truth.

The levels are also optional.

If a report only says:

> "Incident occurred at Baghewala."

we should store what we know and leave the remaining levels empty.

We should **never invent a more specific location**.

For example:

```text
Field: Baghewala
Installation: null
Area: null
```

is correct if that is all the report tells us.

---

## 8. Location verification

Every current location entry contains:

```yaml
verified: false
```

This is intentional.

Our initial location registry is based on publicly available information and our normalised structure.

It has not yet been validated against OIL's official site master.

Once OIL provides the actual site master and the entries are confirmed, they can be changed to:

```yaml
verified: true
```

This makes the uncertainty machine-readable instead of hiding it in documentation.

---

## 9. Location aliases

People may refer to the same location in different ways.

For example:

```text
OCS
collecting station
Oil Collecting Station
```

These may refer to the same entity.

Therefore, location entries support aliases.

Example:

```yaml
label: "Oil Collecting Station"

aliases: ["OCS", "collecting station"]
```

This allows the location resolver to recognise different ways of referring to the same place.

Without aliases, the system could incorrectly treat them as three separate locations.

---

## 10. `location_raw`

The original location wording from the report is **always preserved**.

For example, if the report says:

> "Incident occurred near the old pump."

we keep:

```json
{
  "location_raw": "near the old pump"
}
```

even if the system successfully resolves it.

If resolution fails:

```json
{
  "location_raw": "near the old pump",
  "location": null
}
```

The original text is still available for a human reviewer to resolve later.

This follows one of the main principles of the module:

> **Never lose information that we can point back to in the original report.**

---

## 11. Location resolution is different from classification

Most of the module deals with **classification and extraction**.

For example:

```text
"no gas test was performed"

        ↓

Barrier:
BAR_GAS_TEST

Failure mode:
FM_ABSENT
```

Location resolution is different.

It is an **entity resolution problem**.

For example:

```text
"OCS"

        ↓

Which known location does this refer to?
```

Aliases can solve simple cases.

However, real reports may contain phrases such as:

```text
"near the old pump"
"beside Well #42"
"behind the workshop"
```

These may not match any known location or alias.

Therefore, we should expect location resolution to have lower accuracy than core safety extraction.

When the system is uncertain, it should preserve:

```text
location_raw
```

and allow human correction.

We should agree with Module 4 on how accurate location resolution needs to be before it is used heavily for site ranking.

---

## 12. Barrier and failure mode are separate

A barrier and the failure of that barrier are not the same thing.

For example:

```text
Barrier:
BAR_GAS_TEST
```

can fail in different ways.

### Example 1: Barrier absent

> "No gas testing procedure was available."

```text
BAR_GAS_TEST
FM_ABSENT
```

### Example 2: Barrier existed but was not followed

> "Gas testing was required, but the worker skipped it."

```text
BAR_GAS_TEST
FM_NOT_COMPLIED
```

These are different problems.

If a required barrier does not exist, the organisation may need to create or strengthen the control.

If the barrier exists but people are not following it, the intervention may instead involve supervision, training, procedure compliance, or enforcement.

Therefore, the system keeps them as two separate fields:

```text
barrier
+
failure_mode
```

This also helps Module 4 identify different systemic patterns.

---

## 13. Multiple barrier failures

A single report can contain more than one barrier failure.

For example:

> "The worker entered the area without a permit and no gas test was performed."

There are at least two failures:

```text
1. Permit barrier
2. Gas testing barrier
```

The output therefore allows:

```json
{
  "barrier_failures": [
    {
      "barrier": "BAR_PERMIT_VALID",
      "failure_mode": "FM_NOT_COMPLIED",
      "primary": true
    },
    {
      "barrier": "BAR_GAS_TEST",
      "failure_mode": "FM_ABSENT",
      "primary": false
    }
  ]
}
```

There should be **one primary failure** when possible.

The primary failure represents the main issue driving the incident.

The other failures are still preserved because they may be important for later pattern analysis.

---

## 14. Cross-cutting barriers

Not every barrier belongs to one specific Life-Saving Rule.

Some controls are broader organisational or operational controls.

These are represented using:

```text
CROSS_CUTTING
```

rather than using `null`.

This distinction matters.

### `null`

Means:

> The information was not stated or is unknown.

### `CROSS_CUTTING`

Means:

> The barrier is known, but it does not belong to one specific LSR.

These two meanings should never be mixed.

---

## 15. Design principles

The module follows a few rules that should not be quietly changed during implementation.

### 1. Never invent information

If the report does not provide a value, return:

```text
null
```

Do not infer it simply because it seems likely.

---

### 2. Preserve the original evidence

Keep the original words that support the extraction.

This includes:

```text
evidence_span
location_raw
```

The goal is that a safety officer can trace an AI output back to the report.

---

### 3. Use controlled vocabularies

Extracted values should map to known taxonomy IDs whenever possible.

For example:

```text
"stored pressure"
"pressurised equipment"
"pressure inside the line"
```

should not automatically become three unrelated hazard categories if they represent the same underlying hazard.

A controlled vocabulary makes reports comparable.

---

### 4. Separate the barrier from how it failed

Do not create values such as:

```text
"isolation not verified"
```

as a single combined category.

Instead:

```text
Barrier:
BAR_ISOLATION_VERIFIED

Failure mode:
FM_NOT_COMPLIED
```

This allows the system to analyse the barrier and the failure independently.

---

### 5. Null means "not stated"

`null` should mean:

> The report did not provide this information.

It should not mean:

> This applies everywhere.

For cross-cutting barriers, use:

```text
CROSS_CUTTING
```

---

### 6. Evaluate every field

The system should not be considered successful because a few examples "look right."

We need a labelled **gold dataset** and measurable performance for each important field.

For example:

```text
Activity accuracy
Hazard accuracy
Exposure accuracy
Barrier accuracy
Failure-mode accuracy
LSR accuracy
Evidence-span accuracy
Location resolution accuracy
```

This lets us identify exactly where the model is strong and where it needs improvement.

---

## 16. Project structure

```text
sih_proj/
│
├── taxonomy/
│   ├── taxonomy.yaml
│   └── locations.yaml
│
├── src/
│
├── data/
│   └── raw/              # gitignored
│
├── tests/
│
└── README.md
```

### What each part does

**`taxonomy/`**

Contains the controlled vocabularies and location registry.

**`src/`**

Implementation code. Subpackages are added as each component is built:

```text
loader/       loads and validates the taxonomy before anything else uses it
tagger/       identifies the relevant Life-Saving Rule
extractor/    extracts the SIF Fingerprint fields from the report
explainer/    connects extracted fields back to evidence in the original report
```

**`data/`**

Datasets used for development and evaluation.

Raw and generated data is gitignored. Generation *scripts* are committed; their
output is not.

**`tests/`**

Taxonomy validation and model evaluation.

---

## 17. Current status

| Component              | Status      |
| ---------------------- | ----------- |
| Taxonomy v0.1          | Done        |
| Location registry v0.1 | Provisional |
| Location levels        | Defined     |
| Loader + validation    | Next        |
| LSR tagger             | Not started |
| Fingerprint extractor  | Not started |
| Evidence spans         | Not started |
| Multilingual NLP       | Not started |

### Location registry status

The location registry is intentionally provisional.

It will eventually be aligned with or replaced by OIL's official site master.

Until then:

```text
verified = false
```

is the expected state.

---

## 18. Next step: Loader + validation

The next implementation task is the **taxonomy loader and validator**.

Its job is simple:

```text
taxonomy.yaml
      ↓
   load file
      ↓
   validate structure
      ↓
   validate IDs
      ↓
   validate references
      ↓
   reject invalid taxonomy
      ↓
   make valid taxonomy available to the application
```

For example, the validator should catch things like:

* duplicate IDs
* missing required fields
* invalid LSR references
* invalid barrier references
* invalid failure-mode references
* missing `applies_to`
* unexpected vocabulary values
* malformed YAML

The goal is to make the taxonomy a reliable contract before the NLP components are built on top of it.

---

## 19. Open questions for the team

### 1. Can the SPOC obtain sample UA/UC report formats from OIL?

Even blank templates would help us understand:

* how reports are actually written
* which fields are usually available
* how locations are described
* what terminology workers use
* which information is commonly missing

Real report formats would allow us to design and evaluate the extractor against realistic input rather than assumptions.

### 2. How much location accuracy does Module 4 actually need?

Location resolution will probably be weaker than core safety extraction.

Real reports may contain phrases such as:

```text
"near the old pump"
"at Well #42"
"behind the workshop"
```

These cannot always be resolved from aliases alone.

Before Module 4 builds site-ranking logic around locations, we should agree on:

* what level of location accuracy is required
* when an unresolved location is acceptable
* whether human correction will be part of the workflow

This prevents Module 3 from being held to an unrealistic standard and prevents Module 4 from assuming location data is more precise than it actually is.

---

## 20. The goal

The end result is not just a classifier.

The goal is a **traceable safety intelligence layer**.

```text
Free-text report
       ↓
SIF Fingerprint
       ↓
Structured safety information
       ↓
Evidence from original report
       ↓
Pattern detection
       ↓
Risk intelligence
       ↓
Actionable HSE insight
```

Module 3 is the layer that converts messy human-written reports into structured, explainable safety information that the rest of the system can trust.
