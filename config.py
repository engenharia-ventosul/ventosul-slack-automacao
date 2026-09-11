"""Configuração central da automação Vento Sul <-> Slack.
Todos os valores sensíveis vêm de variáveis de ambiente (ver .env.example).
Nada de token/secret deve ser hardcoded aqui.
"""
import os
from dotenv import load_dotenv
# Sempre resolve o .env relativo à pasta do projeto (não ao diretório de onde o
# comando foi chamado) — evita bugs de "funciona só se eu rodar de dentro da pasta".
_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(_ENV_PATH)  # em produção, prefira um cofre de secrets (Vault, Secrets Manager) ao .env
# --- Credenciais Slack -------------------------------------------------------
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")
# Token xapp-... com o scope connections:write — só é necessário no modo Socket Mode
# (app.py). Gerado em Basic Information > App-Level Tokens, depois de criar o app.
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "")
# Desliga a chamada auth.test no boot do Bolt (útil em CI/testes sem token real).
# Em produção, deixe True (padrão) para falhar rápido se o token estiver errado.
SLACK_TOKEN_VERIFICATION_ENABLED = os.environ.get("SLACK_TOKEN_VERIFICATION_ENABLED", "true").lower() == "true"
# --- Integração ERP ----------------------------------------------------------
ERP_WEBHOOK_URL = os.environ.get("ERP_WEBHOOK_URL", "http://localhost:8080/erp/webhook")
ERP_WEBHOOK_TIMEOUT_SECONDS = float(os.environ.get("ERP_WEBHOOK_TIMEOUT_SECONDS", "5"))
ERP_XML_DROP_FOLDER = os.environ.get("ERP_XML_DROP_FOLDER", "./erp_inbox")
# --- Servidor -----------------------------------------------------------------
PORT = int(os.environ.get("PORT", "3000"))
# --- User Groups (Settings > People > User Groups no Slack) -----------------
# Os handles (@engenharia etc.) precisam ser mapeados para o Group ID (formato S0XXXXXXX)
# na aba "About" do grupo, ou via API usergroups.list.
GRUPO_ENGENHARIA = os.environ.get("SLACK_GROUP_ENGENHARIA", "")
GRUPO_CAMPO = os.environ.get("SLACK_GROUP_CAMPO", "")
GRUPO_DIRETORIA = os.environ.get("SLACK_GROUP_DIRETORIA", "")
GRUPO_FINANCEIRO = os.environ.get("SLACK_GROUP_FINANCEIRO", "")
GRUPOS = {
    "obra": [g for g in [GRUPO_ENGENHARIA] if g],
    "manutencao": [g for g in [GRUPO_CAMPO] if g],
    "manutencao_urgente": [g for g in [GRUPO_CAMPO, GRUPO_DIRETORIA] if g],
    "pagamento": [g for g in [GRUPO_DIRETORIA, GRUPO_FINANCEIRO] if g],
}
# --- Opções de formulário -----------------------------------------------------
ESCOPO_TECNICO_OPCOES = [
    ("Instalação VRF", "vrf"),
    ("Chiller", "chiller"),
    ("Dutos", "dutos"),
    ("Automação/BMS", "bms"),
]
NIVEL_URGENCIA_OPCOES = [
    ("Baixa", "baixa"),
    ("Média", "media"),
    ("Alta / Parada", "alta"),
]
CALLBACK_ID_MODAL = "submit_registro_ventosul"
