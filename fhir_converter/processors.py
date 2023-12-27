from __future__ import annotations

from abc import ABC
from json import dumps as json_dumps
from typing import IO, Optional, Type, TypeVar, Union

from frozendict import frozendict
from liquid import Environment
from pyjson5 import loads as json5_loads

from fhir_converter import filters, parsers, tags, templates

T = TypeVar("T", bound="BaseProcessor")
XMLT = Union[str, IO]


class BaseProcessor(ABC):
    """Base processor from which all processors are derived.

    Args:
        env (Environment): The rendering `Environment`
    """

    def __init__(self, env: Environment) -> None:
        self.env = env
        templates.register_filters(self.env, filters.__default__)
        templates.register_tags(self.env, tags.__default__)

    def convert(
        self, template_name: str, input: XMLT, encoding: Optional[str] = None
    ) -> str:
        """Converts the input data using the supplied rendering template

        Args:
            template_name: The rendering template name
            input: The input data. Either a string or File-like object
            encoding: The encoding for the data. Optional
        """
        raise NotImplementedError("processors must implement a convert method")

    @classmethod
    def from_template_dir(cls: Type[T], template_dir: str, *args, **kwargs) -> T:
        """Constructs a new processor initializing the rendering environment
           with the specified template directory

           See processors for specific initialization parameters

        Args:
            template_dir: The directory of the rendering liquid templates
        """
        return cls(
            Environment(
                loader=templates.TemplateLoader(template_dir, auto_reload=False)
            ),
            *args,
            *kwargs,
        )


class CcdaProcessor(BaseProcessor):
    """Converts consolidated CDA documents to FHIR

    Args:
        env (Environment): The rendering `Environment`
        value_set_path: The path containing the valueset mappings.
    """

    def __init__(self, env: Environment, value_set_path: Optional[str] = None) -> None:
        super().__init__(env)
        self.value_sets = frozendict(
            json5_loads(
                templates.get_template_resource(
                    self.env,
                    value_set_path if value_set_path else "ValueSet/ValueSet.json",
                )
            ).get("Mapping", {})
        )

    def convert(
        self, template_name: str, xml_input: XMLT, encoding: Optional[str] = None
    ) -> str:
        """Convert the xml input to a FHIR string

        Args:
            template_name: The rendering template name
            xml_input: The xml input. Either a string or File-like object
            encoding: The xml encoding. Optional
        """
        return json_dumps(self.convert_to_dict(template_name, xml_input, encoding))

    def convert_to_dict(
        self, template_name: str, xml_input: XMLT, encoding: Optional[str] = None
    ) -> dict:
        """Convert the xml input to a FHIR dict

        Args:
            template_name: The rendering template name
            xml_input: The xml input. Either a string or File-like object
            encoding: The xml encoding. Optional
        """
        template = self.env.get_template(
            template_name, globals={"code_mapping": self.value_sets}
        )
        return parsers.parse_json(
            template.render({"msg": parsers.parse_xml(xml_input, encoding)})
        )
