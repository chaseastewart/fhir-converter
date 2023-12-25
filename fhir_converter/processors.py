from abc import ABC
from json import dumps as json_dumps
from typing import IO, Callable, Optional, Type, Union

from frozendict import frozendict
from liquid import Environment
from pyjson5 import loads as json5_loads

from fhir_converter import filters, parsers, tags, templates

DATAT = Union[str, IO]


class BaseProcessor(ABC):
    """Base processor from which all processors are derived.

    Args:
        template_dir: The path containing the templates to use.

    Attributes:
        env (Environment): The rendering `Environment`
    """

    def __init__(self, template_dir: str) -> None:
        self.env = Environment(
            loader=templates.TemplateLoader(template_dir, auto_reload=False)
        )
        self.register_filters(filters.__filters__)
        self.register_tags(tags.__tags__)

    def register_filters(self, filters: list[tuple[str, Callable]]) -> None:
        """Register 1:* filter function(s) with the processor.

        Args:
            filters: The function(s) to register.
        """
        for filter in filters:
            self.env.add_filter(*filter)

    def register_tags(self, tags: list[Type]) -> None:
        """Register 1:* liquid tag(s) with the processor.

        Args:
            tags: The tag(s) to register.
        """
        for tag in tags:
            self.env.add_tag(tag)

    def convert(
        self, template_name: str, input: DATAT, encoding: Optional[str] = None
    ) -> str:
        """Converts the input data using the supplied rendering template

        Args:
            template_name: The rendering template name
            input: The input data. Either a string or File-like object
            encoding: The encoding for the data. Optional
        """
        raise NotImplementedError("processors must implement a convert method")


class CcdaProcessor(BaseProcessor):
    """Converts consolidated CDA documents to FHIR

    Args:
        template_dir: The path containing the templates to use.
        value_set_path: The path containing the valueset mappings.
    """

    def __init__(self, template_dir: str, value_set_path: Optional[str] = None) -> None:
        super().__init__(template_dir)
        self.value_sets = frozendict(
            json5_loads(
                templates.get_template_resource(
                    self.env,
                    value_set_path if value_set_path else "ValueSet/ValueSet.json",
                )
            ).get("Mapping", {})
        )

    def convert(
        self, template_name: str, xml_input: DATAT, encoding: Optional[str] = None
    ) -> str:
        """Convert the xml input to a FHIR string

        Args:
            template_name: The rendering template name
            xml_input: The xml input. Either a string or File-like object
            encoding: The xml encoding. Optional
        """
        return json_dumps(self.convert_to_dict(template_name, xml_input, encoding))

    def convert_to_dict(
        self, template_name: str, xml_input: DATAT, encoding: Optional[str] = None
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
