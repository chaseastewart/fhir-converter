import time
from functools import partial
from pathlib import Path

from liquid import FileExtensionLoader

from fhir_converter.renderers import (
    CcdaRenderer,
    ccda_default_loader,
    get_environment,
    render_files_to_dir,
)
from fhir_converter.utils import mkdir

builtin_templates = [
    "CCD",
    "ConsultationNote",
    "DischargeSummary",
    "HistoryandPhysical",
    "OperativeNote",
    "ProcedureNote",
    "ProgressNote",
    "ReferralNote",
    "TransferSummary",
]

user_defined_templates = ["LabsandVitals", "Pampi"]
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

    mkdir(data_out_dir)
    mkdirs(data_builtin_dir, builtin_templates)
    mkdirs(data_user_defined_dir, user_defined_templates)
    mkdirs(data_all_dir, all_templates)

    before = time.perf_counter_ns()
    with Profile() as pr:
        renderer = CcdaRenderer()
        render_samples(renderer, templates=builtin_templates, to_dir=data_builtin_dir)

        renderer = CcdaRenderer(
            env=get_environment(
                loader=FileExtensionLoader(search_path=templates_dir),
                additional_loaders=[ccda_default_loader],
            )
        )
        render_samples(
            renderer,
            templates=user_defined_templates,
            to_dir=data_user_defined_dir,
        )
        render_samples(renderer, templates=all_templates, to_dir=data_all_dir)

        with open(data_out_dir.joinpath("stats.log"), "w") as stats_log:
            Stats(pr, stream=stats_log).sort_stats(SortKey.CUMULATIVE).print_stats()
    print(
        f"Took {round((time.perf_counter_ns() - before) / 1000000000, ndigits=3)} seconds"
    )


def render_samples(
    renderer: CcdaRenderer, templates: list[str], to_dir: Path, **kwargs
) -> None:
    for template in templates:
        render_files_to_dir(
            render=partial(renderer.render_fhir, template, **kwargs),
            from_dir=sample_data_dir,
            to_dir=to_dir.joinpath(template),
            path_filter=lambda p: p.suffix in (".ccda", ".xml"),
        )


def mkdirs(path: Path, dirnames: list[str], **kwargs) -> None:
    mkdir(path, **kwargs)
    for dirname in dirnames:
        mkdir(path.joinpath(dirname), **kwargs)


if __name__ == "__main__":
    main()
