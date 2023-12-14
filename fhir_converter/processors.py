from abc import ABC
from json import dumps as json_dumps
from typing import Optional

from frozendict import frozendict
from liquid import Environment
from pyjson5 import loads as json5_loads

from fhir_converter import parsers, templates


class BaseProcessor(ABC):
    """Base processor from which all processors are derived."""

    def __init__(self, template_dir: str) -> None:
        env = Environment(loader=templates.TemplateLoader(template_dir))
        templates.setup(env)

        self.env = env

    def convert(self, data: str) -> str:
        """Performs the data conversion

        Args:
            data: The data to convert
        """
        raise NotImplementedError("processors must implement a convert method")


class CcdaProcessor(BaseProcessor):
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

    def convert(self, template_name: str, xml_input: str) -> str:
        template = self.env.get_template(
            template_name, globals={"code_mapping": self.value_sets}
        )
        return json_dumps(
            parsers.parse_json(template.render({"msg": parsers.parse_xml(xml_input)}))
        )
