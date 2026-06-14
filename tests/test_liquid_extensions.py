"""
Tests pour l'extension FHIR compatible de liquid 2.0
Teste que la syntaxe MSH."7" fonctionne correctement.
"""

import pytest
from liquid import Environment
from fhir_converter.liquid_extensions import register_fhir_compatible_path, restore_original_path


class TestFhirCompatiblePath:
    """Tests pour la syntaxe des propriétés numériques avec guillemets"""
    
    def setup_method(self):
        """Setup pour chaque test"""
        self.env = Environment()
        register_fhir_compatible_path(self.env)
        
        # Données de test qui simulent les structures HL7
        self.test_data = {
            "MSH": {
                "7": "20231009123456",
                "10": "MSG001",
                "4": {
                    "1": "HOSPITAL",
                    "2": "DEPT", 
                    "3": "CODE"
                }
            },
            "firstSegments": {
                "MSH": {
                    "7": {"Value": "20231009123456"},
                    "10": {"Value": "MSG001"},
                    "4": {
                        "1": "HOSPITAL",
                        "2": "DEPT"
                    }
                }
            }
        }
    
    def teardown_method(self):
        """Cleanup après chaque test"""
        restore_original_path(self.env)
    
    def test_simple_quoted_access(self):
        """Test accès simple avec guillemets: MSH."7" """
        template = self.env.from_string('{{ MSH."7" }}')
        result = template.render(MSH=self.test_data["MSH"])
        assert result == "20231009123456"
    
    def test_chained_quoted_access(self):
        """Test accès chaîné avec guillemets: MSH."4"."1" """
        template = self.env.from_string('{{ MSH."4"."1" }}')
        result = template.render(MSH=self.test_data["MSH"])
        assert result == "HOSPITAL"
    
    def test_nested_path_with_quotes(self):
        """Test chemin imbriqué: firstSegments.MSH."7".Value"""
        template = self.env.from_string('{{ firstSegments.MSH."7".Value }}')
        result = template.render(**self.test_data)
        assert result == "20231009123456"
    
    def test_complex_nested_path(self):
        """Test chemin complexe: firstSegments.MSH."4"."1" """
        template = self.env.from_string('{{ firstSegments.MSH."4"."1" }}')
        result = template.render(**self.test_data)
        assert result == "HOSPITAL"
    
    def test_if_condition_with_quotes(self):
        """Test condition if avec guillemets"""
        template = self.env.from_string('{% if MSH."7" %}Found{% endif %}')
        result = template.render(MSH=self.test_data["MSH"])
        assert result == "Found"
    
    def test_complex_if_condition(self):
        """Test condition if complexe comme dans les templates HL7"""
        template_str = '''{% if firstSegments.MSH."4"."1" != "" and firstSegments.MSH."4"."1" != null %}{{ firstSegments.MSH."4"."1" }}{% endif %}'''
        template = self.env.from_string(template_str)
        result = template.render(**self.test_data)
        assert result == "HOSPITAL"
    
    def test_mixed_syntax_compatibility(self):
        """Test compatibilité avec syntax mixte: normale + guillemets"""
        template = self.env.from_string('{{ firstSegments.MSH."7".Value }}')
        result = template.render(**self.test_data)
        assert result == "20231009123456"
    
    def test_bracket_syntax_still_works(self):
        """Test que la syntaxe bracket continue à fonctionner"""
        template = self.env.from_string('{{ MSH["7"] }}')
        result = template.render(MSH=self.test_data["MSH"])
        assert result == "20231009123456"
    
    def test_normal_identifier_still_works(self):
        """Test que les identifiants normaux continuent à fonctionner"""
        template = self.env.from_string('{{ firstSegments.MSH }}')
        result = template.render(**self.test_data)
        assert result == str(self.test_data["firstSegments"]["MSH"])
    
    def test_undefined_property_with_quotes(self):
        """Test accès à une propriété inexistante avec guillemets"""
        template = self.env.from_string('{{ MSH."999" }}')
        result = template.render(MSH=self.test_data["MSH"])
        assert result == ""  # undefined returns empty string in liquid
    
    def test_filter_with_quoted_access(self):
        """Test utilisation avec des filtres"""
        # Simulons un filtre qui pourrait être utilisé dans les templates FHIR
        self.env.add_filter("format_as_date_time", lambda x: f"formatted_{x}")
        
        template = self.env.from_string('{{ MSH."7" | format_as_date_time }}')
        result = template.render(MSH=self.test_data["MSH"])
        assert result == "formatted_20231009123456"


def test_real_world_hl7_template():
    """Test avec un template réel similaire à ADT_A01.liquid"""
    env = Environment()
    register_fhir_compatible_path(env)
    
    try:
        # Template similaire à celui qui causait l'erreur
        template_str = '''{% if firstSegments.MSH."7" -%}
    "timestamp":"{{ firstSegments.MSH."7".Value }}",
{% endif -%}
"identifier": {
    "value":"{{ firstSegments.MSH."10".Value }}"
}'''
        
        template = env.from_string(template_str)
        
        data = {
            "firstSegments": {
                "MSH": {
                    "7": {"Value": "20231009123456"},
                    "10": {"Value": "MSG001"}
                }
            }
        }
        
        result = template.render(**data)
        
        # Vérifier que le résultat contient les bonnes valeurs
        assert "20231009123456" in result
        assert "MSG001" in result
        assert "timestamp" in result
        assert "identifier" in result
        
    finally:
        restore_original_path(env)


if __name__ == "__main__":
    # Test rapide
    test = TestFhirCompatiblePath()
    test.setup_method()
    
    try:
        test.test_simple_quoted_access()
        test.test_chained_quoted_access()
        test.test_nested_path_with_quotes()
        print("✅ Tous les tests passent!")
        
        # Test avec le template réel
        test_real_world_hl7_template()
        print("✅ Test template réel réussi!")
        
    except Exception as e:
        print(f"❌ Test échoué: {e}")
        import traceback
        traceback.print_exc()
    finally:
        test.teardown_method()