import json
import unittest
import modais
class TestModaisEstrutura(unittest.TestCase):
    def test_modal_selecao_e_obra_por_padrao(self):
        view = modais.build_modal_selecao_tipo()
        self.assertEqual(json.loads(view["private_metadata"])["tipo"], "obra")
    def test_view_tem_campos_obrigatorios_do_slack(self):
        for tipo in ("obra", "manutencao", "pagamento"):
            with self.subTest(tipo=tipo):
                view = modais.build_modal_por_tipo(tipo)
                self.assertEqual(view["type"], "modal")
                self.assertEqual(view["callback_id"], "submit_registro_ventosul")
                self.assertIn("title", view)
                self.assertIn("submit", view)
                self.assertIn("close", view)
                self.assertIsInstance(view["blocks"], list)
                self.assertGreater(len(view["blocks"]), 0)
    def test_private_metadata_guarda_o_tipo_certo(self):
        for tipo in ("obra", "manutencao", "pagamento"):
            view = modais.build_modal_por_tipo(tipo)
            self.assertEqual(json.loads(view["private_metadata"])["tipo"], tipo)
    def test_tipo_invalido_levanta_erro(self):
        with self.assertRaises(ValueError):
            modais.build_modal_por_tipo("nao-existe")
    def test_campos_obra_presentes(self):
        view = modais.build_modal_por_tipo("obra")
        action_ids = _todos_action_ids(view)
        for esperado in (
            "nome_obra", "endereco", "razao_social_cnpj", "escopo_tecnico",
            "engenheiro_responsavel", "prazo_execucao",
        ):
            self.assertIn(esperado, action_ids)
    def test_campos_manutencao_presentes(self):
        view = modais.build_modal_por_tipo("manutencao")
        action_ids = _todos_action_ids(view)
        for esperado in ("cliente_local", "equipamento", "relato_defeito", "urgencia", "necessidade_pecas"):
            self.assertIn(esperado, action_ids)
    def test_campos_pagamento_presentes(self):
        view = modais.build_modal_por_tipo("pagamento")
        action_ids = _todos_action_ids(view)
        for esperado in (
            "fornecedor", "cnpj_cpf", "valor_pagamento", "vencimento",
            "vinculo_destino", "link_comprovante",
        ):
            self.assertIn(esperado, action_ids)
    def test_seletor_de_tipo_tem_dispatch_action(self):
        view = modais.build_modal_por_tipo("obra")
        bloco_tipo = next(b for b in view["blocks"] if b.get("block_id") == "b_tipo")
        self.assertTrue(bloco_tipo["dispatch_action"])
        self.assertEqual(bloco_tipo["element"]["action_id"], "select_tipo_registro")
    def test_view_e_serializavel_em_json(self):
        # Garante que não sobrou nenhum objeto não serializável (ex.: datetime) no payload.
        for tipo in ("obra", "manutencao", "pagamento"):
            json.dumps(modais.build_modal_por_tipo(tipo))
def _todos_action_ids(view: dict) -> set:
    ids = set()
    for bloco in view["blocks"]:
        elemento = bloco.get("element")
        if elemento and "action_id" in elemento:
            ids.add(elemento["action_id"])
    return ids
if __name__ == "__main__":
    unittest.main()
