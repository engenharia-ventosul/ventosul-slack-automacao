"""Entrypoint da automação Vento Sul <-> Slack.
Uso normal (depois que o bootstrap já resolveu as dependências):
    python3 app.py
Não rode este arquivo diretamente sem passar por `iniciar.sh`/`bootstrap.py`
pelo menos uma vez — é ele que garante que slack_bolt/slack_sdk/flask estão
instalados e que o .env existe.
"""
import logging
from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
import config
from handlers import actions, commands, views
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("ventosul-slack")
def create_bolt_app() -> App:
    bolt_app = App(
        token=config.SLACK_BOT_TOKEN,
        signing_secret=config.SLACK_SIGNING_SECRET,
        # Evita a chamada auth.test no boot quando ainda não há token real
        # (testes, CI, primeira execução do bootstrap antes do usuário colar o token).
        token_verification_enabled=config.SLACK_TOKEN_VERIFICATION_ENABLED,
    )
    commands.register(bolt_app)
    actions.register(bolt_app)
    views.register(bolt_app)
    return bolt_app
bolt_app = create_bolt_app()
flask_app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)
@flask_app.route("/slack/commands", methods=["POST"])
def slack_commands():
    return handler.handle(request)
@flask_app.route("/slack/interactions", methods=["POST"])
def slack_interactions():
    return handler.handle(request)
@flask_app.route("/healthz", methods=["GET"])
def healthz():
    return {"status": "ok"}, 200
if __name__ == "__main__":
    if not config.SLACK_BOT_TOKEN or not config.SLACK_SIGNING_SECRET:
        logger.warning(
            "SLACK_BOT_TOKEN/SLACK_SIGNING_SECRET não configurados — o servidor vai subir, "
            "mas nenhuma chamada à API do Slack vai funcionar até você rodar o bootstrap "
            "ou preencher o .env."
        )
    logger.info("Subindo servidor em http://0.0.0.0:%s ...", config.PORT)
    flask_app.run(host="0.0.0.0", port=config.PORT)
