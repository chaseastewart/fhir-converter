<!--intro-start-->
<p align="center">
  <img src="https://github.com/chaseastewart/fhir-converter/blob/main/logo.png?raw=true" width="400" alt="Python FHIR Converter"/>
</p>
<p align="center">
    <em>Python FHIR converter, fastish, most nuts and bolts included, ready for production</em>
</p>
<p align="center">
<a href="https://github.com/chaseastewart/fhir-converter/blob/main/LICENSE" target="_blank">
  <img src="https://img.shields.io/pypi/l/python-liquid.svg?style=flat-square" alt="License">
</a>
<a href="https://pypi.org/project/python-fhir-converter/" target="_blank">
  <img src="https://img.shields.io/pypi/v/python-fhir-converter.svg?style=flat-square" alt="PyPi - Version">
</a>
<a href="https://pypi.org/project/python-fhir-converter" target="_blank">
  <img src="https://img.shields.io/pypi/pyversions/python-fhir-converter.svg?style=flat-square" alt="Python versions">
</a>
<br>
<a href="https://github.com/chaseastewart/fhir-converter/actions?query=workflow%3Apython-package">
    <img src="https://img.shields.io/github/actions/workflow/status/chaseastewart/fhir-converter/python-package.yml?style=flat-square&brach=main" />
</a>
<a href="https://coverage-badge.samuelcolvin.workers.dev/redirect/chaseastewart/fhir-converter" target="_blank">
    <img src="https://coverage-badge.samuelcolvin.workers.dev/chaseastewart/fhir-converter.svg" alt="Coverage">
</a>
<a href="https://black.readthedocs.io/en/stable/index.html" target="_blank">
  <img src="https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square" />
</a>
<br>
<a href="https://pepy.tech/project/python-fhir-converter" target="_blank">
  <img src="https://static.pepy.tech/badge/python-fhir-converter/month" />
</a>
</p>

---

Provides a python implementation of [FHIR-Converter](https://github.com/microsoft/FHIR-Converter) written in **C#**. This allows the data transformation to live and breath as any other python module in your favorite python based data pipeline framework

Whats supported:

* **CDA->FHIR R4**
* **STU3->FHIR R4**

Key features:

* **Fast.** Speed is relative. Minimizes overhead outside the rendering engine
* **Designed to be extensibile.** Use the thin rendering API or leverage the builtin parts
* **Designed to be easy to use, extend and deploy.** Use what's bundled or manage the environment your way
* **Multiple enhancement / bug corrections** included with the packaged CDA->R4 templates.

Limitations:

* **Additional work** is needed to support JSON->FHIR, HL7v2->FHIR and FHIR->HL7v2.
* **Comma between parameters**. Python-liquid **requires** a comma between parameters. Templates brought to this environment may need commas added.
* **Variable names when passing variables to a snippet**. Python-liquid **requires** the identifier / variable name. Templates brought to this environment may need changes. See [Resource.liquid](https://github.com/chaseastewart/fhir-converter/blob/main/fhir_converter/templates/stu3/Resource.liquid) as an example of a template that has been updated.
* **C# date format strings** are supported to an extent to mimimize the impact of migrating templates. See [filters](https://github.com/chaseastewart/fhir-converter/blob/cf3311cc2cc0acd3e9105dfc5ba23bb1d06d8393/fhir_converter/filters.py) for more information.

Built on the back of:

* [FHIR-Converter](https://github.com/microsoft/FHIR-Converter)
* [python-liquid](https://github.com/jg-rp/liquid)

<!--intro-end-->
**Table of Contents**

- [Install](#install)
- [Links](#links)
- [Basic Usage](#basic-usage)
- [Command line interface](#command-line-interface)
- [Templates](#templates)
- [Benchmark](#benchmark)
- [Related Projects](#related-projects)


<!--body-start-->
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

- [Documentation](https://chaseastewart.github.io/fhir-converter/): https://chaseastewart.github.io/fhir-converter/
- [PyPi](https://pypi.org/project/python-fhir-converter/): https://pypi.org/project/python-fhir-converter/
- [Source](https://github.com/chaseastewart/fhir-converter): https://github.com/chaseastewart/fhir-converter 
- [Issues](https://github.com/chaseastewart/fhir-converter/issues): https://github.com/chaseastewart/fhir-converter/issues


## Basic Usage
See [examples](https://github.com/chaseastewart/fhir-converter/blob/main/scripts/examples.py) for more indepth usage / usecases.

```python
from fhir_converter.renderers import  CcdaRenderer

with open("data/sample/ccda/ccd.ccda") as xml_in:
    print(CcdaRenderer().render_fhir_string("CCD", xml_in))
```

## Command line interface

The package comes with a CLI interface that can be invoked either by the script name
``fhir_converter_cli`` or as python module ``python -m fhir_converter``. The CLI allows you to transform a single file or an entire directory.

```bash
fhir_converter_cli  --from-file  ./data/sample/ccda/CCD.ccda --to-dir ./data/out --template-name CCD
---------------------------------------------------------------
RENDER SUCCESS
---------------------------------------------------------------
Total time: 0.14s
Finished at: 2024-01-11 10:49:44.182033
Final Memory: 32M
---------------------------------------------------------------
```


## Templates

Templates can be loaded from any python-liquid supported mechanism. To make packaging easier a [ResourceLoader](https://chaseastewart.github.io/fhir-converter/docstrings/loaders/#class-resourceloader) is provided. When a rendering environment is not provided, templates will be loaded from the module [resources](https://github.com/chaseastewart/fhir-converter/tree/main/fhir_converter/templates/). To ease the creation / reuse of templates a [TemplateSystemLoader](https://chaseastewart.github.io/fhir-converter/docstrings/loaders/#class-templatesystemloader) is provided that handles the template name conventions establised by [FHIR-Converter](https://github.com/microsoft/FHIR-Converter). This allows user defined templates to reference existing templates without change. The example user defined [templates](https://github.com/chaseastewart/fhir-converter/tree/main/data/templates/ccda) reuse the default section / header templates.


## Benchmark

You can run the [benchmark](https://github.com/chaseastewart/fhir-converter/blob/main/scripts/benchmark.py) from the root of the source tree. Test rig is a 14-inch, 2021 Macbook Pro with the M1 Pro. The benchmark performs the conversion for each template showing the min, max and mean times for the sample data used.

```text
Python Version=3.12.1
Iterations=20

Sample=data/sample/ccda/Discharge_Summary.ccda
CCD                     max=0.042       min=0.013       avg=0.015
ConsultationNote        max=0.015       min=0.013       avg=0.014
DischargeSummary        max=0.020       min=0.014       avg=0.014
HistoryandPhysical      max=0.015       min=0.013       avg=0.014
OperativeNote           max=0.014       min=0.010       avg=0.010
ProcedureNote           max=0.013       min=0.011       avg=0.012
ProgressNote            max=0.013       min=0.012       avg=0.012
ReferralNote            max=0.015       min=0.014       avg=0.014
TransferSummary         max=0.016       min=0.014       avg=0.014
LabsandVitals           max=0.009       min=0.008       avg=0.008
Pampi                   max=0.010       min=0.009       avg=0.009

Sample=data/sample/ccda/History_and_Physical.ccda
CCD                     max=0.053       min=0.018       avg=0.020
ConsultationNote        max=0.021       min=0.018       avg=0.019
DischargeSummary        max=0.018       min=0.016       avg=0.017
HistoryandPhysical      max=0.020       min=0.018       avg=0.019
OperativeNote           max=0.013       min=0.011       avg=0.012
ProcedureNote           max=0.015       min=0.014       avg=0.014
ProgressNote            max=0.017       min=0.015       avg=0.016
ReferralNote            max=0.022       min=0.018       avg=0.019
TransferSummary         max=0.021       min=0.019       avg=0.020
LabsandVitals           max=0.012       min=0.010       avg=0.011
Pampi                   max=0.013       min=0.012       avg=0.012
```


## Related Projects

- [FHIR-Converter](https://github.com/microsoft/FHIR-Converter)
- [python-liquid](https://github.com/jg-rp/liquid)
- [pyjson5](https://github.com/Kijewski/pyjson5)
- [xmltodict](https://github.com/martinblech/xmltodict)
<!--body-end-->