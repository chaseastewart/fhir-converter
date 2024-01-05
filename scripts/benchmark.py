import time
from collections.abc import Sequence
from functools import partial
from pathlib import Path

from fhir_converter import loaders, renderers, utils

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
all_templates = builtin_templates + user_defined_templates

templates_dir, sample_data_dir = (
    Path("data/templates/ccda"),
    Path("data/sample/ccda"),
)

data_out_dir, data_builtin_dir, data_user_defined_dir, data_all_dir = (
    Path("data/out"),
    Path("data/out/builtin"),
    Path("data/out/user_defined"),
    Path("data/out/all"),
)


def main() -> None:
    from cProfile import Profile
    from pstats import SortKey, Stats

    utils.mkdir_if_not_exists(data_out_dir)
    mkdirs_if_not_exists(data_builtin_dir, builtin_templates)
    mkdirs_if_not_exists(data_user_defined_dir, user_defined_templates)
    mkdirs_if_not_exists(data_all_dir, all_templates)

    before = time.perf_counter_ns()
    with Profile() as pr:
        renderer = renderers.CcdaRenderer()
        render_samples(renderer, templates=builtin_templates, to_dir=data_builtin_dir)

        renderer = renderers.CcdaRenderer(
            renderers.get_environment(
                loader=loaders.get_file_system_loader(search_path=templates_dir)
            )
        )
        render_samples(
            renderer,
            templates=user_defined_templates,
            to_dir=data_user_defined_dir,
        )
        render_samples(renderer, templates=all_templates, to_dir=data_all_dir, indent=2)

        with open(data_out_dir.joinpath("stats.log"), "w") as stats_log:
            Stats(pr, stream=stats_log).sort_stats(SortKey.CUMULATIVE).print_stats()
    print(
        f"Took {round((time.perf_counter_ns() - before) / 1000000000, ndigits=3)} seconds"
    )


def mkdirs_if_not_exists(root: Path, dirnames: Sequence[str]) -> None:
    utils.mkdir_if_not_exists(root)
    for dirname in dirnames:
        utils.mkdir_if_not_exists(root.joinpath(dirname))


def render_samples(
    renderer: renderers.CcdaRenderer, templates: Sequence[str], to_dir: Path, **kwargs
) -> None:
    for template in templates:
        renderers.render_files_to_dir(
            render=partial(renderer.render_fhir, template, **kwargs),
            from_dir=sample_data_dir,
            to_dir=to_dir.joinpath(template),
            path_filter=lambda p: p.suffix in (".ccda", ".xml"),
        )


if __name__ == "__main__":
    main()
