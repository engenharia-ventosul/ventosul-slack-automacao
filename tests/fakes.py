"""Dublê de teste para o `App` do slack_bolt.
Os handlers em handlers/*.py só usam três decorators (`command`, `action`,
`view`) e recebem (ack, body, client, view) — nada mais do slack_bolt é tocado.
Isso nos permite testar toda a lógica de negócio SEM a biblioteca slack_bolt
instalada, registrando os handlers numa classe leve e chamando-os diretamente."""
from unittest.mock import MagicMock
class FakeBoltApp:
    def __init__(self):
        self.commands = {}
        self.actions = {}
        self.views = {}
    def command(self, nome):
        def decorator(func):
            self.commands[nome] = func
            return func
        return decorator
    def action(self, action_id):
        def decorator(func):
            self.actions[action_id] = func
            return func
        return decorator
    def view(self, callback_id):
        def decorator(func):
            self.views[callback_id] = func
            return func
        return decorator
def cliente_mock() -> MagicMock:
    """Client falso com os retornos mínimos que os serviços esperam da Web API."""
    client = MagicMock()
    client.conversations_create.return_value = {"channel": {"id": "C123CANAL"}}
    client.usergroups_users_list.return_value = {"users": []}
    client.chat_postMessage.return_value = {"ts": "1700000000.000100"}
    return client
