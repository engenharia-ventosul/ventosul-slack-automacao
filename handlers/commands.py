"""Handler do Slash Command /ventosul-os."""
import logging
import modais
logger = logging.getLogger("ventosul-slack.commands")
def register(app):
    @app.command("/ventosul-os")
    def abrir_modal_selecao(ack, body, client):
        ack()  # obrigatório responder em < 3s
        client.views_open(
            trigger_id=body["trigger_id"],
            view=modais.build_modal_selecao_tipo(),
        )
        logger.info("Modal de seleção aberto por %s", body.get("user_id"))
