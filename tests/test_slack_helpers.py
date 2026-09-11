import unittest
from unittest.mock import MagicMock
import config
from servicos import slack_helpers
class TestSlugify(unittest.TestCase):
    def test_remove_acentos_e_espacos(self):
        self.assertEqual(slack_helpers.slugify("Shopping Rio Preto"), "shopping-rio-preto")
    def test_remove_caracteres_especiais(self):
        self.assertEqual(slack_helpers.slugify("Climabras & Cia. Ltda!"), "climabras-cia-ltda")
    def test_string_vazia_cai_no_default(self):
        self.assertEqual(slack_helpers.slugify(""), "sem-nome")
        self.assertEqual(slack_helpers.slugify(None), "sem-nome")
    def test_trunca_em_60_caracteres(self):
        texto = "a" * 200
        self.assertLessEqual(len(slack_helpers.slugify(texto)), 60)
    def test_acentos_e_cedilha(self):
        self.assertEqual(slack_helpers.slugify("Ampliação Climatização – São José"), "ampliacao-climatizacao-sao-jose")
class TestMontarNomeCanal(unittest.TestCase):
    def test_obra(self):
        nome = slack_helpers.montar_nome_canal("obra", {"nome_obra": "Shopping Rio Preto"})
        self.assertEqual(nome, "obra-shopping-rio-preto")
    def test_manutencao_inclui_data(self):
        nome = slack_helpers.montar_nome_canal("manutencao", {"cliente_local": "JBS"})
        self.assertTrue(nome.startswith("manut-jbs-"))
        self.assertRegex(nome, r"^manut-jbs-\d{4}$")
    def test_pagamento_inclui_data(self):
        nome = slack_helpers.montar_nome_canal("pagamento", {"fornecedor": "Climabras"})
        self.assertRegex(nome, r"^pag-climabras-\d{4}$")
    def test_tipo_invalido_levanta_erro(self):
        with self.assertRaises(ValueError):
            slack_helpers.montar_nome_canal("inexistente", {})
    def test_nome_de_canal_nunca_excede_80_chars(self):
        nome = slack_helpers.montar_nome_canal("obra", {"nome_obra": "x" * 300})
        self.assertLessEqual(len(nome), 80)
class TestGerarRegistroId(unittest.TestCase):
    def test_formato_e_prefixo_por_tipo(self):
        self.assertRegex(slack_helpers.gerar_registro_id("obra", ano=2026), r"^OBR-2026-\d{4}$")
        self.assertRegex(slack_helpers.gerar_registro_id("manutencao", ano=2026), r"^MAN-2026-\d{4}$")
        self.assertRegex(slack_helpers.gerar_registro_id("pagamento", ano=2026), r"^PAG-2026-\d{4}$")
    def test_ids_sao_unicos_e_sequenciais(self):
        primeiro = slack_helpers.gerar_registro_id("obra", ano=2026)
        segundo = slack_helpers.gerar_registro_id("obra", ano=2026)
        self.assertNotEqual(primeiro, segundo)
class TestCriarCanal(unittest.TestCase):
    def test_chama_conversations_create_com_nome_e_privacidade(self):
        client = MagicMock()
        client.conversations_create.return_value = {"channel": {"id": "C999"}}
        canal_id = slack_helpers.criar_canal(client, "obra-teste")
        client.conversations_create.assert_called_once_with(name="obra-teste", is_private=True)
        self.assertEqual(canal_id, "C999")
class TestResolverStakeholders(unittest.TestCase):
    def setUp(self):
        config.GRUPOS = {
            "obra": ["S_ENG"],
            "manutencao": ["S_CAMPO"],
            "manutencao_urgente": ["S_CAMPO", "S_DIR"],
            "pagamento": ["S_DIR", "S_FIN"],
        }
    def test_obra_inclui_grupo_e_engenheiro_responsavel(self):
        client = MagicMock()
        client.usergroups_users_list.return_value = {"users": ["U_ENG1", "U_ENG2"]}
        membros = slack_helpers.resolver_stakeholders(client, "obra", {"engenheiro_responsavel": "U_JOAO"})
        self.assertEqual(set(membros), {"U_ENG1", "U_ENG2", "U_JOAO"})
        client.usergroups_users_list.assert_called_once_with(usergroup="S_ENG")
    def test_manutencao_urgencia_alta_adiciona_diretoria(self):
        client = MagicMock()
        client.usergroups_users_list.side_effect = [
            {"users": ["U_CAMPO1"]},
            {"users": ["U_DIR1"]},
        ]
        membros = slack_helpers.resolver_stakeholders(client, "manutencao", {"urgencia": "alta"})
        self.assertEqual(set(membros), {"U_CAMPO1", "U_DIR1"})
        self.assertEqual(client.usergroups_users_list.call_count, 2)
    def test_manutencao_urgencia_baixa_nao_chama_diretoria(self):
        client = MagicMock()
        client.usergroups_users_list.return_value = {"users": ["U_CAMPO1"]}
        membros = slack_helpers.resolver_stakeholders(client, "manutencao", {"urgencia": "baixa"})
        self.assertEqual(membros, ["U_CAMPO1"])
        client.usergroups_users_list.assert_called_once_with(usergroup="S_CAMPO")
    def test_pagamento_junta_diretoria_e_financeiro(self):
        client = MagicMock()
        client.usergroups_users_list.side_effect = [{"users": ["U_DIR"]}, {"users": ["U_FIN"]}]
        membros = slack_helpers.resolver_stakeholders(client, "pagamento", {})
        self.assertEqual(set(membros), {"U_DIR", "U_FIN"})
class TestConvidarMembros(unittest.TestCase):
    def test_nao_chama_api_se_lista_vazia(self):
        client = MagicMock()
        slack_helpers.convidar_membros(client, "C1", [])
        client.conversations_invite.assert_not_called()
    def test_junta_ids_unicos_em_csv(self):
        client = MagicMock()
        slack_helpers.convidar_membros(client, "C1", ["U1", "U2", "U1"])
        client.conversations_invite.assert_called_once_with(channel="C1", users="U1,U2")
class TestUsuarioPertenceAGrupo(unittest.TestCase):
    def test_true_quando_usuario_esta_na_lista(self):
        client = MagicMock()
        client.usergroups_users_list.return_value = {"users": ["U1", "U2"]}
        self.assertTrue(slack_helpers.usuario_pertence_a_grupo(client, "U1", "S_DIR"))
    def test_false_quando_nao_esta(self):
        client = MagicMock()
        client.usergroups_users_list.return_value = {"users": ["U2"]}
        self.assertFalse(slack_helpers.usuario_pertence_a_grupo(client, "U1", "S_DIR"))
    def test_false_quando_grupo_nao_configurado(self):
        client = MagicMock()
        self.assertFalse(slack_helpers.usuario_pertence_a_grupo(client, "U1", ""))
        client.usergroups_users_list.assert_not_called()
class TestExtrairValores(unittest.TestCase):
    def test_todos_os_tipos_de_elemento(self):
        state_values = {
            "b_nome_obra": {"nome_obra": {"type": "plain_text_input", "value": "Shopping Rio Preto"}},
            "b_escopo": {
                "escopo_tecnico": {
                    "type": "multi_static_select",
                    "selected_options": [{"value": "vrf"}, {"value": "dutos"}],
                }
            },
            "b_urgencia": {"urgencia": {"type": "radio_buttons", "selected_option": {"value": "alta"}}},
            "b_prazo": {"prazo_execucao": {"type": "datepicker", "selected_date": "2026-12-15"}},
            "b_engenheiro": {"engenheiro_responsavel": {"type": "users_select", "selected_user": "U_ENG"}},
        }
        valores = slack_helpers.extrair_valores(state_values)
        self.assertEqual(valores["nome_obra"], "Shopping Rio Preto")
        self.assertEqual(valores["escopo_tecnico"], ["vrf", "dutos"])
        self.assertEqual(valores["urgencia"], "alta")
        self.assertEqual(valores["prazo_execucao"], "2026-12-15")
        self.assertEqual(valores["engenheiro_responsavel"], "U_ENG")
    def test_campo_opcional_vazio_nao_quebra(self):
        state_values = {"b_pecas": {"necessidade_pecas": {"type": "plain_text_input", "value": None}}}
        valores = slack_helpers.extrair_valores(state_values)
        self.assertIsNone(valores["necessidade_pecas"])
class TestValidarValoresObrigatorios(unittest.TestCase):
    def test_pagamento_valor_valido(self):
        self.assertEqual(slack_helpers.validar_valores_obrigatorios("pagamento", {"valor_pagamento": "1234.56"}), [])
    def test_pagamento_valor_com_virgula_decimal_br(self):
        self.assertEqual(slack_helpers.validar_valores_obrigatorios("pagamento", {"valor_pagamento": "1234,56"}), [])
    def test_pagamento_valor_zero_ou_negativo(self):
        self.assertTrue(slack_helpers.validar_valores_obrigatorios("pagamento", {"valor_pagamento": "0"}))
        self.assertTrue(slack_helpers.validar_valores_obrigatorios("pagamento", {"valor_pagamento": "-5"}))
    def test_pagamento_valor_nao_numerico(self):
        self.assertTrue(slack_helpers.validar_valores_obrigatorios("pagamento", {"valor_pagamento": "abc"}))
    def test_obra_nao_tem_validacao_extra(self):
        self.assertEqual(slack_helpers.validar_valores_obrigatorios("obra", {}), [])
if __name__ == "__main__":
    unittest.main()
