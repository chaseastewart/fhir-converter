# python-fhir-converter

Provides a python native version of the [reference implementation](https://github.com/microsoft/FHIR-Converter) written in C#. The goal is to generate 1:1 output for the same [templates](https://github.com/microsoft/FHIR-Converter/tree/main/data/Templates). Built on the back of [python-liquid](https://github.com/jg-rp/liquid)

**Table of Contents**

- [Install](#install)
- [Links](#links)
- [Example](#example)
- [Related Projects](#related-projects)

## Install

Install Python FHIR Converter using [Pipenv](https://pipenv.pypa.io/en/latest/):

```shell
$ pipenv install -u python-fhir-converter
```

Or [pip](https://pip.pypa.io/en/stable/getting-started/):

```shell
$ pip install python-fhir-converter
```

## Links

- PyPi: https://pypi.org/project/python-fhir-converter/
- Source Code: https://github.com/chaseastewart/fhir-converter
- Issue Tracker: https://github.com/chaseastewart/fhir-converter/issues

## Example

```python
from fhir_converter.processors import CcdaProcessor

processor = CcdaProcessor.from_template_dir(TEMPLATE_DIR)
with open("data/sample/ccda/Discharge_Summary.ccda") as ccda_file:
    print(processor.convert(template_name="DischargeSummary", xml_input=ccda_file))
```

## Related Projects

- [python-liquid](https://github.com/jg-rp/liquid) Python engine for the Liquid template language.
