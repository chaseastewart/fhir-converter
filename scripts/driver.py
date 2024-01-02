import time
from collections.abc import Sequence
from functools import partial
from pathlib import Path

from fhir_converter import loaders, renderers

builtin_templates = (
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

user_defined_templates = ("LabsandVitals", "Pampi")

data_out_dir, templates_dir, sample_data_dir = (
    Path("data/out"),
    Path("data/templates/ccda"),
    Path("data/sample/ccda"),
)


def main() -> None:
    from cProfile import Profile
    from pstats import SortKey, Stats

    if not data_out_dir.is_dir():
        data_out_dir.mkdir()
    for template in builtin_templates + user_defined_templates:
        template_dir = data_out_dir.joinpath(template)
        if not template_dir.is_dir():
            template_dir.mkdir()

    before = time.perf_counter_ns()
    with Profile() as pr:
        # render_samples(renderer=renderers.CcdaRenderer(), templates=builtin_templates)
        render_samples(
            renderer=renderers.CcdaRenderer(
                env=renderers.get_environment(
                    loader=loaders.get_file_system_loader(search_path=templates_dir)
                )
            ),
            templates=builtin_templates + user_defined_templates,
        )

        with open(data_out_dir.joinpath("stats.log"), "w") as stats_log:
            Stats(pr, stream=stats_log).sort_stats(SortKey.CUMULATIVE).print_stats()
    print(
        f"Took {round((time.perf_counter_ns() - before) / 1000000000, ndigits=3)} seconds."
    )


def render_samples(renderer: renderers.CcdaRenderer, templates: Sequence[str]) -> None:
    for template in templates:
        renderers.render_files_to_dir(
            render=partial(renderer.render_to_json_string, template),
            from_dir=sample_data_dir,
            to_dir=data_out_dir.joinpath(template),
            filter_func=lambda p: p.suffix in (".ccda", ".xml"),
        )


if __name__ == "__main__":
    main()
