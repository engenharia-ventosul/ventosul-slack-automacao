"""Construtores de Modais (Block Kit `views`) para o /ventosul-os.
Cada função retorna um dict pronto para `views.open` / `views.update`.
Nenhuma função aqui depende do slack_bolt/slack_sdk — são apenas dicionários,
o que as torna testáveis com o interpretador Python puro.
"""
import json
import config
TITULOS = {
    "obra": "Nova Obra",
    "manutencao": "Nova Manutenção",
    "pagamento": "Novo Pagamento",
}
def _private_metadata(tipo: str) -> str:
    return json.dumps({"tipo": tipo})
def _bloco_seletor_tipo(tipo_selecionado: str) -> dict:
    opcoes = [
        {"text": {"type": "plain_text", "text": "🏗️ Obra"}, "value": "obra"},
        {"text": {"type": "plain_text", "text": "🛠️ Manutenção"}, "value": "manutencao"},
        {"text": {"type": "plain_text", "text": "💰 Pagamento"}, "value": "pagamento"},
    ]
    inicial = next(o for o in opcoes if o["value"] == tipo_selecionado)
    return {
        "type": "input",
        "block_id": "b_tipo",
        "dispatch_action": True,
        "label": {"type": "plain_text", "text": "Tipo de Registro"},
        "element": {
            "type": "radio_buttons",
            "action_id": "select_tipo_registro",
            "initial_option": inicial,
            "options": opcoes,
        },
    }
def build_modal_selecao_tipo() -> dict:
    """Modal inicial aberto pelo /ventosul-os — começa em 'obra' por padrão."""
    return build_modal_por_tipo("obra")
def build_modal_por_tipo(tipo: str) -> dict:
    if tipo == "obra":
        campos = _campos_obra()
    elif tipo == "manutencao":
        campos = _campos_manutencao()
    elif tipo == "pagamento":
        campos = _campos_pagamento()
    else:
        raise ValueError(f"Tipo de registro desconhecido: {tipo!r}")
    return {
        "type": "modal",
        "callback_id": config.CALLBACK_ID_MODAL,
        "private_metadata": _private_metadata(tipo),
        "title": {"type": "plain_text", "text": TITULOS[tipo]},
        "submit": {"type": "plain_text", "text": "Criar Canal"},
        "close": {"type": "plain_text", "text": "Cancelar"},
        "blocks": [_bloco_seletor_tipo(tipo), {"type": "divider"}, *campos],
    }
def _campos_obra() -> list:
    return [
        {
            "type": "input",
            "block_id": "b_nome_obra",
            "label": {"type": "plain_text", "text": "Nome da Obra"},
            "element": {"type": "plain_text_input", "action_id": "nome_obra"},
        },
        {
            "type": "input",
            "block_id": "b_endereco",
            "label": {"type": "plain_text", "text": "Endereço"},
            "element": {"type": "plain_text_input", "action_id": "endereco", "multiline": True},
        },
        {
            "type": "input",
            "block_id": "b_razao_social",
            "label": {"type": "plain_text", "text": "Razão Social / CNPJ"},
            "element": {"type": "plain_text_input", "action_id": "razao_social_cnpj"},
        },
        {
            "type": "input",
            "block_id": "b_escopo",
            "label": {"type": "plain_text", "text": "Escopo Técnico"},
            "element": {
                "type": "multi_static_select",
                "action_id": "escopo_tecnico",
                "placeholder": {"type": "plain_text", "text": "Selecione um ou mais itens"},
                "options": [
                    {"text": {"type": "plain_text", "text": rotulo}, "value": valor}
                    for rotulo, valor in config.ESCOPO_TECNICO_OPCOES
                ],
            },
        },
        {
            "type": "input",
            "block_id": "b_engenheiro",
            "label": {"type": "plain_text", "text": "Engenheiro Responsável"},
            "element": {"type": "users_select", "action_id": "engenheiro_responsavel"},
        },
        {
            "type": "input",
            "block_id": "b_prazo",
            "label": {"type": "plain_text", "text": "Prazo de Execução"},
            "element": {"type": "datepicker", "action_id": "prazo_execucao"},
        },
    ]
def _campos_manutencao() -> list:
    return [
        {
            "type": "input",
            "block_id": "b_cliente_local",
            "label": {"type": "plain_text", "text": "Cliente / Local"},
            "element": {"type": "plain_text_input", "action_id": "cliente_local"},
        },
        {
            "type": "input",
            "block_id": "b_equipamento",
            "label": {"type": "plain_text", "text": "Equipamento"},
            "element": {"type": "plain_text_input", "action_id": "equipamento"},
        },
        {
            "type": "input",
            "block_id": "b_relato_defeito",
            "label": {"type": "plain_text", "text": "Relato do Defeito"},
            "element": {"type": "plain_text_input", "action_id": "relato_defeito", "multiline": True},
        },
        {
            "type": "input",
            "block_id": "b_urgencia",
            "label": {"type": "plain_text", "text": "Nível de Urgência"},
            "element": {
                "type": "radio_buttons",
                "action_id": "urgencia",
                "options": [
                    {"text": {"type": "plain_text", "text": rotulo}, "value": valor}
                    for rotulo, valor in config.NIVEL_URGENCIA_OPCOES
                ],
            },
        },
        {
            "type": "input",
            "block_id": "b_pecas",
            "label": {"type": "plain_text", "text": "Necessidade de Peças"},
            "optional": True,
            "element": {
                "type": "plain_text_input",
                "action_id": "necessidade_pecas",
                "placeholder": {"type": "plain_text", "text": "Ex.: capacitor 40uF, contator 25A (deixe vazio se não houver)"},
            },
        },
    ]
def _campos_pagamento() -> list:
    return [
        {
            "type": "input",
            "block_id": "b_fornecedor",
            "label": {"type": "plain_text", "text": "Fornecedor"},
            "element": {"type": "plain_text_input", "action_id": "fornecedor"},
        },
        {
            "type": "input",
            "block_id": "b_documento",
            "label": {"type": "plain_text", "text": "CNPJ / CPF"},
            "element": {"type": "plain_text_input", "action_id": "cnpj_cpf"},
        },
        {
            "type": "input",
            "block_id": "b_valor",
            "label": {"type": "plain_text", "text": "Valor (R$)"},
            "element": {"type": "plain_text_input", "action_id": "valor_pagamento", "placeholder": {"type": "plain_text", "text": "Ex.: 12500.90"}},
        },
        {
            "type": "input",
            "block_id": "b_vencimento",
            "label": {"type": "plain_text", "text": "Vencimento"},
            "element": {"type": "datepicker", "action_id": "vencimento"},
        },
        {
            "type": "input",
            "block_id": "b_vinculo",
            "label": {"type": "plain_text", "text": "Vínculo (Obra/Manutenção de destino)"},
            "element": {"type": "plain_text_input", "action_id": "vinculo_destino", "placeholder": {"type": "plain_text", "text": "Ex.: OBR-2026-0091 ou #manut-jbs-1109"}},
        },
        {
            "type": "input",
            "block_id": "b_comprovante",
            "label": {"type": "plain_text", "text": "Link do Comprovante/NF"},
            "element": {"type": "plain_text_input", "action_id": "link_comprovante"},
        },
    ]
