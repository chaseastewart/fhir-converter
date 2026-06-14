# HL7v2 to FHIR Conversion - Technical Guide

## Table of Contents

1. [Quick Start](#quick-start)
2. [Data Extraction from HL7v2](#data-extraction-from-hl7v2)
3. [Liquid Template Deep Dive](#liquid-template-deep-dive)
4. [JSON5 Processing](#json5-processing)
5. [Advanced Topics](#advanced-topics)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Basic Usage

```python
from fhir_converter.renderers import Hl7v2Renderer

# Create renderer instance
renderer = Hl7v2Renderer()

# Convert HL7v2 message to FHIR
with open("message.hl7", "r", encoding="utf-8") as hl7v2_file:
    fhir_bundle = renderer.render_fhir_string("ORU_R01", hl7v2_file)
    print(fhir_bundle)
```

### Available Message Types

The library includes templates for these HL7v2 message types:
- **ADT**: A01-A60 (Admit, Discharge, Transfer events)
- **ORU**: R01 (Observation results)
- **ORM**: O01 (Orders)
- **RDE**: O11, O25 (Pharmacy orders)
- **VXU**: V04 (Vaccination updates)
- **MDM**: T01-T10 (Medical documents)
- **SIU**: S12-S26 (Scheduling)
- And many more...

### Custom Template Usage

```python
from liquid import FileSystemLoader
from fhir_converter.renderers import Hl7v2Renderer, make_environment

# Use custom templates
loader = FileSystemLoader("./my-templates")
env = make_environment(loader)
renderer = Hl7v2Renderer(env=env)

with open("message.hl7", "r") as hl7v2_file:
    result = renderer.render_fhir_string("Custom_Template", hl7v2_file)
```

---

## Data Extraction from HL7v2

### Understanding HL7v2 Structure

HL7v2 messages have a hierarchical structure:

```
MESSAGE
├── Segment (e.g., MSH, PID, OBR)
│   ├── Field 1 (separated by |)
│   │   ├── Repeat 1 (separated by ~)
│   │   │   ├── Component 1 (separated by ^)
│   │   │   │   ├── Subcomponent 1 (separated by &)
│   │   │   │   └── Subcomponent 2
│   │   │   └── Component 2
│   │   └── Repeat 2
│   ├── Field 2
│   └── Field 3
└── Segment
```

### Parsing Process

#### Step 1: Extract Encoding Characters

```python
# From MSH segment: MSH|^~\&|...
# Position 3: |  (field separator)
# Position 4: ^  (component separator)
# Position 5: ~  (repetition separator)
# Position 6: \  (escape character)
# Position 7: &  (subcomponent separator)

encoding_characters = Hl7v2EncodingCharacters(
    field_separator="|",
    component_separator="^",
    repetition_separator="~",
    escape_character="\\",
    subcomponent_separator="&"
)
```

#### Step 2: Split Message into Segments

```python
segments = message.replace("\r\n", "\n").replace("\r", "\n").split("\n")
# Result: ["MSH|^~\\&|...", "PID|1||...", "OBR|1|...", ...]
```

#### Step 3: Parse Each Segment

**Example: PID Segment**
```hl7
PID|1||123456789^^^Hospital^MR||Johnson^Sarah^Marie^^Jr^Ph.D||19850312|F
```

**Parsed Structure:**
```python
Hl7v2Segment(
    normalized_text="PID|1||123456789^^^Hospital^MR||Johnson^Sarah^Marie^^Jr^Ph.D||19850312|F",
    fields=[
        Hl7v2Field(value="PID", ...),               # Field 0
        Hl7v2Field(value="1", ...),                 # Field 1: Set ID
        Hl7v2Field(value="", ...),                  # Field 2: (empty)
        Hl7v2Field(                                 # Field 3: Patient ID
            value="123456789^^^Hospital^MR",
            components=[
                None,  # Index 0 (reserved)
                Hl7v2Component(value="123456789", subcomponents=[None, "123456789"]),
                Hl7v2Component(value="", ...),
                Hl7v2Component(value="", ...),
                Hl7v2Component(value="Hospital", subcomponents=[None, "Hospital"]),
                Hl7v2Component(value="MR", subcomponents=[None, "MR"])
            ]
        ),
        None,  # Field 4: Alternate Patient ID (empty)
        Hl7v2Field(                                 # Field 5: Patient Name
            value="Johnson^Sarah^Marie^^Jr^Ph.D",
            components=[
                None,  # Index 0 (reserved)
                Hl7v2Component(value="Johnson", ...),    # Family name
                Hl7v2Component(value="Sarah", ...),      # Given name
                Hl7v2Component(value="Marie", ...),      # Middle name
                Hl7v2Component(value="", ...),           # Suffix (empty)
                Hl7v2Component(value="Jr", ...),         # Prefix
                Hl7v2Component(value="Ph.D", ...)        # Degree
            ]
        ),
        ...
    ]
)
```

#### Step 4: Convert to Dictionary for Templates

```python
segment_dict = {
    'Value': 'PID|1||123456789^^^Hospital^MR||Johnson^Sarah^Marie^^Jr^Ph.D||19850312|F',
    '0': {'Value': 'PID'},
    '1': {'Value': '1'},
    '2': None,  # Empty field
    '3': {
        'Value': '123456789^^^Hospital^MR',
        '1': {'Value': '123456789'},
        '2': None,
        '3': None,
        '4': {'Value': 'Hospital'},
        '5': {'Value': 'MR'}
    },
    '4': None,
    '5': {
        'Value': 'Johnson^Sarah^Marie^^Jr^Ph.D',
        '1': {'Value': 'Johnson'},
        '2': {'Value': 'Sarah'},
        '3': {'Value': 'Marie'},
        '4': None,
        '5': {'Value': 'Jr'},
        '6': {'Value': 'Ph.D'}
    },
    '7': {'Value': '19850312'},
    '8': {'Value': 'F'}
}
```

### Accessing Data in Templates

#### Basic Field Access

```liquid
{%- comment -%}
PID|1||123456789^^^Hospital^MR||Johnson^Sarah^Marie^^Jr^Ph.D||19850312|F
{%- endcomment -%}

{% assign pid = firstSegments.PID -%}

{%- comment -%} Get set ID (field 1) {%- endcomment -%}
{{ pid."1".Value }}  → "1"

{%- comment -%} Get patient ID (field 3, component 1) {%- endcomment -%}
{{ pid."3"."1".Value }}  → "123456789"

{%- comment -%} Get assigning authority (field 3, component 4) {%- endcomment -%}
{{ pid."3"."4".Value }}  → "Hospital"

{%- comment -%} Get family name (field 5, component 1) {%- endcomment -%}
{{ pid."5"."1".Value }}  → "Johnson"

{%- comment -%} Get given name (field 5, component 2) {%- endcomment -%}
{{ pid."5"."2".Value }}  → "Sarah"

{%- comment -%} Get birth date (field 7) {%- endcomment -%}
{{ pid."7".Value }}  → "19850312"

{%- comment -%} Get gender (field 8) {%- endcomment -%}
{{ pid."8".Value }}  → "F"
```

#### Handling Repeating Fields

```liquid
{%- comment -%}
OBX segment with repeating results:
OBX|1|NM|8480-6^Systolic BP^LN~8462-4^Diastolic BP^LN|1|135~85|mm[Hg]|...
{%- endcomment -%}

{% assign obx = obxSegment -%}

{%- comment -%} Access first repeat {%- endcomment -%}
{{ obx."3".Repeats[0]."1".Value }}  → "8480-6"

{%- comment -%} Access second repeat {%- endcomment -%}
{{ obx."3".Repeats[1]."1".Value }}  → "8462-4"

{%- comment -%} Loop through all repeats {%- endcomment -%}
{% for repeat in obx."3".Repeats -%}
    Code: {{ repeat."1".Value }}
    Display: {{ repeat."2".Value }}
{% endfor -%}
```

#### Checking for Empty Values

```liquid
{%- comment -%} Method 1: Check if field exists and is not empty {%- endcomment -%}
{% if pid."5" and pid."5"."1".Value != "" -%}
    "family": "{{ pid."5"."1".Value }}",
{% endif -%}

{%- comment -%} Method 2: Multiple conditions {%- endcomment -%}
{% if pid."5"."1" != "" and pid."5"."1" != null -%}
    "family": "{{ pid."5"."1".Value }}",
{% endif -%}

{%- comment -%} Method 3: Check entire field {%- endcomment -%}
{% if pid."7" -%}
    "birthDate": "{{ pid."7".Value | add_hyphens_date }}",
{% endif -%}
```

---

## Liquid Template Deep Dive

### Template Structure

A typical message template has this structure:

```liquid
{%- comment -%}
1. Extract segments using filters
{%- endcomment -%}
{% assign firstSegments = hl7v2Data | get_first_segments: 'MSH|PID|PV1' -%}
{% assign obrSegmentLists = hl7v2Data | get_segment_lists: 'OBR' -%}
{% assign obxSegmentLists = hl7v2Data | get_segment_lists: 'OBX' -%}

{%- comment -%}
2. Generate unique IDs for resources
{%- endcomment -%}
{% evaluate bundleID using 'ID/Bundle' Data: firstSegments.MSH."10" -%}
{% evaluate patientId using 'ID/Patient' PID: firstSegments.PID -%}

{%- comment -%}
3. Create FHIR Bundle structure
{%- endcomment -%}
{
    "resourceType": "Bundle",
    "type": "batch",
    "id": "{{ bundleID }}",
    {% if firstSegments.MSH."7" -%}
        "timestamp": "{{ firstSegments.MSH."7".Value | format_as_date_time }}",
    {% endif -%}
    "entry": [
        {%- comment -%}
        4. Include resources using sub-templates
        {%- endcomment -%}
        {% include 'Resource/Patient' PID: firstSegments.PID, ID: patientId -%}
        
        {%- comment -%}
        5. Loop through repeating segments
        {%- endcomment -%}
        {% for obrSegment in obrSegmentLists.OBR -%}
            {% evaluate observationId using 'ID/Observation' OBR: obrSegment -%}
            {% include 'Resource/Observation' OBR: obrSegment, ID: observationId -%}
        {% endfor -%}
    ]
}
```

### Custom Filters Reference

#### Segment Extraction Filters

**`get_first_segments`**
```liquid
{%- comment -%}
Get the FIRST occurrence of multiple segment types
Returns: Dictionary with segment names as keys
{%- endcomment -%}
{% assign firstSegments = hl7v2Data | get_first_segments: 'MSH|UAC|EVN|PID|PD1|PV1|PV2' -%}

{%- comment -%} Access specific segments {%- endcomment -%}
{{ firstSegments.MSH."3".Value }}  → Sending Application
{{ firstSegments.PID."5"."1".Value }}  → Patient Family Name
{{ firstSegments.PV1."19".Value }}  → Visit Number
```

**`get_segment_lists`**
```liquid
{%- comment -%}
Get ALL occurrences of multiple segment types
Returns: Dictionary with segment names as keys, arrays as values
{%- endcomment -%}
{% assign segmentLists = hl7v2Data | get_segment_lists: 'OBR|OBX|NTE' -%}

{%- comment -%} Loop through segments {%- endcomment -%}
{% for obrSegment in segmentLists.OBR -%}
    Order: {{ obrSegment."2".Value }}
{% endfor -%}

{% for obxSegment in segmentLists.OBX -%}
    Result: {{ obxSegment."5".Value }}
{% endfor -%}
```

**`get_related_segment_list`**
```liquid
{%- comment -%}
Get child segments that follow a specific parent segment
Useful for hierarchical HL7v2 structures (e.g., OBX under OBR)
{%- endcomment -%}
{% for obrSegment in obrSegmentLists.OBR -%}
    {% assign relatedObxList = hl7v2Data | get_related_segment_list: obrSegment, 'OBX' -%}
    
    Order: {{ obrSegment."2".Value }}
    
    {% for obxSegment in relatedObxList.OBX -%}
        Result: {{ obxSegment."5".Value }}
    {% endfor -%}
{% endfor -%}
```

**`get_parent_segment`**
```liquid
{%- comment -%}
Find parent segment for a given child segment
Useful when iterating through all segments and need context
{%- endcomment -%}
{% assign prtSegmentPositionIndex = 0 -%}
{% for prtSegment in prtSegmentLists.PRT -%}
    {%- comment -%} Find which segment this PRT belongs to {%- endcomment -%}
    {% assign parentOBX = hl7v2Data | get_parent_segment: 'PRT', prtSegmentPositionIndex, 'OBX' -%}
    {% assign parentOBR = hl7v2Data | get_parent_segment: 'PRT', prtSegmentPositionIndex, 'OBR' -%}
    
    {% if parentOBX.OBX.Value != null -%}
        {%- comment -%} PRT is related to an OBX {%- endcomment -%}
    {% elsif parentOBR.OBR.Value != null -%}
        {%- comment -%} PRT is related to an OBR {%- endcomment -%}
    {% endif -%}
    
    {% assign prtSegmentPositionIndex = prtSegmentPositionIndex | plus: 1 -%}
{% endfor -%}
```

#### Date/Time Filters

**`format_as_date_time`**
```liquid
{%- comment -%}
Convert HL7v2 timestamp to FHIR dateTime format
Input: 20241007143000-0500
Output: 2024-10-07T14:30:00-05:00
{%- endcomment -%}
"timestamp": "{{ MSH."7".Value | format_as_date_time }}"
```

**`add_hyphens_date`**
```liquid
{%- comment -%}
Convert HL7v2 date to FHIR date format (day precision)
Input: 19850312
Output: 1985-03-12
{%- endcomment -%}
"birthDate": "{{ PID."7".Value | add_hyphens_date }}"
```

**`date`**
```liquid
{%- comment -%}
Format date with custom format string (supports C# format codes)
{%- endcomment -%}
"formattedDate": "{{ PID."7".Value | date: 'yyyy-MM-dd' }}"
```

**`now`**
```liquid
{%- comment -%}
Get current timestamp in FHIR format
{%- endcomment -%}
"lastUpdated": "{{ '' | now }}"
```

#### ID Generation Filters

**`generate_uuid`**
```liquid
{%- comment -%}
Generate a UUID (different each time)
{%- endcomment -%}
{% assign randomId = 'Resource' | generate_uuid -%}
"id": "{{ randomId }}"
```

**`generate_id_input`**
```liquid
{%- comment -%}
Generate a deterministic hash-based ID
Same input → same output (useful for idempotency)
{%- endcomment -%}
{% assign inputData = PID."3"."1".Value | append: PID."5"."1".Value -%}
{% assign deterministicId = inputData | generate_id_input -%}
"id": "{{ deterministicId }}"
```

#### Data Transformation Filters

**`to_json_string`**
```liquid
{%- comment -%}
Serialize object to JSON string
{%- endcomment -%}
{% assign myObject = {"key": "value"} -%}
"data": {{ myObject | to_json_string }}
```

**`to_array`**
```liquid
{%- comment -%}
Convert single value or object to array
{%- endcomment -%}
{% assign singleValue = "test" -%}
{% assign arrayValue = singleValue | to_array -%}
```

**`match`**
```liquid
{%- comment -%}
Extract data using regex
{%- endcomment -%}
{% assign phoneNumber = PID."13".Value | match: '\d{3}-\d{3}-\d{4}' -%}
```

**`gzip`**
```liquid
{%- comment -%}
Compress and base64 encode data
{%- endcomment -%}
"compressedData": "{{ largeText | gzip }}"
```

**`sha1_hash`**
```liquid
{%- comment -%}
Generate SHA1 hash
{%- endcomment -%}
"hash": "{{ data | sha1_hash }}"
```

#### Math Filters

**`sign`**
```liquid
{%- comment -%}
Get sign of number (-1, 0, or 1)
{%- endcomment -%}
{% assign signValue = -42 | sign -%}  → -1
```

**`divide`**
```liquid
{%- comment -%}
Divide two numbers (float division)
{%- endcomment -%}
{% assign result = 10 | divide: 3 -%}  → 3.333...
```

**`truncate_number`**
```liquid
{%- comment -%}
Truncate number to specified decimal places
{%- endcomment -%}
{% assign truncated = 3.14159 | truncate_number: 2 -%}  → 3.14
```

### Custom Tags Reference

#### `{% evaluate %}`

```liquid
{%- comment -%}
Generate stable IDs using ID generation templates
Syntax: {% evaluate variableName using 'ID/TemplatePath' param1: value1, param2: value2 -%}
{%- endcomment -%}

{%- comment -%} Generate Patient ID {%- endcomment -%}
{% evaluate patientId using 'ID/Patient' PID: pidSegment, type: 'First' -%}

{%- comment -%} Generate Observation ID {%- endcomment -%}
{% evaluate observationId using 'ID/Observation' OBR: obrSegment, OBX: obxSegment -%}

{%- comment -%} Generate Bundle ID {%- endcomment -%}
{% evaluate bundleId using 'ID/Bundle' Data: mshSegment."10" -%}

{%- comment -%} Use the generated ID {%- endcomment -%}
"id": "{{ patientId }}",
"subject": {
    "reference": "Patient/{{ patientId }}"
}
```

The `evaluate` tag executes a sub-template that generates a deterministic ID based on the input data. The ID generation templates are located in `fhir_converter/templates/hl7v2/ID/`.

#### `{% include %}`

```liquid
{%- comment -%}
Include and render a sub-template
Syntax: {% include 'TemplatePath' param1: value1, param2: value2 -%}
Parameters become variables in the included template
{%- endcomment -%}

{%- comment -%} Include Patient resource template {%- endcomment -%}
{% include 'Resource/Patient' PID: pidSegment, PD1: pd1Segment, ID: patientId -%}

{%- comment -%} Include Observation resource template {%- endcomment -%}
{% include 'Resource/Observation' OBR: obrSegment, OBX: obxSegment, ID: observationId -%}

{%- comment -%} Include reference template {%- endcomment -%}
{% include 'Reference/Observation/Subject' ID: observationId, REF: fullPatientId -%}
```

### Best Practices for Templates

#### 1. **Check for Empty Values**

```liquid
{%- comment -%} GOOD: Check before using {%- endcomment -%}
{% if PID."5" and PID."5"."1" -%}
    "family": "{{ PID."5"."1".Value }}",
{% endif -%}

{%- comment -%} BETTER: Multiple checks {%- endcomment -%}
{% if PID."5"."1" != "" and PID."5"."1" != null -%}
    "family": "{{ PID."5"."1".Value }}",
{% endif -%}

{%- comment -%} BAD: No check (may output empty fields) {%- endcomment -%}
"family": "{{ PID."5"."1".Value }}",
```

#### 2. **Use Filters for Data Transformation**

```liquid
{%- comment -%} GOOD: Use appropriate filter {%- endcomment -%}
"birthDate": "{{ PID."7".Value | add_hyphens_date }}",
"timestamp": "{{ MSH."7".Value | format_as_date_time }}",

{%- comment -%} BAD: Manual string manipulation {%- endcomment -%}
"birthDate": "{{ PID."7".Value | slice: 0, 4 }}-{{ PID."7".Value | slice: 4, 2 }}-{{ PID."7".Value | slice: 6, 2 }}",
```

#### 3. **Generate IDs Consistently**

```liquid
{%- comment -%} GOOD: Use evaluate tag for stable IDs {%- endcomment -%}
{% evaluate patientId using 'ID/Patient' PID: pidSegment -%}
"id": "{{ patientId }}",
"subject": {"reference": "Patient/{{ patientId }}"}

{%- comment -%} BAD: Different IDs for same resource {%- endcomment -%}
"id": "{{ 'Patient' | generate_uuid }}",
"subject": {"reference": "Patient/{{ 'Patient' | generate_uuid }}"}
```

#### 4. **Handle Repeating Fields**

```liquid
{%- comment -%} GOOD: Check if repeats exist {%- endcomment -%}
{% if PID."3".Repeats and PID."3".Repeats.size > 0 -%}
    "identifier": [
        {% for repeat in PID."3".Repeats -%}
            {
                "value": "{{ repeat."1".Value }}",
                "system": "{{ repeat."4".Value }}"
            }{% unless forloop.last %},{% endunless %}
        {% endfor -%}
    ],
{% endif -%}

{%- comment -%} BAD: Assume repeats exist {%- endcomment -%}
"identifier": [
    {% for repeat in PID."3".Repeats -%}
        ...
    {% endfor -%}
],
```

#### 5. **Use Comments**

```liquid
{%- comment -%}
This template processes the PID segment to create a FHIR Patient resource.
It extracts:
- Patient identifiers (PID-3)
- Patient name (PID-5)
- Birth date (PID-7)
- Gender (PID-8)
- Address (PID-11)
- Phone numbers (PID-13, PID-14)
{%- endcomment -%}

{% assign pid = firstSegments.PID -%}

{%- comment -%} Extract patient identifiers {%- endcomment -%}
{% if pid."3" -%}
    "identifier": [
        ...
    ],
{% endif -%}
```

---

## JSON5 Processing

### What Gets Removed

The `Json5SkipEmptyLoader` automatically removes:

1. **Null values**
```json5
// Input
{
    "name": "John",
    "email": null
}

// Output
{
    "name": "John"
}
```

2. **Empty strings**
```json5
// Input
{
    "name": "John",
    "suffix": ""
}

// Output
{
    "name": "John"
}
```

3. **Empty objects**
```json5
// Input
{
    "name": "John",
    "address": {}
}

// Output
{
    "name": "John"
}
```

4. **Empty arrays**
```json5
// Input
{
    "name": "John",
    "identifiers": []
}

// Output
{
    "name": "John"
}
```

### Merging Behavior

When the same key appears multiple times, the loader merges intelligently:

#### Array Merging
```json5
// From template (two includes generate same key)
{
    "identifier": [{"system": "sys1", "value": "123"}]
}
{
    "identifier": [{"system": "sys2", "value": "456"}]
}

// Merged output
{
    "identifier": [
        {"system": "sys1", "value": "123"},
        {"system": "sys2", "value": "456"}
    ]
}
```

#### Dictionary Merging
```json5
// From template
{
    "name": {"family": "Johnson"}
}
{
    "name": {"given": ["Sarah"]}
}

// Merged output
{
    "name": {
        "family": "Johnson",
        "given": ["Sarah"]
    }
}
```

#### Scalar Overwriting
```json5
// From template (second value wins)
{
    "status": "preliminary"
}
{
    "status": "final"
}

// Output
{
    "status": "final"
}
```

### Leveraging JSON5 in Templates

#### Use Trailing Commas Freely

```liquid
{
    "resourceType": "Patient",
    "id": "{{ patientId }}",
    {% if PID."5" -%}
        "name": [{
            "family": "{{ PID."5"."1".Value }}",  
        }],  {%- comment -%} Trailing comma is fine {%- endcomment -%}
    {% endif -%}
    {%- comment -%} Trailing comma in main object too {%- endcomment -%}
}
```

#### Add Comments for Documentation

```json5
{
    "resourceType": "Observation",
    // This observation represents a blood pressure reading
    "id": "{{ observationId }}",
    "code": {
        // LOINC code for systolic blood pressure
        "coding": [{
            "system": "http://loinc.org",
            "code": "8480-6",
        }]
    }
}
```

#### Don't Worry About Empty Fields

```liquid
{%- comment -%}
No need to check if every field has a value
JSON5 loader will remove empty ones automatically
{%- endcomment -%}
{
    "resourceType": "Patient",
    "id": "{{ patientId }}",
    "name": [{
        "family": "{{ PID."5"."1".Value }}",
        "given": ["{{ PID."5"."2".Value }}"],
        "suffix": ["{{ PID."5"."4".Value }}"],  {%- comment -%} May be empty {%- endcomment -%}
    }],
    "gender": "{{ PID."8".Value | downcase }}",
    "birthDate": "{{ PID."7".Value | add_hyphens_date }}",
    "address": [],  {%- comment -%} May be empty {%- endcomment -%}
}
```

---

## Advanced Topics

### Custom Template Creation

#### 1. Create Template Structure

```
my-templates/
├── MY_MESSAGE_TYPE.liquid          # Main message template
├── Resource/
│   ├── _MyCustomResource.liquid   # Custom resource template
│   └── _Patient.liquid            # Override default Patient template
└── ID/
    └── _MyCustomResource.liquid   # ID generator for custom resource
```

#### 2. Main Message Template

```liquid
{%- comment -%}
File: MY_MESSAGE_TYPE.liquid
{%- endcomment -%}

{% assign firstSegments = hl7v2Data | get_first_segments: 'MSH|MY1|MY2' -%}
{% assign my3SegmentLists = hl7v2Data | get_segment_lists: 'MY3' -%}

{% evaluate bundleID using 'ID/Bundle' Data: firstSegments.MSH."10" -%}

{
    "resourceType": "Bundle",
    "type": "batch",
    "id": "{{ bundleID }}",
    "entry": [
        {% for my3Segment in my3SegmentLists.MY3 -%}
            {% evaluate resourceId using 'ID/MyCustomResource' MY3: my3Segment -%}
            {% include 'Resource/MyCustomResource' MY3: my3Segment, ID: resourceId -%}
        {% endfor -%}
    ]
}
```

#### 3. Resource Template

```liquid
{%- comment -%}
File: Resource/_MyCustomResource.liquid
Parameters: MY3, ID
{%- endcomment -%}

{
    "fullUrl": "MyCustomResource/{{ ID }}",
    "resource": {
        "resourceType": "MyCustomResource",
        "id": "{{ ID }}",
        {% if MY3."1" -%}
            "identifier": [{
                "value": "{{ MY3."1".Value }}"
            }],
        {% endif -%}
        {% if MY3."2" -%}
            "status": "{{ MY3."2".Value | downcase }}",
        {% endif -%}
    }
},
```

#### 4. ID Generator Template

```liquid
{%- comment -%}
File: ID/_MyCustomResource.liquid
Parameters: MY3
{%- endcomment -%}

{% assign idInput = MY3."1".Value | append: '-' | append: MY3."2".Value -%}
{{ idInput | generate_id_input }}
```

### Custom Filters

Create custom filters for domain-specific transformations:

```python
# my_filters.py
from liquid import Environment
from liquid.filter import liquid_filter

@liquid_filter
def convert_code(hl7_code: str) -> str:
    """Convert HL7 code to FHIR code"""
    code_map = {
        "M": "male",
        "F": "female",
        "U": "unknown"
    }
    return code_map.get(hl7_code, "unknown")

def register_custom_filters(env: Environment):
    env.add_filter("convert_code", convert_code)
```

Use in templates:
```liquid
"gender": "{{ PID."8".Value | convert_code }}"
```

### Error Handling

```python
from fhir_converter.renderers import Hl7v2Renderer
from fhir_converter.exceptions import RenderingError

renderer = Hl7v2Renderer()

try:
    with open("message.hl7", "r") as hl7v2_file:
        result = renderer.render_fhir_string("ORU_R01", hl7v2_file)
except RenderingError as e:
    print(f"Rendering failed: {e}")
    print(f"Cause: {e.__cause__}")
except FileNotFoundError:
    print("HL7v2 file not found")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Troubleshooting

### Common Issues

#### Issue 1: Empty FHIR Resources

**Problem:**
```json
{
    "resourceType": "Patient",
    "id": "patient-123"
}
```

**Cause:** All optional fields were empty or null.

**Solution:** Ensure template extracts data from correct HL7v2 fields.

```liquid
{%- comment -%} DEBUG: Print segment content {%- endcomment -%}
{% comment %}
PID segment: {{ PID.Value }}
Field 5: {{ PID."5".Value }}
{% endcomment %}
```

#### Issue 2: Invalid FHIR Format

**Problem:**
```json
{
    "resourceType": "Patient",
    "name": [,]  // Invalid: empty array with comma
}
```

**Cause:** Template generates empty array elements.

**Solution:** Check for empty values before adding to arrays.

```liquid
{%- comment -%} GOOD {%- endcomment -%}
{% if PID."5" and PID."5"."1" -%}
    "name": [{
        "family": "{{ PID."5"."1".Value }}"
    }],
{% endif -%}

{%- comment -%} BAD {%- endcomment -%}
"name": [{
    "family": "{{ PID."5"."1".Value }}"
}],
```

#### Issue 3: Duplicate Resources

**Problem:** Same resource appears multiple times in Bundle.

**Cause:** Multiple template includes generate same resource without proper ID generation.

**Solution:** Use `{% evaluate %}` tag with consistent parameters.

```liquid
{%- comment -%} GOOD: Same input → same ID {%- endcomment -%}
{% evaluate patientId using 'ID/Patient' PID: pidSegment, type: 'First' -%}

{%- comment -%} BAD: Different IDs each time {%- endcomment -%}
{% assign patientId = 'Patient' | generate_uuid -%}
```

#### Issue 4: Field Access Returns Nothing

**Problem:**
```liquid
{{ PID."5"."1".Value }}  {%- comment -%} Outputs nothing {%- endcomment -%}
```

**Cause:** Field doesn't exist or segment not found.

**Debug:**
```liquid
{% comment %}
Segment exists: {{ PID != null }}
Field 5 exists: {{ PID."5" != null }}
Component 1 exists: {{ PID."5"."1" != null }}
Value: "{{ PID."5"."1".Value }}"
{% endcomment %}
```

#### Issue 5: Date Format Errors

**Problem:** Invalid FHIR date format.

**Solution:** Use appropriate filter.

```liquid
{%- comment -%} For full timestamp (dateTime) {%- endcomment -%}
"timestamp": "{{ MSH."7".Value | format_as_date_time }}",

{%- comment -%} For date only {%- endcomment -%}
"birthDate": "{{ PID."7".Value | add_hyphens_date }}",

{%- comment -%} For custom format {%- endcomment -%}
"date": "{{ MSH."7".Value | date: 'yyyy-MM-dd' }}"
```

### Debug Techniques

#### 1. Print Segment Content

```liquid
{% comment %}
=== DEBUG: PID Segment ===
Full segment: {{ PID.Value }}

Field 3 (ID): {{ PID."3".Value }}
  Component 1: {{ PID."3"."1".Value }}
  Component 4: {{ PID."3"."4".Value }}

Field 5 (Name): {{ PID."5".Value }}
  Component 1: {{ PID."5"."1".Value }}
  Component 2: {{ PID."5"."2".Value }}

Field 7 (DOB): {{ PID."7".Value }}
Field 8 (Gender): {{ PID."8".Value }}
=== END DEBUG ===
{% endcomment %}
```

#### 2. Check Segment Availability

```liquid
{% comment %}
Available segments:
{% for meta_item in hl7v2Data.meta -%}
  - {{ meta_item }}
{% endfor -%}
{% endcomment %}
```

#### 3. Validate Filter Output

```liquid
{% comment %}
First segments:
{% for segment_key in firstSegments -%}
  {{ segment_key }}: {{ firstSegments[segment_key].Value | truncate: 50 }}
{% endfor -%}
{% endcomment %}
```

---

## Summary

This guide covered:

1. **Data Extraction**: How HL7v2 messages are parsed into hierarchical structures
2. **Liquid Templates**: How to access and transform HL7v2 data using custom filters and tags
3. **JSON5 Processing**: How empty fields are removed and duplicates merged automatically
4. **Advanced Topics**: Creating custom templates, filters, and error handling
5. **Troubleshooting**: Common issues and debug techniques

The key to effective use of this library is understanding:
- The hierarchical structure of parsed HL7v2 data
- How to navigate that structure in Liquid templates
- How filters transform data for FHIR compliance
- How JSON5 processing cleans up the output automatically

For more examples, explore the bundled templates in `fhir_converter/templates/hl7v2/`.
