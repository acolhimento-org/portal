"""Testes unitários do pipeline. Rode com: python -m unittest discover tests"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from connectors.cnes import classify, parse_hours, to_services as cnes_to_services  # noqa: E402
from connectors.na_bmlt import to_services as na_to_services  # noqa: E402
from normalize import slugify, to_uf  # noqa: E402


class TestNormalize(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(slugify("São Paulo"), "sao-paulo")
        self.assertEqual(slugify("Santa Bárbara d'Oeste"), "santa-barbara-d-oeste")

    def test_to_uf(self):
        self.assertEqual(to_uf(35), "SP")
        self.assertEqual(to_uf("35"), "SP")
        self.assertEqual(to_uf("sp"), "SP")
        self.assertEqual(to_uf("São Paulo"), "SP")
        self.assertIsNone(to_uf("Naoexiste"))


class TestCnesClassify(unittest.TestCase):
    def test_caps_ad(self):
        self.assertEqual(classify("CAPS AD II DE BREVES"), "caps_ad")
        self.assertEqual(classify("CENTRO DE ATENCAO PSICOSSOCIAL ALCOOL E DROGAS"), "caps_ad")

    def test_caps(self):
        self.assertEqual(classify("CAPS I DE VIGIA DE NAZARE"), "caps")
        self.assertEqual(classify("CENTRO DE ATENCAO PSICOSSOCIAL DA MARAMBAIA"), "caps")

    def test_outro(self):
        self.assertEqual(classify("RESIDENCIAL TERAPEUTICO"), "raps_outro")

    def test_ad_colado_ao_nivel(self):
        self.assertEqual(classify("CAPS ADII GUARUJA"), "caps_ad")
        self.assertEqual(classify("CAPS ADIII DE TUNTUM"), "caps_ad")
        self.assertEqual(classify("CAPS ADI CAVALEIRO"), "caps_ad")

    def test_ad_nao_confunde_com_palavra(self):
        # "AD" precisa ser palavra isolada, senão "CIDADE" viraria caps_ad
        self.assertEqual(classify("CAPS DA CIDADE ALTA"), "caps")


class TestCnesToServices(unittest.TestCase):
    def test_registro_basico(self):
        raw = [{
            "codigo_cnes": 123, "nome_fantasia": "CAPS AD TESTE",
            "codigo_uf": 35, "codigo_municipio": 355030,
            "endereco_estabelecimento": "RUA X", "numero_estabelecimento": "10",
            "bairro_estabelecimento": "CENTRO",
            "latitude_estabelecimento_decimo_grau": -23.5,
            "longitude_estabelecimento_decimo_grau": -46.6,
            "numero_telefone_estabelecimento": "11 99999999",
            "endereco_email_estabelecimento": "X@Y.COM",
        }]
        out = cnes_to_services(raw, {"355030": "São Paulo"})
        self.assertEqual(len(out), 1)
        s = out[0]
        self.assertEqual(s["id"], "cnes-123")
        self.assertEqual(s["kind"], "caps_ad")
        self.assertEqual(s["city_slug"], "sao-paulo")
        self.assertEqual(s["email"], "x@y.com")
        self.assertEqual(s["phones"], ["11 99999999"])

    def test_sem_municipio_e_descartado(self):
        raw = [{"codigo_cnes": 1, "nome_fantasia": "CAPS", "codigo_uf": 35,
                "codigo_municipio": 999999}]
        self.assertEqual(cnes_to_services(raw, {}), [])


class TestNaToServices(unittest.TestCase):
    def test_agrega_reunioes_do_mesmo_grupo(self):
        meeting = {
            "meeting_name": "Grupo Esperança", "location_street": "Rua A, 1",
            "location_municipality": "Campinas", "location_province": "SP",
            "latitude": "-22.9", "longitude": "-47.06", "venue_type": "1",
        }
        raw = [
            {**meeting, "weekday_tinyint": "2", "start_time": "20:00:00"},
            {**meeting, "weekday_tinyint": "5", "start_time": "19:30:00"},
        ]
        out = na_to_services(raw)
        self.assertEqual(len(out), 1)
        self.assertEqual(len(out[0]["schedule"]), 2)
        slot = out[0]["schedule"][0]
        self.assertEqual((slot["weekday"], slot["time"]), ("Segunda", "20:00"))
        self.assertFalse(out[0]["online"])

    def test_reuniao_virtual(self):
        raw = [{
            "meeting_name": "Grupo Online", "location_street": "",
            "location_municipality": "Rio de Janeiro", "location_province": "Rio de Janeiro",
            "latitude": None, "longitude": None, "venue_type": "2",
            "weekday_tinyint": "1", "start_time": "21:00:00",
            "virtual_meeting_link": "https://exemplo/reuniao",
        }]
        out = na_to_services(raw)
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0]["online"])
        self.assertEqual(out[0]["state"], "RJ")
        self.assertIn("https://exemplo/reuniao", out[0]["description"])


class TestParseHours(unittest.TestCase):
    def test_24h(self):
        rotulo, aberto = parse_hours(
            "ATENDIMENTO CONTINUO DE 24 HORAS/DIA (PLANTAO:INCLUI SABADOS, DOMINGOS E FERIADOS)")
        self.assertTrue(aberto)
        self.assertIn("24 horas", rotulo)

    def test_manha_tarde(self):
        rotulo, aberto = parse_hours("ATENDIMENTOS NOS TURNOS DA MANHA E A TARDE")
        self.assertEqual((rotulo, aberto), ("manhã e tarde", False))

    def test_desconhecido_vira_capitalizado(self):
        rotulo, aberto = parse_hours("HORARIO EXOTICO QUALQUER")
        self.assertEqual(aberto, False)
        self.assertEqual(rotulo, "Horario exotico qualquer")

    def test_vazio(self):
        self.assertEqual(parse_hours(None), (None, False))


class TestNaFormats(unittest.TestCase):
    def base(self, formats):
        return {
            "meeting_name": "Grupo X", "location_street": "Rua A, 1",
            "location_municipality": "Campinas", "location_province": "SP",
            "latitude": "-22.9", "longitude": "-47.06", "venue_type": "1",
            "weekday_tinyint": "2", "start_time": "20:00:00", "formats": formats,
        }

    def test_reuniao_aberta(self):
        out = na_to_services([self.base("A,TP")])
        self.assertTrue(out[0]["open_meeting"])
        self.assertTrue(out[0]["schedule"][0]["open"])

    def test_reuniao_fechada(self):
        out = na_to_services([self.base("F,TP,CAR,FuF,APC")])
        s = out[0]
        self.assertFalse(s["open_meeting"])
        self.assertFalse(s["schedule"][0]["open"])
        self.assertTrue(s["wheelchair"])
        self.assertTrue(s["holidays"])
        self.assertTrue(s["court_card"])

    def test_sem_formato_a_ou_f(self):
        out = na_to_services([self.base("TP")])
        self.assertIsNone(out[0]["open_meeting"])
        self.assertNotIn("open", out[0]["schedule"][0])

    def test_grupo_misto_conta_como_aberto(self):
        m1 = self.base("F")
        m2 = self.base("A")
        m2["weekday_tinyint"] = "5"
        out = na_to_services([m1, m2])
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0]["open_meeting"])

    def test_directions(self):
        m = self.base("A")
        m["location_text"] = "Atras do mercado central."
        m["location_info"] = "Entrada pela lateral"
        out = na_to_services([m])
        self.assertEqual(out[0]["directions"], "Atras do mercado central. Entrada pela lateral")


class TestCnesEnriquecimento(unittest.TestCase):
    def test_horario_e_registro(self):
        raw = [{
            "codigo_cnes": 9, "nome_fantasia": "CAPS AD III TESTE",
            "codigo_uf": 35, "codigo_municipio": 355030,
            "descricao_turno_atendimento":
                "ATENDIMENTO CONTINUO DE 24 HORAS/DIA (PLANTAO:INCLUI SABADOS, DOMINGOS E FERIADOS)",
            "data_atualizacao": "2026-01-15",
        }]
        out = cnes_to_services(raw, {"355030": "São Paulo"})
        s = out[0]
        self.assertTrue(s["open_24h"])
        self.assertIn("24 horas", s["hours"])
        self.assertEqual(s["registry_updated_at"], "2026-01-15")


if __name__ == "__main__":
    unittest.main()
