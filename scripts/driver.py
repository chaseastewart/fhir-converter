import os
import sys
import time
from typing import Any, Generator

sys.path.insert(0, os.getcwd())
from fhir_converter.processors import CcdaProcessor

TEMPLATES = (
    "CCD",
    "ConsultationNote",
    "DischargeSummary",
    "HistoryandPhysical",
    "OperativeNote",
    "ProcedureNote",
    "ProgressNote",
    "ReferralNote",
    "TransferSummary",
)

DATA_OUT_DIR, TEMPLATE_DIR, SAMPLE_DIR = (
    "data/out",
    "data/templates/ccda",
    "data/sample/ccda/",
)


def main() -> None:
    from cProfile import Profile
    from pstats import SortKey, Stats

    if not os.path.isdir(DATA_OUT_DIR):
        os.mkdir(DATA_OUT_DIR)
    for template in TEMPLATES:
        template_dir = os.path.join(DATA_OUT_DIR, template)
        if not os.path.isdir(template_dir):
            os.mkdir(template_dir)

    before = time.perf_counter_ns()
    with Profile() as pr:
        processor = CcdaProcessor.from_template_dir(TEMPLATE_DIR)
        for cda_path in walk_dir(SAMPLE_DIR):
            for template in TEMPLATES:
                convert_to_fhir(processor, template, cda_path)

        with open(os.path.join(DATA_OUT_DIR, "stats.log"), "w") as stats_log:
            Stats(pr, stream=stats_log).sort_stats(SortKey.CUMULATIVE).print_stats()
    print(
        f"Took {round((time.perf_counter_ns() - before) / 1000000000, ndigits=3)} seconds."
    )


def walk_dir(path: str) -> Generator[str, Any, None]:
    for root, _, filenames in os.walk(path):
        for filename in filenames:
            if os.path.splitext(filename)[1] in (".ccda", ".xml"):
                yield os.path.join(root, filename)


def convert_to_fhir(processor: CcdaProcessor, template_name: str, cda_path: str) -> None:
    with open(cda_path) as ccda_file:
        fhir_path = os.path.join(
            DATA_OUT_DIR,
            template_name,
            os.path.splitext(os.path.basename(cda_path))[0] + ".json",
        )
        with open(fhir_path, "w") as fhir_file:
            fhir_file.write(processor.convert(template_name, ccda_file))


if __name__ == "__main__":
    main()
