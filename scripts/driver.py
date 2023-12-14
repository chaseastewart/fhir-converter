import os
import sys

sys.path.insert(0, os.getcwd())
from fhir_converter import processors


def ccda_to_fhir(
    processor: processors.CcdaProcessor, template_name: str, filename: str
) -> None:
    with open(f"data/sample/ccda/{filename}.ccda") as ccda_file:
        with open(f"data/out/{filename}.json", "w") as fhir_file:
            fhir_file.write(
                processor.convert(
                    template_name=template_name,
                    xml_input=ccda_file.read(),
                )
            )


def main() -> None:
    from cProfile import Profile
    from pstats import SortKey, Stats

    if not os.path.isdir("data/out"):
        os.mkdir("data/out")

    with Profile() as pr:
        processor = processors.CcdaProcessor(template_dir="data/templates/ccda")
        ccda_to_fhir(processor, "CCD", "C-CDA_R2-1_CCD")
        ccda_to_fhir(processor, "ConsultationNote", "Consultation_Note")
        ccda_to_fhir(processor, "DischargeSummary", "Discharge_Summary")
        ccda_to_fhir(processor, "HistoryandPhysical", "History_and_Physical")
        ccda_to_fhir(processor, "OperativeNote", "Operative_Note")
        ccda_to_fhir(processor, "ProcedureNote", "Procedure_Note")
        ccda_to_fhir(processor, "ProgressNote", "Progress_Note")
        ccda_to_fhir(processor, "ReferralNote", "Referral_Note")
        ccda_to_fhir(processor, "TransferSummary", "Transfer_Summary")

        with open("data/out/stats.log", "w") as stats_log:
            Stats(pr, stream=stats_log).sort_stats(SortKey.CUMULATIVE).print_stats()


main()
