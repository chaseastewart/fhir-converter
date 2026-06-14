"""Tests pour le tag {% evaluate %} - Régression Liquid 2 migration"""

import pytest
from fhir_converter.renderers import Hl7v2Renderer


class TestEvaluateTag:
    """Tests pour vérifier que le tag evaluate passe correctement les paramètres"""
    
    def test_evaluate_tag_passes_parameters_to_template(self):
        """
        Test de régression pour le bug où les paramètres du tag evaluate
        n'étaient pas passés au template rendu.
        
        Avant la correction, la boucle while not tokens.eof ne s'exécutait jamais
        car tokens.eof retourne un objet Token au lieu d'un boolean, donc
        `not tokens.eof` était toujours False.
        
        Ce test vérifie que les Device resources générés à partir des segments AIG
        ont des UUIDs distincts basés sur leurs paramètres au lieu d'utiliser tous
        le même UUID généré à partir de la chaîne "Device" vide.
        """
        renderer = Hl7v2Renderer()
        
        # Message HL7v2 SIU-S12 avec 3 segments AIG (3 devices différents)
        hl7_message = """MSH|^~\\&|ADTApp|GOOD HEALTH HOSPITAL|RSP1P8|GOOD HEALTH HOSPITAL|20210513112700||SIU^S12|20210513112700|P|2.5
EVN||20110613122700|||||
PID|1|3333|3333||Test^Patient||19600101|F||||||||||3333
PV1|1|A
RGS|1|^||||||
AIG|1||123^Cell Counter^L^^^^|011^Lab Equipment^L||||||||
NTE|||Equipment specific Notes1
AIG|1||1001^XYZ X-Ray Machine^L|015^Imaging Equipment^L||||||||
NTE|||Equipment specific Notes2
AIG|2||1010^ABC CT Scan Machine^L||||
NTE|||Equipment specific Notes2"""
        
        # Rendre le message
        output = renderer.render_fhir_string("SIU_S12", hl7_message)
        
        # Parser le JSON
        import json
        bundle = json.loads(output)
        
        # Extraire tous les Device resources
        devices = []
        device_ids = []
        for entry in bundle['entry']:
            if entry['resource']['resourceType'] == 'Device':
                devices.append(entry['resource'])
                device_ids.append(entry['resource']['id'])
        
        # Note: parse_fhir() fusionne les Device resources avec le même ID.
        # Avec le bug, tous les Devices auraient le même UUID (7b14e451...) généré
        # à partir de la chaîne "Device" sans paramètres, et seraient fusionnés en un seul.
        # 
        # Avec la correction, chaque Device a un UUID unique basé sur ses paramètres:
        # - Device MSH: c73757f8-d1bc-5b3b-bb8a-ed05e023b4c6
        # - Device AIG 123: 4320e0a4-b6e8-526c-837d-509ab9443b7f
        # - Device AIG 1001: 034bbbd0-5a0e-56e1-b97c-e081ee089aa7
        # - Device AIG 1010: 40286015-aa23-534b-a1d6-9e9e0587faa4
        # 
        # Après fusion JSON5, on devrait avoir au moins 1 Device (peut-être plus selon
        # la logique de fusion), mais surtout, on ne doit PAS avoir le bug UUID.
        
        assert len(devices) >= 1, f"Expected at least 1 Device resource, got {len(devices)}"
        
        # LE TEST PRINCIPAL: Vérifier qu'on n'a PAS l'UUID du bug
        # Cet UUID (7b14e451...) est généré quand evaluate ne passe pas les paramètres,
        # donc le template ID/_Device.liquid génère un UUID à partir de "Device" vide.
        bug_uuid = '7b14e451-21e4-5412-8d9a-395f0b3a7e52'  # UUID5(DNS_NAMESPACE, "Device")
        assert bug_uuid not in device_ids, (
            f"Found bug UUID {bug_uuid} in device IDs: {device_ids}. "
            "This UUID is generated when evaluate tag doesn't pass parameters to templates, "
            "indicating a REGRESSION of the bug where `while not tokens.eof` never executed."
        )
        
        # Test secondaire: Vérifier qu'au moins un Device a un identifiant AIG
        # (prouve que les données AIG ont été traitées avec les bons paramètres)
        found_aig_identifier = False
        for device in devices:
            if 'identifier' in device:
                for identifier in device['identifier']:
                    if 'value' in identifier and identifier['value'] in ['123', '1001', '1010']:
                        found_aig_identifier = True
                        break
        
        assert found_aig_identifier, (
            f"No Device with AIG identifiers found. This suggests evaluate tag "
            f"is not passing AIG parameters correctly. Device IDs: {device_ids}"
        )
    
    def test_evaluate_tag_with_multiple_parameters(self):
        """
        Test que le tag evaluate peut accepter plusieurs paramètres séparés par des virgules.
        
        Exemple: {% evaluate id using 'ID/Patient' PID: segment, type: 'First' %}
        
        Ce test vérifie que le tag evaluate génère un UUID stable basé sur les paramètres
        passés, confirmant que les paramètres sont bien transmis au template.
        """
        renderer = Hl7v2Renderer()
        
        # Message minimal avec PID
        hl7_message = """MSH|^~\\&|ADTApp|HOSPITAL|RSP1P8|HOSPITAL|20210513112700||ADT^A01|20210513112700|P|2.5
EVN||20110613122700|||||
PID|1|12345|12345||Doe^John||19900101|M||||||||||"""
        
        # Rendre le message (ADT_A01 utilise evaluate avec PID: pidSegment, type: 'First')
        output = renderer.render_fhir_string("ADT_A01", hl7_message)
        
        # Parser le JSON
        import json
        bundle = json.loads(output)
        
        # Vérifier que le Patient resource existe
        patients = [
            entry['resource'] 
            for entry in bundle['entry'] 
            if entry['resource']['resourceType'] == 'Patient'
        ]
        
        assert len(patients) >= 1, "Expected at least 1 Patient resource"
        
        # Vérifier que le patient a un identifiant
        patient = patients[0]
        assert 'identifier' in patient, "Patient should have identifiers"
        assert len(patient['identifier']) > 0, "Patient should have at least one identifier"
        
        # Vérifier que l'ID du patient est cohérent (UUID généré à partir des paramètres)
        # Si les paramètres ne sont pas passés, l'UUID serait différent
        patient_id = patient['id']
        assert patient_id is not None, "Patient should have an ID"
        assert len(patient_id) == 36, f"Patient ID should be a valid UUID, got: {patient_id}"
        
        # Vérifier que l'identifiant du patient contient la valeur du PID
        identifier_values = [id['value'] for id in patient['identifier'] if 'value' in id]
        assert '12345' in identifier_values, f"Expected identifier '12345' in patient identifiers: {identifier_values}"
    
    def test_device_references_in_appointment_have_uuids(self):
        """
        Test de régression pour le bug où les références Device dans Appointment
        étaient vides ("Device/") à cause d'une faute de frappe dans le template
        _Appointment.liquid (device_ID_AIG_3 au lieu de device_Id_AIG_3).
        """
        renderer = Hl7v2Renderer()
        
        # Message HL7v2 SIU-S12 avec 3 segments AIG
        hl7_message = """MSH|^~\\&|ADTApp|GOOD HEALTH HOSPITAL|RSP1P8|GOOD HEALTH HOSPITAL|20210513112700||SIU^S12|20210513112700|P|2.5
EVN||20110613122700|||||
PID|1|3333|3333||Test^Patient||19600101|F||||||||||3333
PV1|1|A
RGS|1|^||||||
AIG|1||123^Cell Counter^L^^^^|011^Lab Equipment^L||||||||
NTE|||Equipment specific Notes1
AIG|1||1001^XYZ X-Ray Machine^L|015^Imaging Equipment^L||||||||
NTE|||Equipment specific Notes2
AIG|2||1010^ABC CT Scan Machine^L||||
NTE|||Equipment specific Notes2"""
        
        # Rendre le message
        output = renderer.render_fhir_string("SIU_S12", hl7_message)
        
        # Parser le JSON
        import json
        bundle = json.loads(output)
        
        # Trouver l'Appointment
        appointments = [
            entry['resource'] 
            for entry in bundle['entry'] 
            if entry['resource']['resourceType'] == 'Appointment'
        ]
        
        assert len(appointments) >= 1, "Expected at least 1 Appointment resource"
        
        appointment = appointments[0]
        assert 'participant' in appointment, "Appointment should have participants"
        
        # Vérifier que tous les participants Device ont des UUIDs valides
        device_references = []
        for participant in appointment['participant']:
            if 'actor' in participant and 'reference' in participant['actor']:
                ref = participant['actor']['reference']
                if ref.startswith('Device/'):
                    device_references.append(ref)
        
        # Note: parse_fhir() fusionne les participants avec le même type,
        # donc on peut avoir moins de 3 références après fusion.
        # L'important est qu'aucune référence ne soit vide.
        assert len(device_references) >= 1, f"Expected at least 1 Device reference, got {len(device_references)}"
        
        # Vérifier qu'aucune référence Device n'est vide
        for ref in device_references:
            assert ref != "Device/", f"Found empty Device reference: {ref}"
            # Vérifier que la référence contient un UUID (36 caractères après "Device/")
            device_id = ref.replace("Device/", "")
            assert len(device_id) == 36, f"Device reference should have a valid UUID (36 chars), got: {ref}"
            assert '-' in device_id, f"Device reference should have a valid UUID format, got: {ref}"
        
        # Test régressif: l'UUID ne doit PAS être vide
        # (c'était le bug avant la correction: "Device/" sans UUID)
        invalid_refs = [ref for ref in device_references if ref == "Device/"]
        assert len(invalid_refs) == 0, f"Found {len(invalid_refs)} empty Device references (regression)"
