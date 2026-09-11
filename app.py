"""Entrypoint da automação Vento Sul <-> Slack — modo Socket Mode.
Socket Mode não precisa de URL pública nem de túnel: o processo abre uma
conexão de saída (WebSocket) para o Slack, então funciona atrás de qualquer
firewall/NAT — inclusive num notebook comum. É o modo recomendado por padrão.
Se em algum momento você preferir expor um endpoint HTTP de verdade (atrás de
um domínio próprio, em produção), use `app_http.py` no lugar deste arquivo —
o manifest e o .env precisam ser ajustados de acordo (ver README.md).
Uso:
    python3 app.py
"""
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import config
from handlers import actions, commands, views
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("ventosul-slack")
def create_bolt_app() -> App:
    bolt_app = App(
        token=config.SLACK_BOT_TOKEN,
        # Socket Mode não recebe webhooks HTTP, então não há requisição para
        # assinar/verificar — o signing secret fica opcional aqui (mantido só
        # para compatibilidade com app_http.py, se você trocar de modo).
        signing_secret=config.SLACK_SIGNING_SECRET or None,
        token_verification_enabled=config.SLACK_TOKEN_VERIFICATION_ENABLED,
    )
    commands.register(bolt_app)
    actions.register(bolt_app)
    views.register(bolt_app)
    return bolt_app
def main() -> None:
    if not config.SLACK_BOT_TOKEN:
        raise SystemExit(
            "SLACK_BOT_TOKEN não configurado. Preencha o .env (veja .env.example) "
            "ou rode `python3 bootstrap.py`."
        )
    if not config.SLACK_APP_TOKEN:
        raise SystemExit(
            "SLACK_APP_TOKEN não configurado (token xapp-..., gerado em "
            "Basic Information > App-Level Tokens, com o scope connections:write). "
            "Preencha o .env ou rode `python3 bootstrap.py`."
        )
    bolt_app = create_bolt_app()
    logger.info("Conectando ao Slack via Socket Mode...")
    SocketModeHandler(bolt_app, config.SLACK_APP_TOKEN).start()
if __name__ == "__main__":
    main()
