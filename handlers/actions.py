"""Handlers de `block_actions`: troca dinâmica do modal e os quatro botões do
rodapé do Dossiê (Aprovar, Registrar Pagamento, Gerar PDF, Arquivar Canal)."""
import logging
import config
import dossies
import modais
from servicos import armazenamento, erp, slack_helpers
logger = logging.getLogger("ventosul-slack.actions")
def register(app):
    # ------------------------------------------------------------------
    # Troca do radio Obra/Manutenção/Pagamento -> reconstrói o modal
    # ------------------------------------------------------------------
    @app.action("select_tipo_registro")
    def atualizar_modal_dinamico(ack, body, client):
        ack()
        tipo = body["actions"][0]["selected_option"]["value"]
        client.views_update(
            view_id=body["view"]["id"],
            hash=body["view"].get("hash"),
            view=modais.build_modal_por_tipo(tipo),
        )
    # ------------------------------------------------------------------
    # ✅ Aprovar Projeto — restrito ao grupo @diretoria
    # ------------------------------------------------------------------
    @app.action("approve_project")
    def aprovar_projeto(ack, body, client):
        ack()
        _tratar_botao_status(
            body, client,
            novo_status="aprovado", acao_label="Aprovado", evento_erp="aprovado",
            grupo_autorizado=config.GRUPO_DIRETORIA,
            mensagem_negado="⛔ Apenas a diretoria pode aprovar este projeto.",
        )
    # ------------------------------------------------------------------
    # 💰 Registrar Pagamento — restrito ao grupo @financeiro
    # ------------------------------------------------------------------
    @app.action("register_payment")
    def registrar_pagamento(ack, body, client):
        ack()
        _tratar_botao_status(
            body, client,
            novo_status="pago", acao_label="Pagamento registrado", evento_erp="pago",
            grupo_autorizado=config.GRUPO_FINANCEIRO,
            mensagem_negado="⛔ Apenas o financeiro pode registrar este pagamento.",
        )
    # ------------------------------------------------------------------
    # 📄 Gerar PDF — qualquer membro do canal pode disparar
    # ------------------------------------------------------------------
    @app.action("generate_pdf")
    def gerar_pdf(ack, body, client):
        ack()
        registro_id = body["actions"][0]["value"]
        canal_id = body["container"]["channel_id"]
        ts_original = body["container"]["message_ts"]
        registro = armazenamento.obter_registro(registro_id)
        if registro is None:
            client.chat_postEphemeral(channel=canal_id, user=body["user"]["id"], text="Registro não encontrado.")
            return
        # A geração do PDF em si (WeasyPrint/ReportLab, ou um serviço dedicado) fica
        # a cargo do ERP: aqui só disparamos o evento com todos os dados necessários.
        payload = erp.despachar_para_erp("gerar_pdf", registro["valores"], canal_id=canal_id, nome_canal=registro["nome_canal"])
        client.chat_postMessage(
            channel=canal_id, thread_ts=ts_original,
            text=f"📄 Solicitação de PDF enviada ao ERP para *{registro_id}* (arquivo: `{payload['_xml_fallback']}`).",
        )
    # ------------------------------------------------------------------
    # 🗄️ Arquivar Canal — sempre com `confirm` no Block Kit antes de chegar aqui
    # ------------------------------------------------------------------
    @app.action("archive_channel")
    def arquivar_canal(ack, body, client):
        ack()
        registro_id = body["actions"][0]["value"]
        canal_id = body["container"]["channel_id"]
        client.conversations_archive(channel=canal_id)
        armazenamento.atualizar_status(registro_id, "arquivado")
        registro = armazenamento.obter_registro(registro_id)
        if registro:
            erp.despachar_para_erp(
                f"{registro['tipo']}.arquivado", registro["valores"],
                canal_id=canal_id, nome_canal=registro["nome_canal"],
            )
        logger.info("Canal %s arquivado (registro %s) por %s", canal_id, registro_id, body["user"]["id"])
def _tratar_botao_status(body, client, *, novo_status: str, acao_label: str, evento_erp: str, grupo_autorizado: str, mensagem_negado: str) -> None:
    registro_id = body["actions"][0]["value"]
    ator_id = body["user"]["id"]
    canal_id = body["container"]["channel_id"]
    ts_original = body["container"]["message_ts"]
    if grupo_autorizado and not slack_helpers.usuario_pertence_a_grupo(client, ator_id, grupo_autorizado):
        client.chat_postEphemeral(channel=canal_id, user=ator_id, text=mensagem_negado)
        return
    registro = armazenamento.obter_registro(registro_id)
    if registro is None:
        client.chat_postEphemeral(channel=canal_id, user=ator_id, text="Registro não encontrado (pode já ter sido processado).")
        return
    armazenamento.atualizar_status(registro_id, novo_status)
    dossie_original = dossies.build_dossie_message(registro["tipo"], registro["valores"], registro["autor_id"], registro_id, status=registro["status"])
    novos_blocks = dossies.atualizar_status(dossie_original["blocks"], novo_status, ator_id, acao_label)
    client.chat_update(channel=canal_id, ts=ts_original, blocks=novos_blocks, text=dossie_original["text"])
    client.chat_postMessage(channel=canal_id, thread_ts=ts_original, text=f"{acao_label} por <@{ator_id}>.")
    erp.despachar_para_erp(f"{registro['tipo']}.{evento_erp}", registro["valores"], canal_id=canal_id, nome_canal=registro["nome_canal"])
