"""Handler de submit do modal (`view_submission`): valida, cria o canal, convida
os stakeholders corretos e posta o Dossiê Técnico. É aqui que as três
regras de negócio (Obra / Manutenção / Pagamento) convergem."""
import json
import logging
import dossies
from servicos import armazenamento, erp, slack_helpers
logger = logging.getLogger("ventosul-slack.views")
def register(app):
    @app.view("submit_registro_ventosul")
    def processar_submit(ack, body, client, view):
        metadata = json.loads(view["private_metadata"] or "{}")
        tipo = metadata.get("tipo", "obra")
        valores = slack_helpers.extrair_valores(view["state"]["values"])
        erros = slack_helpers.validar_valores_obrigatorios(tipo, valores)
        if erros:
            # `response_action: errors` reabre o modal com a mensagem embaixo do campo,
            # sem fechar a janela — é a forma correta de validação server-side no Slack.
            ack(
                response_action="errors",
                errors={"b_valor": erros[0]} if tipo == "pagamento" else {},
            )
            return
        ack()  # a partir daqui o modal já fechou — erros vão por DM, nunca mais pelo ack()
        autor_id = body["user"]["id"]
        try:
            _processar_registro(client, tipo, valores, autor_id)
        except Exception:
            logger.exception("Falha ao processar submit do tipo=%s", tipo)
            client.chat_postMessage(
                channel=autor_id,
                text=(
                    f"⚠️ Não foi possível concluir o cadastro de *{tipo}*. "
                    "A equipe de TI já foi notificada do erro."
                ),
            )
def _processar_registro(client, tipo: str, valores: dict, autor_id: str) -> dict:
    registro_id = slack_helpers.gerar_registro_id(tipo)
    nome_canal = slack_helpers.montar_nome_canal(tipo, valores)
    canal_id = slack_helpers.criar_canal(client, nome_canal)
    membros = slack_helpers.resolver_stakeholders(client, tipo, valores)
    slack_helpers.convidar_membros(client, canal_id, membros + [autor_id])
    armazenamento.salvar_registro(
        registro_id, tipo=tipo, valores=valores, canal_id=canal_id,
        nome_canal=nome_canal, autor_id=autor_id, status="pendente",
    )
    dossie = dossies.build_dossie_message(tipo, valores, autor_id, registro_id, status="pendente")
    resposta_msg = client.chat_postMessage(channel=canal_id, **dossie)
    ts = resposta_msg.get("ts") if isinstance(resposta_msg, dict) else resposta_msg["ts"]
    armazenamento.definir_mensagem_ts(registro_id, ts)
    erp.despachar_para_erp(f"{tipo}.criado", valores, canal_id=canal_id, nome_canal=nome_canal)
    logger.info("Registro %s criado no canal #%s (%s)", registro_id, nome_canal, canal_id)
    return {"registro_id": registro_id, "canal_id": canal_id, "nome_canal": nome_canal}
