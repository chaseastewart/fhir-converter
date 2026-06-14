# HL7v2 to FHIR Conversion - Quick Reference

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        HL7v2 Raw Message (Text)                          │
│  MSH|^~\&|CardioSystem|Hospital|...                                     │
│  PID|1||123456789||Johnson^Sarah^Marie||19850312|F|...                  │
│  OBR|1|BP001|BP001|85354-9^Blood pressure panel^LN|...                  │
│  OBX|1|NM|8480-6^Systolic BP^LN|1|135|mm[Hg]|...                       │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        Hl7v2DataParser.parse()                           │
│  • Extract encoding characters (|, ^, ~, \, &)                          │
│  • Split by line breaks → segments                                       │
│  • Split by | → fields                                                   │
│  • Split by ^ → components                                               │
│  • Split by & → subcomponents                                            │
│  • Split by ~ → repeating fields                                         │
│  • Normalize text (unescape sequences)                                   │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      Hl7v2Data (Structured Object)                       │
│  meta: ["MSH", "PID", "OBR", "OBX", ...]                               │
│  data: [                                                                 │
│    Hl7v2Segment(                                                        │
│      normalized_text: "MSH|^~\&|...",                                   │
│      fields: [                                                           │
│        Hl7v2Field(                                                      │
│          value: "CardioSystem^2.16.840^ISO",                           │
│          components: [                                                   │
│            Hl7v2Component(value: "CardioSystem", ...),                 │
│            Hl7v2Component(value: "2.16.840", ...),                     │
│            Hl7v2Component(value: "ISO", ...)                           │
│          ]                                                               │
│        ),                                                                │
│        ...                                                               │
│      ]                                                                   │
│    ),                                                                    │
│    ...                                                                   │
│  ]                                                                       │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        Liquid Template Engine                            │
│                                                                          │
│  1. Load template: ORU_R01.liquid                                       │
│                                                                          │
│  2. Extract segments with filters:                                      │
│     {% assign firstSegments = hl7v2Data                                 │
│        | get_first_segments: 'MSH|PID' -%}                             │
│                                                                          │
│  3. Convert segments to dictionaries:                                   │
│     segment_to_dict() → {                                               │
│       "Value": "PID|1||123456...",                                     │
│       "3": {                                                            │
│         "Value": "123456789",                                          │
│         "1": {"Value": "123456789"}                                    │
│       },                                                                │
│       "5": {                                                            │
│         "Value": "Johnson^Sarah^Marie",                                │
│         "1": {"Value": "Johnson"},                                     │
│         "2": {"Value": "Sarah"}                                        │
│       }                                                                 │
│     }                                                                   │
│                                                                          │
│  4. Access data in template:                                            │
│     {{ firstSegments.PID."5"."1".Value }} → "Johnson"                 │
│                                                                          │
│  5. Generate IDs:                                                       │
│     {% evaluate patientId using 'ID/Patient' PID: pid -%}             │
│                                                                          │
│  6. Include sub-templates:                                              │
│     {% include 'Resource/Patient' PID: pid, ID: patientId -%}         │
│                                                                          │
│  7. Apply filters for formatting:                                       │
│     {{ MSH."7".Value | format_as_date_time }}                          │
│     20241007143000-0500 → 2024-10-07T14:30:00-05:00                   │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    JSON5 Output (from template)                          │
│  {                                                                       │
│    "resourceType": "Bundle",                                            │
│    "type": "batch",                                                     │
│    "id": "bundle-123",                                                  │
│    "entry": [                                                           │
│      {                                                                  │
│        "fullUrl": "Patient/patient-123",                               │
│        "resource": {                                                    │
│          "resourceType": "Patient",                                     │
│          "id": "patient-123",                                          │
│          "name": [{                                                    │
│            "family": "Johnson",                                        │
│            "given": ["Sarah", "Marie"],                                │
│            "suffix": "",  // Empty field                               │
│          }],                                                           │
│          "address": [],  // Empty array                                │
│        },  // Trailing comma                                           │
│      },                                                                 │
│      {                                                                  │
│        "fullUrl": "Observation/obs-systolic",                          │
│        "resource": {                                                    │
│          "resourceType": "Observation",                                 │
│          "code": {                                                      │
│            "coding": [{                                                 │
│              "system": "http://loinc.org",                             │
│              "code": "8480-6",                                         │
│            }],                                                          │
│          },                                                             │
│          "valueQuantity": {                                             │
│            "value": 135,                                                │
│            "unit": "mm[Hg]",                                           │
│          },                                                             │
│        },                                                               │
│      },                                                                 │
│    ]                                                                    │
│  }                                                                       │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                Json5SkipEmptyLoader (Custom Parser)                      │
│                                                                          │
│  • Parse JSON5 (handle comments, trailing commas)                       │
│  • Remove empty values:                                                  │
│    - null                                                                │
│    - ""                                                                  │
│    - {}                                                                  │
│    - []                                                                  │
│  • Merge duplicate keys:                                                 │
│    - Arrays: append elements                                             │
│    - Objects: merge properties                                           │
│    - Scalars: last value wins                                            │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    Cleaned Python Dictionary                             │
│  {                                                                       │
│    "resourceType": "Bundle",                                            │
│    "type": "batch",                                                     │
│    "id": "bundle-123",                                                  │
│    "entry": [                                                           │
│      {                                                                  │
│        "fullUrl": "Patient/patient-123",                               │
│        "resource": {                                                    │
│          "resourceType": "Patient",                                     │
│          "id": "patient-123",                                          │
│          "name": [{                                                    │
│            "family": "Johnson",                                        │
│            "given": ["Sarah", "Marie"]                                 │
│          }]                                                            │
│        }                                                               │
│      },                                                                 │
│      {                                                                  │
│        "fullUrl": "Observation/obs-systolic",                          │
│        "resource": {                                                    │
│          "resourceType": "Observation",                                 │
│          "code": {                                                      │
│            "coding": [{                                                 │
│              "system": "http://loinc.org",                             │
│              "code": "8480-6"                                          │
│            }]                                                           │
│          },                                                             │
│          "valueQuantity": {                                             │
│            "value": 135,                                                │
│            "unit": "mm[Hg]"                                            │
│          }                                                              │
│        }                                                               │
│      }                                                                  │
│    ]                                                                    │
│  }                                                                       │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     post_process_fhir()                                  │
│                                                                          │
│  • Merge duplicate resources (same resourceType + id)                   │
│  • Consolidate extensions:                                              │
│    If two consecutive entries have same resourceType and second only    │
│    has extensions, merge extensions into first entry                    │
│  • Remove merged duplicates                                             │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      Final FHIR Bundle (JSON)                            │
│  Valid, clean FHIR R4 Bundle with:                                      │
│  • No empty fields                                                       │
│  • No duplicate resources                                                │
│  • Merged extensions                                                     │
│  • Proper FHIR formatting                                                │
└──────────────────────────────────────────────────────────────────────────┘
```

## Key Components Reference

### 1. Parser Components
```python
Hl7v2EncodingCharacters       # Stores separators: |, ^, ~, \, &
Hl7v2Segment                  # Segment with normalized text + fields
Hl7v2Field                    # Field with value, components, repeats
Hl7v2Component                # Component with value + subcomponents
Hl7v2Data                     # Top-level: meta[] + data[]
```

### 2. Key Filters
```liquid
get_first_segments            # Get first occurrence of segments
get_segment_lists             # Get all occurrences of segments
get_related_segment_list      # Get child segments after parent
get_parent_segment            # Find parent of child segment
format_as_date_time           # HL7v2 timestamp → FHIR dateTime
add_hyphens_date              # HL7v2 date → FHIR date
generate_uuid                 # Generate random UUID
generate_id_input             # Generate deterministic hash ID
```

### 3. Key Tags
```liquid
{% evaluate var using 'ID/Template' params -%}    # Generate stable ID
{% include 'Resource/Type' params -%}             # Include sub-template
{% comment %} ... {% endcomment %}                # Add comments
```

### 4. Data Access Pattern
```liquid
{%- comment -%}
segment."field"."component"."subcomponent".Value
{%- endcomment -%}

{{ MSH."3".Value }}                    # Full field
{{ MSH."3"."1".Value }}                # First component
{{ PID."5"."1".Value }}                # Patient family name
{{ PID."3".Repeats[0]."1".Value }}     # First repeat, first component
```

## Common HL7v2 Field References

### MSH (Message Header)
```liquid
MSH."3"         # Sending Application
MSH."4"         # Sending Facility
MSH."5"         # Receiving Application
MSH."6"         # Receiving Facility
MSH."7"         # Message DateTime
MSH."9"         # Message Type (MSG^ORU^ORU_R01)
MSH."10"        # Message Control ID
```

### PID (Patient Identification)
```liquid
PID."2"         # Patient ID (External)
PID."3"         # Patient ID (Internal)
PID."5"         # Patient Name (XPN)
  ."1"          #   Family Name
  ."2"          #   Given Name
  ."3"          #   Middle Name
PID."7"         # Birth Date/Time
PID."8"         # Administrative Sex
PID."11"        # Patient Address (XAD)
PID."13"        # Phone Number - Home
PID."14"        # Phone Number - Business
```

### OBR (Observation Request)
```liquid
OBR."2"         # Placer Order Number
OBR."3"         # Filler Order Number
OBR."4"         # Universal Service Identifier (CE)
  ."1"          #   Identifier
  ."2"          #   Text
  ."3"          #   Coding System
OBR."7"         # Observation Date/Time
OBR."16"        # Ordering Provider
```

### OBX (Observation Result)
```liquid
OBX."2"         # Value Type (NM, ST, CE, etc.)
OBX."3"         # Observation Identifier (CE)
  ."1"          #   Identifier
  ."2"          #   Text
  ."3"          #   Coding System
OBX."5"         # Observation Value
OBX."6"         # Units (CE)
OBX."7"         # Reference Range
OBX."8"         # Abnormal Flags
OBX."11"        # Observation Result Status
OBX."14"        # Date/Time of Observation
```

## Example: Complete Conversion

### Input HL7v2
```hl7
MSH|^~\&|CardioSystem|Hospital|EMR|HIE|20241007143000-0500||ORU^R01|MSG001|P|2.5.1
PID|1||123456789||Johnson^Sarah^Marie||19850312|F
OBR|1|BP001|BP001|85354-9^Blood pressure panel^LN|||20241007143000
OBX|1|NM|8480-6^Systolic BP^LN|1|135|mm[Hg]|||F
OBX|2|NM|8462-4^Diastolic BP^LN|2|85|mm[Hg]|||F
```

### Template Snippet
```liquid
{% assign firstSegments = hl7v2Data | get_first_segments: 'MSH|PID' -%}
{% assign obrSegmentLists = hl7v2Data | get_segment_lists: 'OBR' -%}

{
  "resourceType": "Bundle",
  "type": "batch",
  "timestamp": "{{ firstSegments.MSH."7".Value | format_as_date_time }}",
  "entry": [
    {% evaluate patientId using 'ID/Patient' PID: firstSegments.PID -%}
    {% include 'Resource/Patient' PID: firstSegments.PID, ID: patientId -%}
  ]
}
```

### Output FHIR
```json
{
  "resourceType": "Bundle",
  "type": "batch",
  "timestamp": "2024-10-07T14:30:00-05:00",
  "entry": [
    {
      "fullUrl": "Patient/patient-123456789",
      "resource": {
        "resourceType": "Patient",
        "id": "patient-123456789",
        "identifier": [{"value": "123456789"}],
        "name": [{
          "family": "Johnson",
          "given": ["Sarah", "Marie"]
        }],
        "birthDate": "1985-03-12",
        "gender": "female"
      }
    }
  ]
}
```

## Performance Tips

1. **Use `get_first_segments`** for segments that appear only once (MSH, PID, PV1)
2. **Use `get_segment_lists`** for repeating segments (OBR, OBX, NTE)
3. **Check for empty values** before including fields in output
4. **Use `{% evaluate %}`** for stable ID generation (enables deduplication)
5. **Template caching** is enabled by default (300 templates)
6. **JSON5 loader** automatically removes empty fields (no manual cleanup needed)

## Troubleshooting Checklist

- [ ] Verify segment exists: `{% if firstSegments.PID %}`
- [ ] Check field has value: `{% if PID."5"."1" != "" and PID."5"."1" != null %}`
- [ ] Use correct filter for dates: `format_as_date_time` vs `add_hyphens_date`
- [ ] Generate stable IDs with `{% evaluate %}` not `generate_uuid`
- [ ] Add debug comments: `{% comment %}Field 5: {{ PID."5".Value }}{% endcomment %}`
- [ ] Validate JSON5 syntax (trailing commas are OK)
- [ ] Check for proper template file naming (sub-templates start with `_`)

## Additional Resources

- **Architecture Guide**: [ARCHITECTURE.md](ARCHITECTURE.md) - Comprehensive overview of system design
- **Technical Guide**: [TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md) - Detailed usage instructions
- **Templates**: `fhir_converter/templates/hl7v2/` - Built-in message templates
- **Filters**: `fhir_converter/filters.py` - All available custom filters
- **Parser**: `fhir_converter/parsers.py` - HL7v2 parsing implementation
