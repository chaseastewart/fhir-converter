import sys
from pathlib import Path
from typing import Any, Dict, List

from liquid import FileExtensionLoader

from fhir_converter.parsers import parse_xml
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

disch_sum_cda = sample_data_dir.joinpath("Discharge_Summary.ccda")
hist_and_phys_cda = sample_data_dir.joinpath("History_and_Physical.ccda")
render_media_cda = sample_data_dir.joinpath("cda-ch-emed-2-7-MedicationCard.ccda")


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
    _mkdirs(data_builtin_dir, builtin_templates)
    _mkdirs(data_user_defined_dir, user_defined_templates)
    _mkdirs(data_all_dir, all_templates)

    before = perf_counter_ns()
    with Profile() as pr:
        renderer = CcdaRenderer()
        _render_samples(renderer, templates=builtin_templates, to_dir=data_builtin_dir)

        renderer = CcdaRenderer(
            env=make_environment(
                loader=FileExtensionLoader(search_path=templates_dir),
                additional_loaders=[ccda_default_loader],
            )
        )
        _render_samples(
            renderer, templates=user_defined_templates, to_dir=data_user_defined_dir
        )
        _render_samples(renderer, templates=all_templates, to_dir=data_all_dir)

        with open(data_out_dir.joinpath("stats.log"), "w") as stats_log:
            Stats(pr, stream=stats_log).sort_stats(SortKey.CUMULATIVE).print_stats()
    print(f"Took {(perf_counter_ns() - before) / 1000000000:.3f} seconds")


def _mkdirs(path: Path, dirnames: List[str], **kwargs) -> None:
    mkdir(path, **kwargs)
    for dirname in dirnames:
        mkdir(path.joinpath(dirname), **kwargs)


def _render_samples(
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
    _benchmark_cda_renderer(iterations)
    _benchmark_xml_parser(iterations)


def _benchmark_cda_renderer(iterations: int):
    _benchmark_render_cda(disch_sum_cda, iterations)
    _benchmark_render_cda(disch_sum_cda, iterations, render_narrative=True)
    _benchmark_render_cda(hist_and_phys_cda, iterations)
    _benchmark_render_cda(hist_and_phys_cda, iterations, render_narrative=True)
    _benchmark_render_cda(render_media_cda, iterations)
    _benchmark_render_cda(render_media_cda, iterations, render_narrative=True)


def _benchmark_render_cda(
    sample_ccda: Path, iterations: int, render_narrative: bool = False
) -> None:
    print(f"\nSample={sample_ccda}, render_narrative={render_narrative}")
    renderer = CcdaRenderer(
        env=make_environment(
            loader=FileExtensionLoader(search_path=templates_dir),
            additional_loaders=[ccda_default_loader],
        ),
        template_globals={"render_narrative": render_narrative},
    )
    for template_name in all_templates:
        _benchmark_function(
            template_name,
            "renderer.render_to_fhir(template_name, xml_in)",
            {
                **globals(),
                "renderer": renderer,
                "template_name": template_name,
                "xml_in": sample_ccda.read_bytes(),
            },
            iterations,
        )


def _benchmark_xml_parser(iterations: int) -> None:
    _benchmark_parse_xml(disch_sum_cda, iterations)
    _benchmark_parse_xml(hist_and_phys_cda, iterations)
    _benchmark_parse_xml(render_media_cda, iterations)


def _benchmark_parse_xml(sample_ccda: Path, iterations: int) -> None:
    print(f"\nSample={sample_ccda}")
    _benchmark_function(
        parse_xml.__name__,
        "parse_xml(xml_in)",
        {
            **globals(),
            "xml_in": sample_ccda.read_bytes(),
        },
        iterations,
    )


def _benchmark_function(
    what: str, stmt: str, globals: Dict[str, Any], iterations: int
) -> None:
    from statistics import mean
    from timeit import repeat

    times = repeat(stmt, globals=globals, number=1, repeat=iterations)
    print(
        f"{what: <18}\tmax={max(times):.3f}\tmin={min(times):.3f}\tavg={mean(times):.3f}"
    )


if __name__ == "__main__":
    main(sys.argv[1:])
