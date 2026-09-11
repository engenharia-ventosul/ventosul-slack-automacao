"""Funções puras de negócio: slug de canal, resolução de stakeholders,
parsing de formulário do modal e geração de ID interno de registro.
Recebem `client` (um slack_sdk.WebClient real, ou qualquer objeto com a mesma
interface — nos testes usamos unittest.mock.MagicMock) como parâmetro, nunca
importado globalmente, o que torna cada função testável isoladamente.
"""
import itertools
import re
import unicodedata
from datetime import datetime
import config
_contador_registro = itertools.count(1)
_PREFIXO_REGISTRO = {"obra": "OBR", "manutencao": "MAN", "pagamento": "PAG"}
def slugify(texto: str) -> str:
    """Normaliza um texto livre para um trecho válido de nome de canal Slack
    (minúsculas, sem acento, apenas [a-z0-9-], sem hifens duplicados/nas pontas)."""
    if not texto:
        return "sem-nome"
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = texto.lower().strip()
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    texto = re.sub(r"-{2,}", "-", texto).strip("-")
    return texto[:60] or "sem-nome"
def gerar_registro_id(tipo: str, ano: int | None = None) -> str:
    """Gera um ID interno sequencial, ex.: OBR-2026-0091. Em produção, troque o
    contador em memória por uma sequence do banco/ERP para garantir unicidade
    entre múltiplas instâncias do middleware."""
    ano = ano or datetime.now().year
    numero = next(_contador_registro)
    prefixo = _PREFIXO_REGISTRO.get(tipo, "REG")
    return f"{prefixo}-{ano}-{numero:04d}"
def montar_nome_canal(tipo: str, valores: dict) -> str:
    hoje = datetime.now().strftime("%d%m")
    if tipo == "obra":
        return f"obra-{slugify(valores.get('nome_obra'))}"
    if tipo == "manutencao":
        return f"manut-{slugify(valores.get('cliente_local'))}-{hoje}"
    if tipo == "pagamento":
        return f"pag-{slugify(valores.get('fornecedor'))}-{hoje}"
    raise ValueError(f"Tipo de registro desconhecido: {tipo!r}")
def criar_canal(client, nome_canal: str, is_private: bool = True) -> str:
    """conversations.create — devolve o channel_id criado."""
    resposta = client.conversations_create(name=nome_canal, is_private=is_private)
    return resposta["channel"]["id"]
def resolver_stakeholders(client, tipo: str, valores: dict) -> list[str]:
    """Expande os User Groups configurados (config.GRUPOS) em User IDs individuais,
    pois conversations.invite exige IDs de usuário, não IDs de grupo (S0XXXXXXX)."""
    urgencia_alta = tipo == "manutencao" and valores.get("urgencia") == "alta"
    chave_grupo = "manutencao_urgente" if urgencia_alta else tipo
    grupos_slack = config.GRUPOS.get(chave_grupo, [])
    membros: set[str] = set()
    for group_id in grupos_slack:
        resposta = client.usergroups_users_list(usergroup=group_id)
        membros.update(resposta.get("users", []))
    if tipo == "obra" and valores.get("engenheiro_responsavel"):
        membros.add(valores["engenheiro_responsavel"])
    return sorted(membros)
def convidar_membros(client, canal_id: str, user_ids: list[str]) -> None:
    if not user_ids:
        return
    client.conversations_invite(channel=canal_id, users=",".join(dict.fromkeys(user_ids)))
def extrair_valores(state_values: dict) -> dict:
    """Faz o parse genérico do `view.state.values` do Slack — cobre todos os tipos
    de elemento usados nos modais (plain_text_input, static_select,
    multi_static_select, radio_buttons, datepicker, users_select)."""
    saida: dict = {}
    for bloco in state_values.values():
        for action_id, elemento in bloco.items():
            tipo_elemento = elemento.get("type")
            if tipo_elemento == "plain_text_input":
                saida[action_id] = elemento.get("value")
            elif tipo_elemento == "static_select":
                opcao = elemento.get("selected_option")
                saida[action_id] = opcao["value"] if opcao else None
            elif tipo_elemento == "multi_static_select":
                saida[action_id] = [o["value"] for o in elemento.get("selected_options") or []]
            elif tipo_elemento == "radio_buttons":
                opcao = elemento.get("selected_option")
                saida[action_id] = opcao["value"] if opcao else None
            elif tipo_elemento == "datepicker":
                saida[action_id] = elemento.get("selected_date")
            elif tipo_elemento == "users_select":
                saida[action_id] = elemento.get("selected_user")
            else:
                saida[action_id] = elemento.get("value")
    return saida
def usuario_pertence_a_grupo(client, user_id: str, group_id: str) -> bool:
    """Confere se `user_id` está entre os membros do User Group `group_id`.
    Usado nas autorizações de botão (ex.: só @diretoria aprova pagamentos)."""
    if not group_id:
        return False
    resposta = client.usergroups_users_list(usergroup=group_id)
    return user_id in (resposta.get("users") or [])
def validar_valores_obrigatorios(tipo: str, valores: dict) -> list[str]:
    """Validação de negócio complementar à do próprio Slack (campos `input` sem
    `optional: true` já são obrigatórios na UI). Usada para erros de formato
    (ex.: valor monetário) que o Block Kit não valida nativamente.
    Retorna uma lista de mensagens de erro (vazia se tudo estiver ok)."""
    erros = []
    if tipo == "pagamento":
        valor_bruto = (valores.get("valor_pagamento") or "").replace(",", ".").strip()
        try:
            if float(valor_bruto) <= 0:
                erros.append("O valor do pagamento deve ser maior que zero.")
        except ValueError:
            erros.append("Valor do pagamento inválido — use o formato 1234.56.")
    return erros
