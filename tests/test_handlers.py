"""Testes de integração dos handlers (comando -> modal -> submit -> dossiê ->
botões), usando FakeBoltApp no lugar do slack_bolt real e um client mockado no
lugar da Web API do Slack. Cobrem o fluxo ponta a ponta descrito no pedido
original, sem precisar de nenhuma credencial ou rede."""
import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import requests
import config
from handlers import actions, commands, views
from servicos import armazenamento
from tests.fakes import FakeBoltApp, cliente_mock
class BaseHandlerTest(unittest.TestCase):
    def setUp(self):
        armazenamento.limpar_tudo()
        self._pasta_temp = tempfile.mkdtemp(prefix="ventosul-handlers-test-")
        self._pasta_original = config.ERP_XML_DROP_FOLDER
        config.ERP_XML_DROP_FOLDER = self._pasta_temp
        self._grupos_originais = dict(config.GRUPOS)
        config.GRUPOS = {
            "obra": ["S_ENG"], "manutencao": ["S_CAMPO"],
            "manutencao_urgente": ["S_CAMPO", "S_DIR"], "pagamento": ["S_DIR", "S_FIN"],
        }
        self._grupo_diretoria_original = config.GRUPO_DIRETORIA
        self._grupo_financeiro_original = config.GRUPO_FINANCEIRO
        config.GRUPO_DIRETORIA = "S_DIR"
        config.GRUPO_FINANCEIRO = "S_FIN"
        self.app = FakeBoltApp()
        commands.register(self.app)
        actions.register(self.app)
        views.register(self.app)
        self._patch_requests = patch(
            "servicos.erp.requests.post", side_effect=requests.exceptions.ConnectionError("sem rede nos testes")
        )
        self._patch_requests.start()
    def tearDown(self):
        self._patch_requests.stop()
        config.ERP_XML_DROP_FOLDER = self._pasta_original
        config.GRUPOS = self._grupos_originais
        config.GRUPO_DIRETORIA = self._grupo_diretoria_original
        config.GRUPO_FINANCEIRO = self._grupo_financeiro_original
        shutil.rmtree(self._pasta_temp, ignore_errors=True)
        armazenamento.limpar_tudo()
class TestComando(BaseHandlerTest):
    def test_slash_command_abre_modal(self):
        ack = MagicMock()
        client = cliente_mock()
        body = {"trigger_id": "T1", "user_id": "U1"}
        self.app.commands["/ventosul-os"](ack=ack, body=body, client=client)
        ack.assert_called_once()
        client.views_open.assert_called_once()
        view_enviada = client.views_open.call_args.kwargs["view"]
        self.assertEqual(view_enviada["callback_id"], "submit_registro_ventosul")
class TestSubmitObra(BaseHandlerTest):
    def _view_obra(self):
        return {
            "private_metadata": json.dumps({"tipo": "obra"}),
            "state": {
                "values": {
                    "b_nome_obra": {"nome_obra": {"type": "plain_text_input", "value": "Shopping Rio Preto"}},
                    "b_endereco": {"endereco": {"type": "plain_text_input", "value": "Av. das Nações, 1200"}},
                    "b_razao_social": {"razao_social_cnpj": {"type": "plain_text_input", "value": "12.345.678/0001-90"}},
                    "b_escopo": {"escopo_tecnico": {"type": "multi_static_select", "selected_options": [{"value": "vrf"}]}},
                    "b_engenheiro": {"engenheiro_responsavel": {"type": "users_select", "selected_user": "U_ENG"}},
                    "b_prazo": {"prazo_execucao": {"type": "datepicker", "selected_date": "2026-12-15"}},
                }
            },
        }
    def test_fluxo_completo_cria_canal_convida_e_posta_dossie(self):
        ack = MagicMock()
        client = cliente_mock()
        client.usergroups_users_list.return_value = {"users": ["U_ENG_GRUPO"]}
        body = {"user": {"id": "U_AUTOR"}}
        self.app.views["submit_registro_ventosul"](ack=ack, body=body, client=client, view=self._view_obra())
        ack.assert_called_once_with()  # sem response_action -> fecha o modal normalmente
        client.conversations_create.assert_called_once_with(name="obra-shopping-rio-preto", is_private=True)
        convidados = client.conversations_invite.call_args.kwargs["users"].split(",")
        self.assertIn("U_ENG_GRUPO", convidados)
        self.assertIn("U_ENG", convidados)  # engenheiro responsável do formulário
        self.assertIn("U_AUTOR", convidados)  # autor do cadastro
        client.chat_postMessage.assert_called_once()
        canal_destino = client.chat_postMessage.call_args.kwargs["channel"]
        self.assertEqual(canal_destino, "C123CANAL")
        registro = armazenamento.obter_registro_por_canal("C123CANAL")
        self.assertIsNotNone(registro)
        self.assertEqual(registro["tipo"], "obra")
        self.assertEqual(registro["status"], "pendente")
        self.assertEqual(registro["valores"]["nome_obra"], "Shopping Rio Preto")
    def test_erro_inesperado_notifica_autor_por_dm_em_vez_de_quebrar(self):
        ack = MagicMock()
        client = cliente_mock()
        client.conversations_create.side_effect = RuntimeError("Slack fora do ar")
        body = {"user": {"id": "U_AUTOR"}}
        self.app.views["submit_registro_ventosul"](ack=ack, body=body, client=client, view=self._view_obra())
        client.chat_postMessage.assert_called_once()
        self.assertEqual(client.chat_postMessage.call_args.kwargs["channel"], "U_AUTOR")
class TestSubmitPagamentoValidacao(BaseHandlerTest):
    def _view_pagamento(self, valor: str):
        return {
            "private_metadata": json.dumps({"tipo": "pagamento"}),
            "state": {
                "values": {
                    "b_fornecedor": {"fornecedor": {"type": "plain_text_input", "value": "Climabras"}},
                    "b_valor": {"valor_pagamento": {"type": "plain_text_input", "value": valor}},
                }
            },
        }
    def test_valor_invalido_reabre_modal_com_erro_sem_criar_canal(self):
        ack = MagicMock()
        client = cliente_mock()
        body = {"user": {"id": "U_AUTOR"}}
        self.app.views["submit_registro_ventosul"](ack=ack, body=body, client=client, view=self._view_pagamento("abc"))
        ack.assert_called_once()
        self.assertEqual(ack.call_args.kwargs.get("response_action"), "errors")
        client.conversations_create.assert_not_called()
    def test_valor_valido_segue_o_fluxo_normal(self):
        ack = MagicMock()
        client = cliente_mock()
        body = {"user": {"id": "U_AUTOR"}}
        self.app.views["submit_registro_ventosul"](ack=ack, body=body, client=client, view=self._view_pagamento("1500.00"))
        client.conversations_create.assert_called_once()
        self.assertNotIn("response_action", ack.call_args.kwargs if ack.call_args else {})
class TestSelecaoDeTipo(BaseHandlerTest):
    def test_troca_de_tipo_reconstroi_modal_via_views_update(self):
        ack = MagicMock()
        client = cliente_mock()
        body = {
            "actions": [{"selected_option": {"value": "manutencao"}}],
            "view": {"id": "V1", "hash": "abc123"},
        }
        self.app.actions["select_tipo_registro"](ack=ack, body=body, client=client)
        client.views_update.assert_called_once()
        nova_view = client.views_update.call_args.kwargs["view"]
        self.assertEqual(json.loads(nova_view["private_metadata"])["tipo"], "manutencao")
class TestBotoesDoDossie(BaseHandlerTest):
    def setUp(self):
        super().setUp()
        self.registro = armazenamento.salvar_registro(
            "OBR-2026-0001", tipo="obra", valores={"nome_obra": "Shopping X"},
            canal_id="C123CANAL", nome_canal="obra-shopping-x", autor_id="U_AUTOR",
        )
        armazenamento.definir_mensagem_ts("OBR-2026-0001", "1700000000.000100")
    def _body_botao(self, action_id: str, user_id: str):
        return {
            "actions": [{"value": "OBR-2026-0001"}],
            "user": {"id": user_id},
            "container": {"channel_id": "C123CANAL", "message_ts": "1700000000.000100"},
        }
    def test_aprovar_negado_para_quem_nao_e_diretoria(self):
        ack = MagicMock()
        client = cliente_mock()
        client.usergroups_users_list.return_value = {"users": []}  # ninguém é diretoria
        self.app.actions["approve_project"](ack=ack, body=self._body_botao("approve_project", "U_QUALQUER"), client=client)
        client.chat_postEphemeral.assert_called_once()
        client.chat_update.assert_not_called()
        self.assertEqual(armazenamento.obter_registro("OBR-2026-0001")["status"], "pendente")
    def test_aprovar_autorizado_atualiza_status_e_mensagem(self):
        ack = MagicMock()
        client = cliente_mock()
        client.usergroups_users_list.return_value = {"users": ["U_DIRETOR"]}
        self.app.actions["approve_project"](ack=ack, body=self._body_botao("approve_project", "U_DIRETOR"), client=client)
        client.chat_update.assert_called_once()
        self.assertEqual(armazenamento.obter_registro("OBR-2026-0001")["status"], "aprovado")
    def test_arquivar_canal_chama_conversations_archive(self):
        ack = MagicMock()
        client = cliente_mock()
        self.app.actions["archive_channel"](ack=ack, body=self._body_botao("archive_channel", "U_QUALQUER"), client=client)
        client.conversations_archive.assert_called_once_with(channel="C123CANAL")
        self.assertEqual(armazenamento.obter_registro("OBR-2026-0001")["status"], "arquivado")
    def test_gerar_pdf_despacha_para_erp_e_avisa_na_thread(self):
        ack = MagicMock()
        client = cliente_mock()
        self.app.actions["generate_pdf"](ack=ack, body=self._body_botao("generate_pdf", "U_QUALQUER"), client=client)
        client.chat_postMessage.assert_called_once()
        self.assertEqual(client.chat_postMessage.call_args.kwargs["thread_ts"], "1700000000.000100")
if __name__ == "__main__":
    unittest.main()
