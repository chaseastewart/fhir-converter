import sys
from pathlib import Path
from typing import List

from liquid import FileExtensionLoader

from fhir_converter.renderers import (
    CcdaRenderer,
    ccda_default_loader,
    make_environment,
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


def main(argv: List[str]) -> None:
    from platform import python_version

    print(f"Python Version={python_version()}")
    if not argv:
        benchmark()
    elif "--profile" in argv:
        profile()
    else:
        print("usage: python benchmark.py [--profile]\n", file=sys.stderr)
        sys.exit(1)


def profile() -> None:
    from cProfile import Profile
    from pstats import SortKey, Stats
    from time import perf_counter_ns

    data_out_dir, data_builtin_dir, data_user_defined_dir, data_all_dir = (
        Path("data/out"),
        Path("data/out/builtin"),
        Path("data/out/user_defined"),
        Path("data/out/all"),
    )

    mkdir(data_out_dir)
    mkdirs(data_builtin_dir, builtin_templates)
    mkdirs(data_user_defined_dir, user_defined_templates)
    mkdirs(data_all_dir, all_templates)

    before = perf_counter_ns()
    with Profile() as pr:
        renderer = CcdaRenderer()
        render_samples(renderer, templates=builtin_templates, to_dir=data_builtin_dir)

        renderer = CcdaRenderer(
            env=make_environment(
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
    print(f"Took {(perf_counter_ns() - before) / 1000000000:.3f} seconds")


def mkdirs(path: Path, dirnames: List[str], **kwargs) -> None:
    mkdir(path, **kwargs)
    for dirname in dirnames:
        mkdir(path.joinpath(dirname), **kwargs)


def render_samples(
    renderer: CcdaRenderer, templates: List[str], to_dir: Path, **kwargs
) -> None:
    from functools import partial

    for template in templates:
        render_files_to_dir(
            render=partial(renderer.render_fhir, template, **kwargs),
            from_dir=sample_data_dir,
            to_dir=to_dir.joinpath(template),
            path_filter=lambda p: p.suffix in (".ccda", ".xml"),
        )


def benchmark(iterations: int = 20) -> None:
    print(f"Iterations={iterations}")
    benchmark_renderer(sample_data_dir.joinpath("Discharge_Summary.ccda"), iterations)
    benchmark_renderer(sample_data_dir.joinpath("History_and_Physical.ccda"), iterations)


def benchmark_renderer(sample_ccda: Path, iterations: int) -> None:
    print(f"\nSample={sample_ccda}")
    renderer = CcdaRenderer(
        env=make_environment(
            loader=FileExtensionLoader(search_path=templates_dir),
            additional_loaders=[ccda_default_loader],
        )
    )
    for template_name in all_templates:
        benchmark_render_to_fhir(renderer, sample_ccda, template_name, iterations)


def benchmark_render_to_fhir(
    renderer: CcdaRenderer, sample_ccda: Path, template_name: str, iterations: int
) -> None:
    from statistics import mean
    from timeit import repeat

    times = repeat(
        "render_to_fhir(renderer, sample_ccda, template_name)",
        globals={
            **globals(),
            "renderer": renderer,
            "sample_ccda": sample_ccda,
            "template_name": template_name,
        },
        number=1,
        repeat=iterations,
    )
    print(
        f"{template_name: <18}\tmax={max(times):.3f}\tmin={min(times):.3f}\tavg={mean(times):.3f}"
    )


def render_to_fhir(renderer: CcdaRenderer, sample_ccda: Path, template_name: str) -> None:
    with sample_ccda.open() as xml_in:
        renderer.render_to_fhir(template_name, xml_in)


if __name__ == "__main__":
    main(sys.argv[1:])
