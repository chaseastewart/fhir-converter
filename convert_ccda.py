from fhir_converter.renderers import CcdaRenderer

input_file = "data/sample/ccda/CCD.ccda"

renderer = CcdaRenderer()

with open(input_file, "r", encoding="utf-8") as xml_in:

    fhir_output = renderer.render_fhir_string(
        "CCD",
        xml_in
    )

    print(fhir_output)

    with open("output.json", "w", encoding="utf-8") as output:
        output.write(fhir_output)