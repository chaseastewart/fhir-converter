from unittest import TestCase

from liquid import Environment

from fhir_converter import filters


class ToArrayFilterTestCase(TestCase):
    def setUp(self) -> None:
        env = Environment(strict_filters=True)
        filters.register(env, filters.all)

        self.template = env.from_string(
            """
            {% assign keys = el.key | to_array -%}
            {% for key in keys -%}{{key}},{% endfor -%}
            """.strip()
        )

    def test_list(self) -> None:
        result = self.template.render(el={"key": ["one", "two", "three"]})
        self.assertEqual(result, "one,two,three,")

        result = self.template.render(el={"key": ["one"]})
        self.assertEqual(result, "one,")

    def test_wrap(self) -> None:
        result = self.template.render(el={"key": "one"})
        self.assertEqual(result, "one,")

    def test_undefined(self) -> None:
        result = self.template.render()
        self.assertEqual(result, "")


class MatchFilterTestCase(TestCase):
    def setUp(self) -> None:
        self.env = Environment(strict_filters=True)
        filters.register(self.env, filters.all)

    def test_match(self) -> None:
        template = self.env.from_string("""{{code | match: "[0123456789.]+" | size}}""")
        result = template.render(code="2.16.840.1.113883.6.1")
        self.assertEqual(result, "1")

        template = self.env.from_string("""{{code | match: "[0123456789.]+"}}""")
        result = template.render(code="2.16.840.1.113883.6.1")
        self.assertEqual(result, "2.16.840.1.113883.6.1")

    def test_does_not_match(self) -> None:
        template = self.env.from_string("""{{code | match: "[0123456789.]+" | size}}""")
        result = template.render(code="a")
        self.assertEqual(result, "0")

    def test_empty_string(self) -> None:
        template = self.env.from_string("""{{code | match: "[0123456789.]+" | size}}""")
        result = template.render(code="")
        self.assertEqual(result, "0")

    def test_undefined(self) -> None:
        template = self.env.from_string("""{{code | match: "[0123456789.]+" | size}}""")
        result = template.render()
        self.assertEqual(result, "0")
