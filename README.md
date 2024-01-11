<p align="center">
  <img src="https://chaseastewart.github.io/fhir-converter/logo.png" width="360" alt="Python FHIR Converter"/>
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
</p>

---

Provides a python native version of [FHIR-Converter](https://github.com/microsoft/FHIR-Converter) written in C#.

The key features are:

* **Fastish**: Leverages Cython where possible 
* **Move fast**: Designed to be extensibile. Use the thin rendering API or leverage the builtin parts
* **Easy**: Designed to be easy to use, extend and deploy.
* **Robust**: Get production-ready code.

Limitations:
* **Only CDA->FHIR** is currently builtin. Additional work is needed to implement the filters, etc to support FHIR->FHIR and HL7v2->FHIR and back.
* **Python-liquid requires** a comma between parameters to filters. This does not appear to be a restriction with DotLiquid. As a result templates brought to this environment may need commas added.

Built on the back of:

* [FHIR-Converter](https://github.com/microsoft/FHIR-Converter)
* [python-liquid](https://github.com/jg-rp/liquid)


**Table of Contents**

- [Install](#install)
- [Links](#links)
- [Basic Usage](#basic-usage)
- [Command line interface](#command-line-interface)
- [Templates](#templates)
- [Benchmark](#benchmark)
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


## Basic Usage
See [examples](./scripts/examples.py) for more indepth usage / usecases.

```python
from fhir_converter.renderers import  CcdaRenderer

# Render the file to string using the rendering defaults
with open("data/sample/ccda/ccd.ccda") as xml_in:
    # indent is provided, any other kwargs supported by dump may be provided
    print(CcdaRenderer().render_fhir_string("CCD", xml_in, indent=1))
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

fhir-converter % fhir_converter_cli --template-dir ./data/templates/ccda --from-dir ./data/sample/ccda --to-dir ./data/out --template-name pampi
---------------------------------------------------------------
RENDER SUCCESS
---------------------------------------------------------------
Total time: 0.32s
Finished at: 2024-01-11 10:49:44.182033
Final Memory: 37M
---------------------------------------------------------------
```


## Templates

Templates can be loaded from any python-liquid supported mechanism. To make packaging easier a ResourceLoader is provided. When a rendering environment is not provided, templates will be loaded from the [module](/fhir_converter/templates/). To ease the creation of user defined templates a TemplateSystemLoader is provided that allows templates to be loaded from a primary and optionally default location. This allows user defined templates to reference templates in the default location. The example user defined [templates](data/templates/ccda) reuse the default section / header templates.


## Benchmark

You can run the [benchmark](./scripts/benchmark.py) from the root of the source tree. Test rig is a 14-inch, 2021 Macbook Pro with the binned M1 PRO not in low power mode.
```text
   Ordered by: cumulative time

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        3    0.000    0.000   16.998    5.666 ../scripts/benchmark.py:75(render_samples)
       22    0.003    0.000   16.997    0.773 ../fhir-converter/fhir_converter/renderers.py:187(render_files_to_dir)
      484    0.002    0.000   16.968    0.035 ../fhir-converter/fhir_converter/renderers.py:220(render_to_dir)
      484    0.010    0.000   16.842    0.035 ../fhir-converter/fhir_converter/renderers.py:93(render_fhir)
      484    0.003    0.000   14.674    0.030 ../fhir-converter/fhir_converter/renderers.py:117(render_to_fhir)
```
The test fixture profiles the converter using a single thread. The samples are rendered using all of the builtin templates along with the handful of user defined templates. The percall time is relative to the rendering template being used, the number of files being rendered (there is some warm up) and the size of the files to be rendered. In a 60 minute period in similar conditions a little over 100K CDA documents could be rendered into FHIR bundles. Note: including the original CDA document in the bundle as a DocumentReference adds noticable overhead to the render. Omitting this via a user defined template is recommended if this is not required for your usecase.


## Related Projects

- [FHIR-Converter](https://github.com/microsoft/FHIR-Converter)
- [python-liquid](https://github.com/jg-rp/liquid)
- [pyjson5](https://github.com/Kijewski/pyjson5)
- [xmltodict](https://github.com/martinblech/xmltodict)