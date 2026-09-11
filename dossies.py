"""Construtores do Dossiê Técnico (mensagem Block Kit) postado no canal recém-criado.
Assim como em modais.py, tudo aqui é dict puro — sem dependência do slack_bolt —
para poder ser testado isoladamente.
"""
import config
_ESCOPO_LABELS = dict((valor, rotulo) for rotulo, valor in config.ESCOPO_TECNICO_OPCOES)
_URGENCIA_LABELS = dict((valor, rotulo) for rotulo, valor in config.NIVEL_URGENCIA_OPCOES)
_STATUS_EMOJI = {
    "pendente": "🟡 Pendente de Aprovação",
    "aprovado": "🟢 Aprovado",
    "pago": "🟢 Pago",
    "arquivado": "⚪ Arquivado",
}
# Botões padrão do rodapé — reaproveitados pelos três tipos, o "value" carrega o registro_id
# para que o handler saiba a qual registro a interação se refere.
def _bloco_acoes(registro_id: str) -> dict:
    return {
        "type": "actions",
        "block_id": "acoes_dossie",
        "elements": [
            {
                "type": "button",
                "action_id": "approve_project",
                "text": {"type": "plain_text", "text": "✅ Aprovar Projeto"},
                "style": "primary",
                "value": registro_id,
            },
            {
                "type": "button",
                "action_id": "register_payment",
                "text": {"type": "plain_text", "text": "💰 Registrar Pagamento"},
                "value": registro_id,
            },
            {
                "type": "button",
                "action_id": "generate_pdf",
                "text": {"type": "plain_text", "text": "📄 Gerar PDF"},
                "value": registro_id,
            },
            {
                "type": "button",
                "action_id": "archive_channel",
                "text": {"type": "plain_text", "text": "🗄️ Arquivar Canal"},
                "style": "danger",
                "value": registro_id,
                "confirm": {
                    "title": {"type": "plain_text", "text": "Confirmar arquivamento"},
                    "text": {"type": "mrkdwn", "text": "Este canal será arquivado. Confirma?"},
                    "confirm": {"type": "plain_text", "text": "Arquivar"},
                    "deny": {"type": "plain_text", "text": "Cancelar"},
                },
            },
        ],
    }
def _bloco_contexto(registro_id: str) -> dict:
    return {
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"Vento Sul Soluções Térmicas · Registro automático · ID interno: {registro_id}"}
        ],
    }
def build_dossie_message(tipo: str, valores: dict, autor_id: str, registro_id: str, status: str = "pendente") -> dict:
    """Dispatcher — devolve o payload completo (kwargs de chat_postMessage, exceto 'channel')."""
    construtores = {
        "obra": build_dossie_obra,
        "manutencao": build_dossie_manutencao,
        "pagamento": build_dossie_pagamento,
    }
    if tipo not in construtores:
        raise ValueError(f"Tipo de registro desconhecido: {tipo!r}")
    return construtores[tipo](valores, autor_id, registro_id, status)
def build_dossie_obra(valores: dict, autor_id: str, registro_id: str, status: str = "pendente") -> dict:
    escopo = ", ".join(_ESCOPO_LABELS.get(v, v) for v in valores.get("escopo_tecnico", []))
    eng = valores.get("engenheiro_responsavel")
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "🏗️ Nova Obra Cadastrada", "emoji": True}},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{valores.get('nome_obra', '—')}*\nCadastrada por <@{autor_id}>",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Endereço:*\n{valores.get('endereco', '—')}"},
                {"type": "mrkdwn", "text": f"*Razão Social/CNPJ:*\n{valores.get('razao_social_cnpj', '—')}"},
                {"type": "mrkdwn", "text": f"*Escopo Técnico:*\n{escopo or '—'}"},
                {"type": "mrkdwn", "text": f"*Eng. Responsável:*\n{f'<@{eng}>' if eng else '—'}"},
                {"type": "mrkdwn", "text": f"*Prazo de Execução:*\n{valores.get('prazo_execucao', '—')}"},
                {"type": "mrkdwn", "text": f"*Status:*\n{_STATUS_EMOJI.get(status, status)}"},
            ],
        },
        {"type": "divider"},
        _bloco_contexto(registro_id),
        _bloco_acoes(registro_id),
    ]
    return {"text": f"Nova Obra cadastrada: {valores.get('nome_obra', '—')}", "blocks": blocks}
def build_dossie_manutencao(valores: dict, autor_id: str, registro_id: str, status: str = "pendente") -> dict:
    urgencia_valor = valores.get("urgencia", "")
    urgencia_label = _URGENCIA_LABELS.get(urgencia_valor, urgencia_valor or "—")
    alerta = "🚨 " if urgencia_valor == "alta" else ""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{alerta}🛠️ Nova Manutenção Cadastrada", "emoji": True},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{valores.get('cliente_local', '—')}*\nCadastrada por <@{autor_id}>",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Equipamento:*\n{valores.get('equipamento', '—')}"},
                {"type": "mrkdwn", "text": f"*Nível de Urgência:*\n{urgencia_label}"},
                {"type": "mrkdwn", "text": f"*Necessidade de Peças:*\n{valores.get('necessidade_pecas') or 'Nenhuma informada'}"},
                {"type": "mrkdwn", "text": f"*Status:*\n{_STATUS_EMOJI.get(status, status)}"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Relato do Defeito:*\n{valores.get('relato_defeito', '—')}"},
        },
        {"type": "divider"},
        _bloco_contexto(registro_id),
        _bloco_acoes(registro_id),
    ]
    return {"text": f"Nova manutenção cadastrada: {valores.get('cliente_local', '—')}", "blocks": blocks}
def build_dossie_pagamento(valores: dict, autor_id: str, registro_id: str, status: str = "pendente") -> dict:
    valor = valores.get("valor_pagamento", "—")
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "💰 Novo Pagamento Cadastrado", "emoji": True}},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{valores.get('fornecedor', '—')}*\nCadastrado por <@{autor_id}>",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*CNPJ/CPF:*\n{valores.get('cnpj_cpf', '—')}"},
                {"type": "mrkdwn", "text": f"*Valor:*\nR$ {valor}"},
                {"type": "mrkdwn", "text": f"*Vencimento:*\n{valores.get('vencimento', '—')}"},
                {"type": "mrkdwn", "text": f"*Vínculo:*\n{valores.get('vinculo_destino', '—')}"},
                {"type": "mrkdwn", "text": f"*Comprovante/NF:*\n{valores.get('link_comprovante', '—')}"},
                {"type": "mrkdwn", "text": f"*Status:*\n{_STATUS_EMOJI.get(status, status)}"},
            ],
        },
        {"type": "divider"},
        _bloco_contexto(registro_id),
        _bloco_acoes(registro_id),
    ]
    return {"text": f"Novo pagamento cadastrado: {valores.get('fornecedor', '—')}", "blocks": blocks}
def atualizar_status(mensagem_blocks: list, novo_status: str, ator_id: str, acao_label: str) -> list:
    """Retorna uma cópia dos blocks com o campo 'Status' atualizado e uma nota de auditoria
    anexada ao bloco de contexto — usado por chat.update quando um botão é clicado."""
    import copy
    from datetime import datetime
    blocks = copy.deepcopy(mensagem_blocks)
    agora = datetime.now().strftime("%d/%m %H:%M")
    for bloco in blocks:
        if bloco.get("type") == "section" and "fields" in bloco:
            for campo in bloco["fields"]:
                if campo["text"].startswith("*Status:*"):
                    campo["text"] = f"*Status:*\n{_STATUS_EMOJI.get(novo_status, novo_status)} — {acao_label} por <@{ator_id}> em {agora}"
    return blocks
