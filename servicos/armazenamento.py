"""Armazenamento do estado dos registros (Obra/Manutenção/Pagamento).
Implementação de referência em memória, pensada para o middleware rodar como
processo único (é isso que os testes exercitam). Antes de ir para produção com
mais de um worker, troque `_REGISTROS` por Redis/Postgres — a interface
(salvar/obter/atualizar) permanece a mesma, então nenhum handler precisa mudar.
"""
import threading
_lock = threading.Lock()
_REGISTROS: dict[str, dict] = {}
def salvar_registro(registro_id: str, *, tipo: str, valores: dict, canal_id: str, nome_canal: str, autor_id: str, status: str = "pendente") -> dict:
    registro = {
        "registro_id": registro_id,
        "tipo": tipo,
        "valores": valores,
        "canal_id": canal_id,
        "nome_canal": nome_canal,
        "autor_id": autor_id,
        "status": status,
        "mensagem_ts": None,
    }
    with _lock:
        _REGISTROS[registro_id] = registro
    return registro
def obter_registro(registro_id: str) -> dict | None:
    with _lock:
        registro = _REGISTROS.get(registro_id)
        return dict(registro) if registro else None
def obter_registro_por_canal(canal_id: str) -> dict | None:
    with _lock:
        for registro in _REGISTROS.values():
            if registro["canal_id"] == canal_id:
                return dict(registro)
        return None
def atualizar_status(registro_id: str, novo_status: str) -> dict | None:
    with _lock:
        registro = _REGISTROS.get(registro_id)
        if registro is None:
            return None
        registro["status"] = novo_status
        return dict(registro)
def definir_mensagem_ts(registro_id: str, ts: str) -> None:
    with _lock:
        registro = _REGISTROS.get(registro_id)
        if registro is not None:
            registro["mensagem_ts"] = ts
def limpar_tudo() -> None:
    """Usado apenas pelos testes, para garantir isolamento entre casos."""
    with _lock:
        _REGISTROS.clear()
