from functools import partial
from pathlib import Path

from liquid import FileExtensionLoader
from liquid.loaders import DictLoader

from fhir_converter.renderers import (
    BaseFhirRenderer,
    CcdaRenderer,
    Stu3FhirRenderer,
    ccda_default_loader,
    make_environment,
    render_files_to_dir,
    render_to_dir,
)
from fhir_converter.utils import mkdir

templates_dir, sample_data_dir, data_out_dir = (
    Path("data/templates"),
    Path("data/sample"),
    Path("data/out"),
)
mkdir(data_out_dir)

ccda_templates_dir = templates_dir.joinpath("ccda")
ccda_sample_dir = sample_data_dir.joinpath("ccda")
ccda_data_out_dir = data_out_dir.joinpath("ccda")
mkdir(ccda_data_out_dir)

stu3_sample_dir = sample_data_dir.joinpath("stu3")
stu3_data_out_dir = data_out_dir.joinpath("stu3")
mkdir(stu3_data_out_dir)

renderer: BaseFhirRenderer = CcdaRenderer()

print("Render the ccda file to string using the rendering defaults")
from_file = ccda_sample_dir.joinpath("CCD.ccda")
with from_file.open() as xml_in:
    print(renderer.render_fhir_string("CCD", xml_in))


# Static / Dictonary loader
static_templates = {
    "RESULTS": """{
    "resourceType": "Bundle",
    "type": "batch",
    "entry": [ {% include 'Section/Result' %} ]
}"""
}
renderer = CcdaRenderer(
    env=make_environment(
        loader=DictLoader(templates=static_templates),
        additional_loaders=[ccda_default_loader],
    )
)

print("\nRender the results section with no patient / header information")
with from_file.open() as xml_in:
    print(renderer.render_fhir_string("RESULTS", xml_in))


# Create a renderer that will load the user defined templates into the rendering env
renderer = CcdaRenderer(
    env=make_environment(
        loader=FileExtensionLoader(search_path=ccda_templates_dir),
        additional_loaders=[ccda_default_loader],
    )
)

print("\nRender the ccda file to the output directory using the CCD template")
render_to_dir(
    render=partial(renderer.render_fhir, "CCD"),
    from_file=from_file,
    to_dir=ccda_data_out_dir,
)

print("\nRender all sample ccda files to the output directory using the Pampi template")
render_files_to_dir(
    render=partial(renderer.render_fhir, "Pampi"),
    from_dir=ccda_sample_dir,
    to_dir=ccda_data_out_dir,
    path_filter=lambda p: p.suffix in (".ccda", ".xml"),
)


renderer = Stu3FhirRenderer()

print("\nRender the stu3 file to string")
from_file = stu3_sample_dir.joinpath("Patient.json")
with from_file.open() as fhir_in:
    print(renderer.render_fhir_string("Patient", fhir_in))

print("\nRender the stu3 files to the output directory")
render_to_dir(
    render=partial(renderer.render_fhir, "Patient"),
    from_file=from_file,
    to_dir=stu3_data_out_dir,
)

from_file = stu3_sample_dir.joinpath("AllergyIntolerance.json")
render_to_dir(
    render=partial(renderer.render_fhir, "AllergyIntolerance"),
    from_file=from_file,
    to_dir=stu3_data_out_dir,
)
