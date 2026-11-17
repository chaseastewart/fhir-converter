"""FastAPI application for converting CCDA and STU3 data into FHIR R4.

Endpoints:
    GET  /health                              Liveness check
    GET  /templates/{source}                  List templates for "ccda" or "stu3"
    POST /convert/ccda/{template}             Raw CCDA XML in the request body
    POST /convert/stu3                        Raw STU3 JSON in the request body
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from liquid.exceptions import TemplateNotFound

import fhir_converter
from fhir_converter.exceptions import RenderingError
from fhir_converter.renderers import CcdaRenderer, Stu3FhirRenderer

TEMPLATES_DIR = Path(fhir_converter.__file__).parent / "templates"
FHIR_JSON = "application/fhir+json"

API_KEY = 'testapikey1'

app = FastAPI(
    title="FHIR Converter API",
    description="Convert CCDA (XML) and FHIR STU3 (JSON) payloads into FHIR R4.",
    version=fhir_converter.__version__ if hasattr(fhir_converter, "__version__") else "0.3.0",
)


# --------------------------------------------------------------------------- #
# Renderers and template discovery
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def ccda_renderer() -> CcdaRenderer:
    return CcdaRenderer()


@lru_cache(maxsize=1)
def stu3_renderer() -> Stu3FhirRenderer:
    return Stu3FhirRenderer()


@lru_cache(maxsize=None)
def list_templates(source: str) -> List[str]:
    """Top-level (root) templates available for a source format."""
    return sorted(p.stem for p in (TEMPLATES_DIR / source).glob("*.liquid"))


def _require_template(source: str, template: str) -> None:
    if template not in list_templates(source):
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"Unknown {source} template '{template}'",
                "available": list_templates(source),
            },
        )


def _render(renderer, template: str, data: bytes) -> JSONResponse:
    if not data or not data.strip():
        raise HTTPException(status_code=400, detail="Request body is empty")
    try:
        output = renderer.render_fhir_string(template, data.decode("utf-8-sig"))
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Payload must be UTF-8 encoded")
    except TemplateNotFound as exc:
        raise HTTPException(status_code=404, detail=f"Template not found: {exc}")
    except RenderingError as exc:
        raise HTTPException(status_code=422, detail=f"Conversion failed: {exc}")
    return JSONResponse(content=json.loads(output), media_type=FHIR_JSON)


async def _convert(renderer, template: str, data: bytes) -> JSONResponse:
    # Rendering is CPU bound; keep it off the event loop.
    return await run_in_threadpool(_render, renderer, template, data)


def _stu3_template_from(data: bytes, template: Optional[str]) -> str:
    """Use the explicit template, else infer it from the STU3 resourceType."""
    if template:
        return template
    try:
        resource_type = json.loads(data.decode("utf-8-sig")).get("resourceType")
    except (ValueError, UnicodeDecodeError, AttributeError):
        raise HTTPException(status_code=400, detail="Body is not a valid JSON object")
    if not resource_type:
        raise HTTPException(
            status_code=400,
            detail="No 'template' query parameter and no 'resourceType' in payload",
        )
    return resource_type


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.get("/health", tags=["meta"])
def health() -> Dict[str, str]:
    return {"status": "Hey, I'm from fhir-converter. I'm healthy and ready to serve you !"}


@app.get("/templates/{source}", tags=["meta"])
def templates(source: Literal["ccda", "stu3"]) -> Dict[str, Any]:
    return {"source": source, "templates": list_templates(source)}



_XML_BODY = {
    "requestBody": {
        "required": True,
        "content": {"application/xml": {"schema": {"type": "string"}}},
    }
}

_JSON_BODY = {
    "requestBody": {
        "required": True,
        "content": {"application/json": {"schema": {"type": "object"}}},
    }
}


@app.post("/convert/ccda/{template}", tags=["ccda"], openapi_extra=_XML_BODY)
async def convert_ccda(template: str, request: Request) -> JSONResponse:
    """Convert a CCDA document (raw XML body) using a template such as CCD."""
    _require_template("ccda", template)
    return await _convert(ccda_renderer(), template, await request.body())



@app.post("/convert/stu3", tags=["stu3"], openapi_extra=_JSON_BODY)
async def convert_stu3(
    request: Request,
    template: Optional[str] = Query(None, description="Defaults to the payload resourceType"),
) -> JSONResponse:
    """Convert an STU3 resource (raw JSON body) to R4."""
    data = await request.body()
    name = _stu3_template_from(data, template)
    _require_template("stu3", name)
    return await _convert(stu3_renderer(), name, data)
