"""Tests pour les tags personnalisés FHIR Converter - Version Liquid 2.0"""

from typing import Optional
from fhir_converter.tags import EvaluateNode, MergeDiffNode, all_tags, register_tags
from unittest import TestCase

from liquid import BoundTemplate, DictLoader, Environment
from liquid.exceptions import LiquidSyntaxError, TemplateNotFoundError as TemplateNotFound
from liquid.loader import BaseLoader
from pytest import raises


def get_template(
    source: str,
    register: bool = True,
    loader: Optional[BaseLoader] = None,
) -> BoundTemplate:
    """Helper pour créer un template avec les tags personnalisés."""
    env = Environment(loader=loader)
    if register:
        register_tags(env, all_tags)
    return env.from_string(source)


class MergeDiffTest(TestCase):
    """Tests pour le tag mergeDiff"""
    
    missing_endmerge = "{% mergeDiff var -%}"
    missing_identifier = "{% mergeDiff -%}{% endmergeDiff -%}"
    block = "{% mergeDiff var -%}{{block}}{% endmergeDiff -%}"

    def test_unregistered(self) -> None:
        """Test que le tag n'est pas reconnu sans enregistrement"""
        with raises(LiquidSyntaxError, match="unexpected tag 'mergeDiff'"):
            get_template(source=self.block, register=False).render()

    def test_missing_endmerge(self) -> None:
        """Test qu'une erreur est levée si endmergeDiff est manquant"""
        with raises(LiquidSyntaxError, match="expected tag endmergeDiff"):
            get_template(source=self.missing_endmerge).render()

    def test_missing_identifier(self) -> None:
        """Test qu'une erreur est levée si l'identifiant est manquant"""
        with raises(LiquidSyntaxError, match="missing expression"):
            get_template(source=self.missing_identifier).render()

    def test_invalid_json(self) -> None:
        """Test que du JSON invalide dans le bloc est ignoré"""
        template = get_template(source=self.block)
        # Le JSON invalide doit être ignoré et retourner l'objet original
        result = template.render(var={"test": "ok"}, block="{test:ok}")
        self.assertEqual(result, '{"test":"ok"}')

    def test_empty(self) -> None:
        """Test avec un bloc vide"""
        template = get_template(source=self.block)
        self.assertEqual(template.render(var={"test": "ok"}, block=""), '{"test":"ok"}')

    def test_space(self) -> None:
        """Test avec un bloc contenant uniquement des espaces"""
        template = get_template(source=self.block)
        self.assertEqual(template.render(var={"test": "ok"}, block=" "), '{"test":"ok"}')

    def test_empty_quote(self) -> None:
        """Test avec un bloc contenant une chaîne vide"""
        template = get_template(source=self.block)
        self.assertEqual(template.render(var={"test": "ok"}, block='""'), '{"test":"ok"}')

    def test_str(self) -> None:
        """Test avec une chaîne dans le bloc (non-dict)"""
        template = get_template(source=self.block)
        self.assertEqual(
            template.render(var={"test": "ok"}, block='"failed"'),
            '{"test":"ok"}',
        )

    def test_variable_undefined(self) -> None:
        """Test avec une variable non définie"""
        template = get_template(source=self.block)
        self.assertEqual(template.render(block={"test": "ok"}), "{}")

    def test_variable_str(self) -> None:
        """Test avec une variable qui est une chaîne (non-dict)"""
        template = get_template(source=self.block)
        self.assertEqual(template.render(var="ok", block={"test": "ok"}), '"ok"')

    def test_add(self) -> None:
        """Test l'ajout d'une nouvelle propriété"""
        template = get_template(source=self.block)
        self.assertEqual(template.render(var={}, block={"test": "add"}), '{"test":"add"}')

    def test_update(self) -> None:
        """Test la mise à jour d'une propriété existante"""
        template = get_template(source=self.block)
        self.assertEqual(
            template.render(var={"test": "ok"}, block={"test": "update"}),
            '{"test":"update"}',
        )

    def test_remove(self) -> None:
        """Test la mise à une chaîne vide (équivalent à une suppression logique)"""
        template = get_template(source=self.block)
        self.assertEqual(
            template.render(var={"test": "ok"}, block={"test": ""}), 
            '{"test":""}'
        )

    def test_empty_dict(self) -> None:
        """Test avec un bloc contenant un dict vide"""
        template = get_template(source=self.block)
        self.assertEqual(template.render(var={"test": "ok"}, block={}), '{"test":"ok"}')

    def test_empty_dicts(self) -> None:
        """Test avec var et block tous deux vides"""
        template = get_template(source=self.block)
        self.assertEqual(template.render(var={}, block={}), "{}")

    def test_choice_update(self) -> None:
        """Test la mise à jour d'un champ FHIR choice type (ex: value[x])"""
        template = get_template(source=self.block)
        self.assertEqual(
            template.render(var={"test_first": "ok"}, block={"test[x]": "update"}),
            '{"test_first":"update"}',
        )

    def test_choice_update_first(self) -> None:
        """Test que seul le premier champ correspondant est mis à jour"""
        template = get_template(source=self.block)
        self.assertEqual(
            template.render(
                var={"test_first": "ok", "test_second": "failed"},
                block={"test[x]": "update"},
            ),
            '{"test_first":"update","test_second":"failed"}',
        )

    def test_choice_remove(self) -> None:
        """Test la suppression d'un champ choice type"""
        template = get_template(source=self.block)
        self.assertEqual(
            template.render(var={"test_first": "ok"}, block={"test[x]": ""}),
            '{"test_first":""}',
        )

    def test_choice_remove_first(self) -> None:
        """Test que seul le premier champ choice correspondant est supprimé"""
        template = get_template(source=self.block)
        self.assertEqual(
            template.render(
                var={"test_first": "ok", "test_second": "failed"}, 
                block={"test[x]": ""}
            ),
            '{"test_first":"","test_second":"failed"}',
        )

    def test_choice_remove_multiple(self) -> None:
        """Test la suppression de plusieurs champs choice types"""
        template = get_template(source=self.block)
        self.assertEqual(
            template.render(
                var={"test_first": "ok", "test_second": "failed"},
                block={"test_f[x]": "", "test_s[x]": ""},
            ),
            '{"test_first":"","test_second":""}',
        )

    def test_choice_ignore(self) -> None:
        """Test qu'un champ choice sans correspondance est ignoré"""
        template = get_template(source=self.block)
        self.assertEqual(
            template.render(var={"other": "unknown"}, block={"test[x]": "ok"}),
            '{"other":"unknown"}',
        )


class EvaluateTest(TestCase):
    """Tests pour le tag evaluate"""
    
    missing_keyword = "{% evaluate var 'nosuchthing' -%}"
    not_found = "{% evaluate var using 'nosuchthing' -%}"
    no_arg = "{% evaluate var using 'no_arg' -%}{{ var }}"
    single_arg = "{% evaluate var using 'single_arg' arg1: val -%}{{ var }}"
    missing_comma = "{% evaluate var using 'multi_arg' arg1: val1 arg2: val2 -%}"
    multi_arg = "{% evaluate var using 'multi_arg' arg1: val1, arg2: val2 -%}{{ var }}"
    hl7v2_arg = "{% evaluate var using 'hl7v2' arg1: val[\"10\"] -%}{{ var }}"

    loader = DictLoader(
        {
            "no_arg": "ok",
            "single_arg": "{{ arg1 }}",
            "multi_arg": "{{ arg1 }}, {{ arg2 }}",
            "hl7v2": "{{ arg1 }}"
        }
    )

    def test_unregistered(self) -> None:
        """Test que le tag n'est pas reconnu sans enregistrement"""
        with raises(LiquidSyntaxError):
            get_template(source=self.no_arg, register=False).render()

    def test_template_not_found(self) -> None:
        """Test qu'une erreur est levée si le template n'existe pas"""
        with raises(TemplateNotFound):
            get_template(source=self.not_found).render()

    def test_missing_keyword(self) -> None:
        """Test qu'une erreur est levée si le mot-clé 'using' est manquant"""
        with raises(LiquidSyntaxError):
            get_template(source=self.missing_keyword).render()

    def test_missing_comma(self) -> None:
        """Test le comportement avec une virgule manquante entre les arguments"""
        # En liquid 2.0, sans virgule, le parser arrête le parsing des arguments
        # et 'arg2' est ignoré. Le template se rend quand même mais arg2 n'est pas défini
        template = get_template(source=self.missing_comma, loader=self.loader)
        # Le rendu devrait produire "test, " (arg2 est undefined)
        result = template.render(val1="test", val2="ok")
        self.assertEqual(result, "")

    def test_no_arg(self) -> None:
        """Test evaluate sans arguments"""
        template = get_template(source=self.no_arg, loader=self.loader)
        self.assertEqual(template.render(), "ok")

    def test_single_arg(self) -> None:
        """Test evaluate avec un seul argument"""
        template = get_template(source=self.single_arg, loader=self.loader)
        self.assertEqual(template.render(val="test"), "test")

    def test_multiple_args(self) -> None:
        """Test evaluate avec plusieurs arguments"""
        template = get_template(source=self.multi_arg, loader=self.loader)
        self.assertEqual(template.render(val1="test", val2="ok"), "test, ok")

    def test_hl7v2_arg(self) -> None:
        """Test evaluate avec un argument HL7v2 contenant des guillemets"""
        template = get_template(source=self.hl7v2_arg, loader=self.loader)
        self.assertEqual(template.render(val={'10': 'test'}), "test")