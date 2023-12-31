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
from functools import partial
from pathlib import Path
from fhir_converter.loaders import get_file_system_loader
from fhir_converter.renderers import (
    CcdaRenderer,
    get_environment,
    render_files_to_dir,
    render_to_dir,
)

templates_dir, sample_data_dir, data_out_dir = (
    Path("data/templates/ccda"),
    Path("data/sample/ccda"),
    Path("data/out")
)
from_file = sample_data_dir.joinpath("CCD.ccda")

# Render the file to string using the rendering defaults indenting the output
with open(from_file) as xml_in:
    # indent is provided, any other kwargs supported by dump may be provided
    print(CcdaRenderer().render_fhir_string("CCD", xml_in, indent=1))

# Create a renderer that will load the user defined templates into the rendering env
renderer = CcdaRenderer(
    get_environment(
        loader=get_file_system_loader(search_path=templates_dir)
    )
)

# Render the file to the output directory using the default CCD template
render_to_dir(
    render=partial(renderer.render_fhir, "CCD"),
    from_file=from_file,
    to_dir=data_out_dir,
)

# Render all of the sample files to the output directory using the user defined
# pampi (problems, allergies, meds, procedures, immunizations) template
render_files_to_dir(
    render=partial(renderer.render_fhir, "pampi"),
    from_dir=sample_data_dir,
    to_dir=data_out_dir,
    path_filter=lambda p: p.suffix in (".ccda", ".xml"),
)
```

## Related Projects

- [python-liquid](https://github.com/jg-rp/liquid) Python engine for the Liquid template language.
