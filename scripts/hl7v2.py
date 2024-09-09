from fhir_converter.renderers import Hl7v2Renderer

with open("data/sample/hl7v2/ORU-R01-01.hl7",mode="r",encoding="utf-8") as hl7v2_in:
    result = Hl7v2Renderer().render_fhir_string("ORU_R01", hl7v2_in)
    print(result)