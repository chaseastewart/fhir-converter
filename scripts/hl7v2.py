from pathlib import Path
from liquid import FileExtensionLoader
from fhir_converter.renderers import Hl7v2Renderer, make_environment, hl7v2_default_loader

templates_dir = Path("fhir_converter/templates/hl7v2")

with open("data/sample/hl7v2/ADT-A01-01.hl7",mode="r",encoding="utf-8") as hl7v2_in:
    # env=make_environment(
    #     loader=FileExtensionLoader(search_path=templates_dir),
    #     additional_loaders=[hl7v2_default_loader],
    # )
    print(Hl7v2Renderer().render_fhir_string("ADT_A01_test", hl7v2_in))