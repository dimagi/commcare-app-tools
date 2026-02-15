---
name: commcare-test-builder
description: Generate CommCare test YAML fixtures for the cc test run command. Use when the user wants to create a new test, write a test fixture, build a test from a bug report or acceptance criteria, or asks about the test YAML format.
---

# CommCare Test Builder

Build test YAML fixtures that run end-to-end CommCare form tests via `cc test run`.

## Inputs You May Receive

1. **CCZ file path** -- a `.ccz` file (ZIP archive) containing the app's XForm XML
2. **Bug report or acceptance criteria** -- text describing what to test
3. **Existing test YAML files** -- other tests for the same app to use as reference

## Step 1: Gather Context

### From a CCZ file

A CCZ is a ZIP. Extract form structure to find question XPaths:

```python
import zipfile, os
with zipfile.ZipFile("app.ccz") as z:
    # XForm XMLs are in modules_*/forms_*/form.xml
    for name in z.namelist():
        if name.endswith("form.xml"):
            print(name)
            print(z.read(name).decode("utf-8")[:2000])
```

Inside each `form.xml`, look for:
- `<bind nodeset="/data/question_name" type="xsd:string" .../>` -- defines question XPaths and types
- `<select1 ref="/data/choice_q">` with `<item><value>1</value></item>` -- select options
- `<group ref="/data/group_name"><repeat ...>` -- repeat groups
- `<setvalue ref="/data/hidden" .../>` -- hidden/calculated values (do NOT include in answers)

### From existing test YAMLs

Read them to extract:
- `domain`, `app_id`, `username` -- reuse these for new tests against the same app
- `navigation` patterns -- same app menus apply to sibling forms
- Naming conventions -- follow the same style

### From a bug report or acceptance criteria

Map user actions to test steps:
- "Open the registration form" --> navigation steps (menu selections)
- "Enter name as John" --> answer: `/data/name: "John"`
- "Select female for gender" --> answer: `/data/gender: "2"` (select index)
- "Add a second household member" --> answer: `/data/members: NEW_REPEAT`
- "Skip the optional notes field" --> answer: `/data/notes: SKIP`

## Step 2: Build the Test YAML

### Required Fields

```yaml
name: "Descriptive test name"
domain: the-project-domain
app_id: hex-app-id-string
username: mobile-worker-name
```

### Optional Fields

```yaml
timeout: 120  # seconds, default 120
```

### Navigation

Ordered list of menu/entity selections to reach the target form. These are 1-indexed numbers matching the CLI menu display:

```yaml
navigation:
  - "1"    # First menu module
  - "3"    # Third form in that module
```

For entity selection (case list), use the row number. If the form does not require case selection, only menu items are needed.

### Answers

Dict mapping question XPath to value. Keys MUST match `<bind nodeset="...">` paths from the XForm XML.

```yaml
answers:
  /data/name: "Jane Doe"
  /data/age: "32"
  /data/gender: "1"           # select1 option index (1-indexed)
  /data/multi_select: "1 3"   # space-separated indices for multi-select
  /data/date_field: "2025-06-15"
  /data/repeat_group: NEW_REPEAT
  /data/repeat_group/child_name: "Alice"
  /data/optional_notes: SKIP
```

**Answer value rules:**
- Text/number/date: provide the literal value as a string
- `select1`: provide the 1-indexed option number as a string
- Multi-select: space-separated option indices
- `SKIP`: explicitly skip a non-required question
- `NEW_REPEAT`: add a new repeat group instance
- Do NOT include hidden/calculated fields -- they are filled automatically

**XPath rules:**
- Always start with `/data/`
- Match the `nodeset` attribute from `<bind>` elements exactly
- For questions inside groups: `/data/group_name/question_name`
- For questions inside repeats: `/data/repeat_name/question_name`

## Step 3: Validate

Before presenting the YAML to the user, check:

- [ ] All four required fields are present (`name`, `domain`, `app_id`, `username`)
- [ ] Navigation steps are strings (quoted numbers)
- [ ] Every answer XPath starts with `/data/`
- [ ] Answer XPaths match actual `<bind nodeset>` values from the form XML (if CCZ was provided)
- [ ] Select answers use valid option indices (not labels)
- [ ] Hidden/calculated fields are excluded from answers
- [ ] `SKIP` and `NEW_REPEAT` are uppercase with no quotes around the keyword
- [ ] Test name is descriptive (not generic like "My Test")

## Complete Example

```yaml
name: "Register new patient - basic info"
domain: my-health-project
app_id: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4
username: nurse1

timeout: 120

navigation:
  - "1"    # Registration module
  - "1"    # New Patient form

answers:
  /data/patient_name: "Jane Doe"
  /data/age: "32"
  /data/gender: "2"
  /data/village: "Kigali"
  /data/phone: "+250781234567"
  /data/consent: "1"
  /data/household_members: NEW_REPEAT
  /data/household_members/member_name: "John Doe"
  /data/household_members/member_age: "35"
  /data/notes: SKIP
```

## Running the Test

```
cc test run path/to/test.yaml
cc test run path/to/test.yaml --output-xml result.xml
cc test run path/to/test.yaml --show-output
```

## Reference Files

For implementation details on the test format and execution:
- [src/commcare_app_tools/test/definition.py](src/commcare_app_tools/test/definition.py) -- `TestDefinition` dataclass, YAML parsing, replay string builder
- [src/commcare_app_tools/test/runner.py](src/commcare_app_tools/test/runner.py) -- `TestRunner` (setup, execution, result parsing) and `TestResult`
