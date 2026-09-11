#!/usr/bin/env python3
"""Iniciador único do projeto — o único comando que você precisa rodar.
O que ele faz por você, sem nenhuma instalação manual:
  1. Cria um ambiente virtual (.venv) e instala todas as dependências dentro dele.
  2. Cria o arquivo .env (perguntando as credenciais do Slack, se você já tiver).
  3. Sobe o servidor (Socket Mode — não precisa de URL pública nem de túnel).
Uso:
    python3 bootstrap.py
"""
import hashlib
import os
import subprocess
import sys
from pathlib import Path
PROJETO_DIR = Path(__file__).resolve().parent
VENV_DIR = PROJETO_DIR / ".venv"
MARKER = VENV_DIR / ".requirements.hash"
REQUIREMENTS = PROJETO_DIR / "requirements.txt"
ENV_FILE = PROJETO_DIR / ".env"
ENV_EXAMPLE = PROJETO_DIR / ".env.example"
def _venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python3"
def garantir_venv_e_dependencias() -> None:
    if not VENV_DIR.exists():
        print("→ Criando ambiente virtual (.venv)...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
    hash_atual = hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()
    hash_salvo = MARKER.read_text().strip() if MARKER.exists() else None
    if hash_atual != hash_salvo:
        print("→ Instalando dependências (só acontece na primeira vez / quando requirements.txt mudar)...")
        subprocess.run([str(_venv_python()), "-m", "pip", "install", "--quiet", "--upgrade", "pip"], check=True)
        subprocess.run([str(_venv_python()), "-m", "pip", "install", "--quiet", "-r", str(REQUIREMENTS)], check=True)
        MARKER.write_text(hash_atual)
    else:
        print("→ Dependências já instaladas, seguindo direto.")
def reexecutar_dentro_do_venv() -> None:
    """Se ainda não estamos rodando com o Python do .venv, substitui o processo
    atual por ele — o usuário nunca precisa saber o que é 'ativar um venv'."""
    venv_python = _venv_python()
    if Path(sys.executable).resolve() != venv_python.resolve():
        os.execv(str(venv_python), [str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]])
def garantir_env() -> None:
    if ENV_FILE.exists():
        return
    print("→ Nenhum .env encontrado, criando agora.")
    conteudo = ENV_EXAMPLE.read_text(encoding="utf-8")
    if sys.stdin.isatty():
        conteudo = _perguntar_credenciais(conteudo)
    ENV_FILE.write_text(conteudo, encoding="utf-8")
    print(f"→ .env criado em {ENV_FILE}")
def _perguntar_credenciais(conteudo: str) -> str:
    print()
    print("Cole as credenciais do seu Slack App (Basic Information / OAuth & Permissions).")
    print("Se ainda não criou o app, aperte Enter 3x — o manifest.yml já está pronto para")
    print("colar em api.slack.com/apps > Create New App > From an app manifest.")
    bot_token = input("  SLACK_BOT_TOKEN (começa com xoxb-): ").strip()
    signing_secret = input("  SLACK_SIGNING_SECRET: ").strip()
    app_token = input("  SLACK_APP_TOKEN (começa com xapp-): ").strip()
    if bot_token:
        conteudo = conteudo.replace(
            "SLACK_BOT_TOKEN=xoxb-substitua-pelo-token-do-seu-app", f"SLACK_BOT_TOKEN={bot_token}"
        )
    if signing_secret:
        conteudo = conteudo.replace(
            "SLACK_SIGNING_SECRET=substitua-pelo-signing-secret-do-seu-app", f"SLACK_SIGNING_SECRET={signing_secret}"
        )
    if app_token:
        conteudo = conteudo.replace(
            "SLACK_APP_TOKEN=xapp-substitua-pelo-app-level-token", f"SLACK_APP_TOKEN={app_token}"
        )
    print()
    return conteudo
def main() -> None:
    garantir_venv_e_dependencias()
    reexecutar_dentro_do_venv()  # a partir daqui, sempre dentro do .venv
    garantir_env()
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE, override=True)
    if not os.environ.get("SLACK_BOT_TOKEN") or not os.environ.get("SLACK_APP_TOKEN"):
        print(
            "\n============================================================\n"
            "ÚLTIMO PASSO — este aqui só você consegue fazer (é o Slack que\n"
            "exige um humano logado para criar/instalar o App, por segurança):\n"
            "  1. Abra https://api.slack.com/apps → 'Create New App' → 'From an app manifest'\n"
            "  2. Cole o conteúdo de manifest.yml\n"
            "  3. Em 'Install App', clique 'Install to Workspace'\n"
            "  4. Copie o 'Bot User OAuth Token' (xoxb-...) em 'OAuth & Permissions'\n"
            "  5. Em 'Basic Information' → 'App-Level Tokens' → 'Generate Token and Scopes',\n"
            "     crie um token com o scope connections:write (vai gerar um xapp-...)\n"
            "  6. Cole os tokens no arquivo .env e rode `python3 bootstrap.py` de novo\n"
            "============================================================\n"
        )
        return
    print("→ Tudo configurado. Conectando ao Slack (Socket Mode)...")
    os.execv(sys.executable, [sys.executable, str(PROJETO_DIR / "app.py")])
if __name__ == "__main__":
    main()
