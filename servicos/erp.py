"""Integração com o ERP: webhook JSON síncrono (Python/C#) + fallback em XML
para sistemas legados baseados em macro VBA (que não hospedam endpoints HTTP)."""
import logging
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import requests
import config
logger = logging.getLogger("ventosul-slack.erp")
def _payload_base(evento: str, canal_id: str | None, nome_canal: str | None, valores: dict) -> dict:
    return {
        "evento": evento,
        "canal_slack": nome_canal,
        "canal_id": canal_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dados": valores,
    }
def despachar_para_erp(evento: str, valores: dict, canal_id: str | None = None, nome_canal: str | None = None) -> dict:
    """Modo A: POST JSON síncrono no webhook do ERP (backend Python/C# próprio).
    Modo B (sempre executado como fallback e para consumo por VBA): grava um XML
    equivalente na pasta monitorada. Retorna o payload despachado, útil para testes/log."""
    payload = _payload_base(evento, canal_id, nome_canal, valores)
    enviado = False
    try:
        resposta = requests.post(config.ERP_WEBHOOK_URL, json=payload, timeout=config.ERP_WEBHOOK_TIMEOUT_SECONDS)
        resposta.raise_for_status()
        enviado = True
    except requests.RequestException as exc:
        logger.warning("Webhook ERP indisponível (%s); gravando fallback XML.", exc)
    caminho_xml = gravar_xml_para_vba(payload)
    payload["_webhook_enviado"] = enviado
    payload["_xml_fallback"] = caminho_xml
    return payload
def gravar_xml_para_vba(payload: dict) -> str:
    """Macros VBA normalmente não hospedam endpoints HTTP: a integração legada lê
    arquivos XML de uma pasta compartilhada via Workbook_Open / Application.OnTime.
    Devolve o caminho do arquivo gravado."""
    os.makedirs(config.ERP_XML_DROP_FOLDER, exist_ok=True)
    raiz = ET.Element("RegistroVentoSul", evento=payload["evento"])
    ET.SubElement(raiz, "CanalSlack").text = payload.get("canal_slack") or ""
    ET.SubElement(raiz, "CanalId").text = payload.get("canal_id") or ""
    ET.SubElement(raiz, "Timestamp").text = payload["timestamp"]
    dados_el = ET.SubElement(raiz, "Dados")
    for chave, valor in (payload.get("dados") or {}).items():
        campo = ET.SubElement(dados_el, "Campo", nome=chave)
        campo.text = ", ".join(valor) if isinstance(valor, list) else ("" if valor is None else str(valor))
    slug_evento = payload["evento"].replace(".", "_")
    slug_canal = (payload.get("canal_id") or "sem_canal").replace("#", "")
    nome_arquivo = f"{slug_evento}_{slug_canal}_{int(datetime.now().timestamp())}.xml"
    caminho = os.path.join(config.ERP_XML_DROP_FOLDER, nome_arquivo)
    ET.ElementTree(raiz).write(caminho, encoding="utf-8", xml_declaration=True)
    return caminho
