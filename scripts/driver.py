import time
from functools import partial
from pathlib import Path

from fhir_converter import loaders, renderers

templates = (
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

data_out_dir, templates_dir, sample_data_dir = (
    Path("data/out"),
    Path("fhir_converter/templates/ccda"),
    Path("data/sample/ccda"),
)


def main() -> None:
    from cProfile import Profile
    from pstats import SortKey, Stats

    if not data_out_dir.is_dir():
        data_out_dir.mkdir()
    for template in templates:
        template_dir = data_out_dir.joinpath(template)
        if not template_dir.is_dir():
            template_dir.mkdir()

    before = time.perf_counter_ns()
    with Profile() as pr:
        render_samples(renderer=renderers.CcdaRenderer())
        render_samples(
            renderer=renderers.CcdaRenderer(
                env=renderers.get_environment(
                    loader=lambda: loaders.get_file_system_loader(
                        search_path=templates_dir
                    )
                )
            )
        )

        with open(data_out_dir.joinpath("stats.log"), "w") as stats_log:
            Stats(pr, stream=stats_log).sort_stats(SortKey.CUMULATIVE).print_stats()
    print(
        f"Took {round((time.perf_counter_ns() - before) / 1000000000, ndigits=3)} seconds."
    )


def render_samples(renderer: renderers.CcdaRenderer) -> None:
    for template in templates:
        renderers.render_files_to_dir(
            render=partial(renderer.render_to_json_string, template),
            from_dir=sample_data_dir,
            to_dir=data_out_dir.joinpath(template),
        )


if __name__ == "__main__":
    main()
