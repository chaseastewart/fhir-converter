# Python FHIR Converter Change Log

## Version 0.5.1
**Bug Fixes: {% evaluate %} Tag Parameter Passing**

### 🐛 Bug Fixes
- **Fixed {% evaluate %} tag parameter passing** - Corrected regression where the `{% evaluate %}` tag was not passing parameters to rendered templates after liquid 2.0 migration
  - **Root cause**: The parsing loop `while not tokens.eof` never executed because `tokens.eof` returns a Token object instead of a boolean
  - **Solution**: Changed to `while tokens.current.kind != TOKEN_EOF` and used `parse_primitive()` instead of `FilteredExpression.parse()`
  - **Impact**: Device resources now correctly generate distinct UUIDs based on their segment parameters (AIG, HD, etc.) instead of all using the same empty UUID
  
- **Fixed empty Device references in Appointment participants** - Corrected typo in `_Appointment.liquid` template
  - **Root cause**: Template used `device_ID_AIG_3` (uppercase ID) instead of `device_Id_AIG_3` (lowercase Id as defined in evaluate tag)
  - **Impact**: Appointment participants now correctly reference Device resources with valid UUIDs instead of empty references (`"Device/"`)

### ✅ Tests Added
- **test_evaluate_tag.py**: Three new regression tests
  - `test_evaluate_tag_passes_parameters_to_template`: Verifies evaluate tag passes parameters correctly and generates distinct UUIDs
  - `test_evaluate_tag_with_multiple_parameters`: Tests multiple comma-separated parameters
  - `test_device_references_in_appointment_have_uuids`: Ensures Device references in Appointment have valid UUIDs

### 📝 Technical Details
- Updated `EvaluateTag.parse` in `tags.py` to correctly iterate through argument tokens
- Fixed token stream handling to match python-liquid 2.0 `KeywordArgument.parse` pattern
- Added imports: `TOKEN_EOF`, `TOKEN_WORD`, `parse_primitive`

## Version 0.5.0
**Major Update: Migration to python-liquid 2.0**

### 🚀 Breaking Changes
- **Upgraded to python-liquid 2.0** - Major dependency upgrade with breaking API changes
- **Minimum Python version**: Now requires Python 3.8+ (aligned with python-liquid 2.0)

### ✨ New Features  
- **FHIR Syntax Extension**: Added custom liquid extension to maintain backward compatibility with `MSH."7"` syntax
- **Enhanced Template Support**: Full support for HL7v2 templates with quoted numeric property access
- **Improved Error Handling**: Better error messages and syntax validation

### 🔧 Technical Improvements
- **API Modernization**: Updated all internal APIs to use python-liquid 2.0 interfaces
- **Filter Migration**: Successfully migrated all 176 custom filters to new API
- **Tag Migration**: Updated custom tags (`evaluate`, `mergeDiff`) for liquid 2.0 compatibility  
- **Performance**: Leverages liquid 2.0 performance improvements and stricter parsing
- **Test Coverage**: Maintained 504 passing tests with comprehensive coverage

### 🐛 Bug Fixes
- **Template Syntax**: Fixed 4 template syntax errors discovered during migration (`X."400"`, `PV1.."16"`, etc.)
- **Loader Compatibility**: Updated template loaders for liquid 2.0 caching behavior
- **Expression Parsing**: Enhanced expression parsing for complex FHIR property paths

### 📦 Dependencies
- **python-liquid**: Updated from `~1.12.1` to `^2.0.0`
- All other dependencies remain compatible

### 🔄 Migration Notes
- **Full Backward Compatibility**: All existing templates continue to work without modification
- **Automatic Activation**: FHIR syntax extension is automatically enabled for all renders
- **No Breaking Changes**: Public API remains unchanged for end users

## Version 0.4.10
- Remove depency from pyjson5 replace with json-five slower but more efficient and build on python 3.13

## Version 0.4.0
- Add support for HL7v2 to FHIR conversion. See [#12](https://github.com/chaseastewart/fhir-converter/pull/12)

## Version 0.3.0
- Render narrative text from the CDA to xhtml to include in the Composition resource. See [#11](https://github.com/chaseastewart/fhir-converter/issues/11)
- Fix bug in CDA to R4 Immunization template to correctly map lotNumberText to lotNumber.

## Version 0.2.0
- Map C-CDA Allergy to FHIR Allergy Intolerance Category. See [#6](https://github.com/chaseastewart/fhir-converter/issues/6)
- Renamed `render_to_fhir_internal` to `render` to simplify `BaseFhirRenderer` API.

## Version 0.1.0
- Fixed missing required AllergyIntolerance.reaction.manifestation for CDA->FHIR conversion. [_AllergyIntolerance.liquid](https://github.com/chaseastewart/fhir-converter/blob/69ca8f81cade9a480e624e09bfa3c4aa1663a2bf/fhir_converter/templates/ccda/Resource/_AllergyIntolerance.liquid#L23) incorrectly created an additional reaction for the severity. See [#3](https://github.com/chaseastewart/fhir-converter/issues/3)
- Remove time when timezone is not present in CDA datetime to conform with FHIR datetime.  See [#2](https://github.com/chaseastewart/fhir-converter/issues/2)
- Added `CachingTemplateSystemLoader`. `TemplateSystemLoader` now extends `ChoiceLoader` to better align with `python-liquid`.
- Added `make_template_system_loader()`, a factory function that returns a `TemplateSystemLoader` or `CachingTemplateSystemLoader` depending on its arguments.
- Renamed `get_environment` factory function to `make_environment` to align with a consistent naming convention.
- Moved `RenderingError` and `fail` to exceptions.py.
- Removed deprecated `ResourceLoader` and `CachedChoiceLoader`. 
- Now depends on [python-liquid](https://pypi.org/project/python-liquid/) = 1.12.1.

## Version 0.0.22
- `ResourceLoader` and `CachedChoiceLoader` are depreciated and will be removed in 0.1.0. Use `PackageLoader` and `CachingChoiceLoader` instead.
- Run tests on mac, windows and ubuntu.
- Now depends on [python-liquid](https://pypi.org/project/python-liquid/) = 1.11.0.