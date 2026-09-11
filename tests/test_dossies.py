import json
import unittest
import dossies
class TestDossies(unittest.TestCase):
    def test_dispatcher_roteia_por_tipo(self):
        for tipo in ("obra", "manutencao", "pagamento"):
            with self.subTest(tipo=tipo):
                msg = dossies.build_dossie_message(tipo, {}, "U1", "REG-1")
                self.assertIn("blocks", msg)
                self.assertIn("text", msg)
    def test_tipo_invalido_levanta_erro(self):
        with self.assertRaises(ValueError):
            dossies.build_dossie_message("invalido", {}, "U1", "REG-1")
    def test_obra_contem_dados_e_quatro_botoes(self):
        valores = {
            "nome_obra": "Shopping Rio Preto",
            "endereco": "Av. das Nações, 1200",
            "razao_social_cnpj": "12.345.678/0001-90",
            "escopo_tecnico": ["vrf", "dutos"],
            "engenheiro_responsavel": "U_ENG",
            "prazo_execucao": "2026-12-15",
        }
        msg = dossies.build_dossie_message("obra", valores, "U_AUTOR", "OBR-2026-0091")
        texto_completo = json.dumps(msg, ensure_ascii=False)
        self.assertIn("Shopping Rio Preto", texto_completo)
        self.assertIn("U_ENG", texto_completo)
        self.assertIn("Instalação VRF", texto_completo)
        self.assertIn("Dutos", texto_completo)
        bloco_acoes = _bloco_por_tipo(msg["blocks"], "actions")
        action_ids = [el["action_id"] for el in bloco_acoes["elements"]]
        self.assertEqual(action_ids, ["approve_project", "register_payment", "generate_pdf", "archive_channel"])
    def test_manutencao_urgencia_alta_tem_alerta_no_header(self):
        msg = dossies.build_dossie_message("manutencao", {"urgencia": "alta", "cliente_local": "JBS"}, "U1", "MAN-1")
        header = _bloco_por_tipo(msg["blocks"], "header")
        self.assertIn("🚨", header["text"]["text"])
    def test_manutencao_urgencia_baixa_sem_alerta(self):
        msg = dossies.build_dossie_message("manutencao", {"urgencia": "baixa", "cliente_local": "JBS"}, "U1", "MAN-1")
        header = _bloco_por_tipo(msg["blocks"], "header")
        self.assertNotIn("🚨", header["text"]["text"])
    def test_pagamento_mostra_valor_e_vinculo(self):
        valores = {"fornecedor": "Climabras", "valor_pagamento": "12500.90", "vinculo_destino": "OBR-2026-0091"}
        msg = dossies.build_dossie_message("pagamento", valores, "U1", "PAG-1")
        texto_completo = json.dumps(msg, ensure_ascii=False)
        self.assertIn("Climabras", texto_completo)
        self.assertIn("12500.90", texto_completo)
        self.assertIn("OBR-2026-0091", texto_completo)
    def test_status_pendente_por_padrao(self):
        msg = dossies.build_dossie_message("obra", {}, "U1", "OBR-1")
        secao_campos = _bloco_por_tipo(msg["blocks"], "section", precisa_fields=True)
        campo_status = next(f for f in secao_campos["fields"] if f["text"].startswith("*Status:*"))
        self.assertIn("Pendente", campo_status["text"])
    def test_e_serializavel_em_json(self):
        for tipo in ("obra", "manutencao", "pagamento"):
            json.dumps(dossies.build_dossie_message(tipo, {}, "U1", "REG-1"))
class TestAtualizarStatus(unittest.TestCase):
    def test_atualiza_campo_status_preservando_o_resto(self):
        msg = dossies.build_dossie_message("obra", {"nome_obra": "Shopping X"}, "U1", "OBR-1")
        novos_blocks = dossies.atualizar_status(msg["blocks"], "aprovado", "U_DIR", "Aprovado")
        secao_campos = _bloco_por_tipo(novos_blocks, "section", precisa_fields=True)
        campo_status = next(f for f in secao_campos["fields"] if f["text"].startswith("*Status:*"))
        self.assertIn("Aprovado por <@U_DIR>", campo_status["text"])
        # Os demais campos permanecem intactos.
        campo_nome = next(f for f in secao_campos["fields"] if "Razão Social" not in f["text"])
        self.assertTrue(any("Shopping X" in json.dumps(novos_blocks) for _ in [0]))
    def test_nao_muta_a_lista_original(self):
        msg = dossies.build_dossie_message("obra", {}, "U1", "OBR-1")
        original_json = json.dumps(msg["blocks"])
        dossies.atualizar_status(msg["blocks"], "aprovado", "U_DIR", "Aprovado")
        self.assertEqual(json.dumps(msg["blocks"]), original_json)
def _bloco_por_tipo(blocks: list, tipo: str, precisa_fields: bool = False) -> dict:
    for bloco in blocks:
        if bloco.get("type") == tipo and (not precisa_fields or "fields" in bloco):
            return bloco
    raise AssertionError(f"Nenhum bloco do tipo {tipo!r} encontrado")
if __name__ == "__main__":
    unittest.main()
