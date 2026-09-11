# Vento Sul OS — Automação Slack
Implementação completa do `/ventosul-os`: Slash Command → Modal dinâmico (Obra /
Manutenção / Pagamento) → criação automática de canal → convite dos
stakeholders certos → Dossiê Técnico em Block Kit → botões interativos →
integração com o ERP (webhook JSON + fallback XML para VBA).
## Rodar sem instalar nada manualmente
```bash
python3 bootstrap.py
# ou, se preferir dar duplo-clique/atalho:
./iniciar.sh
```
Esse único comando:
**Passo 1.** cria um ambiente virtual (`.venv`) e instala todas as dependências dentro dele;
**Passo 2.** cria o `.env` (perguntando os tokens do Slack, se você já tiver);
**Passo 3.** sobe o servidor em **Socket Mode** — o processo abre uma conexão de saída para o Slack, então não precisa de URL pública, domínio, nem túnel (ngrok etc.); funciona atrás de qualquer firewall/NAT, inclusive num notebook comum.
Rode `python3 bootstrap.py` de novo sempre que quiser (re-)iniciar — ele detecta o que já está pronto e pula direto para o que falta.
### O único passo que só você pode fazer (e por quê)
Criar e instalar um Slack App exige um humano logado no navegador — é uma
exigência de segurança do próprio Slack, nenhuma automação legítima consegue
pular essa etapa. O `bootstrap.py` te mostra exatamente isto quando faltar:
**Passo 1.** Abra **https://api.slack.com/apps** → **Create New App** → **From an app manifest**
**Passo 2.** Cole o conteúdo de `manifest.yml`
**Passo 3.** Em **Install App**, clique **Install to Workspace**
**Passo 4.** Copie o **Bot User OAuth Token** (`xoxb-...`) em **OAuth & Permissions**
**Passo 5.** Em **Basic Information** → **App-Level Tokens** → **Generate Token and Scopes**, crie um token com o scope `connections:write` (isso gera um `xapp-...`) — é o que liga o Socket Mode
**Passo 6.** Cole os tokens no `.env` (ou deixe o próprio `bootstrap.py` perguntar) e rode `python3 bootstrap.py` de novo
Depois de instalado uma vez, os Group IDs (`SLACK_GROUP_ENGENHARIA`,
`SLACK_GROUP_CAMPO`, `SLACK_GROUP_DIRETORIA`, `SLACK_GROUP_FINANCEIRO`) e a
URL do webhook do seu ERP (`ERP_WEBHOOK_URL`) vão no mesmo `.env` — veja
`.env.example` para a lista completa.
Se preferir expor um endpoint HTTP de verdade atrás de um domínio próprio em
produção (em vez de Socket Mode), use `app_http.py` no lugar de `app.py` —
ele já vem pronto (Flask + rotas `/slack/commands` e `/slack/interactions`),
só ajuste o manifest para usar Request URLs em vez de `socket_mode_enabled`.
## Testar (sem Slack, sem rede, sem credenciais)
```bash
./executar_testes.sh
```
63 testes cobrindo toda a lógica de negócio: geração de nome de canal e slug,
roteamento de stakeholders por User Group (incluindo escalonamento de
manutenção urgente para a diretoria), parsing dos campos do modal, montagem
dos três Dossiês (Obra/Manutenção/Pagamento), autorização dos botões
(Aprovar exige @diretoria, Registrar Pagamento exige @financeiro), o fluxo
completo de submit → criação de canal → convite → postagem, e o
webhook/XML do ERP com fallback quando o ERP está fora do ar.
## Estrutura
```
app.py               → entrypoint Flask + slack_bolt (rotas /slack/commands e /slack/interactions)
bootstrap.py          → iniciador zero-instalação (venv, .env, túnel público, manifest)
config.py             → toda a configuração via variáveis de ambiente
modais.py             → Block Kit dos modais (seleção de tipo + campos de Obra/Manutenção/Pagamento)
dossies.py            → Block Kit do Dossiê Técnico postado no canal + atualização de status
manifest.yml          → App Manifest do Slack (scopes, slash command, interactivity)
handlers/
  commands.py          → /ventosul-os
  views.py              → submit do modal (view_submission)
  actions.py            → troca dinâmica de tipo + botões (Aprovar/Pagamento/PDF/Arquivar)
servicos/
  slack_helpers.py      → slugify, nome de canal, resolução de User Groups, parsing do form
  erp.py                 → despacho ao webhook do ERP + fallback XML para VBA
  armazenamento.py       → estado dos registros (referência em memória — troque por Postgres/Redis em produção)
tests/                 → 63 testes unitários/integração (unittest + mocks, sem dependências externas)
```
## Notas para produção
**Múltiplos processos / escala**: troque `servicos/armazenamento.py` (hoje em memória) por Postgres ou Redis antes de rodar mais de um worker — a interface (`salvar_registro`/`obter_registro`/`atualizar_status`) já foi desenhada para essa troca não exigir mudança nos handlers.
**Servidor**: `app.py` usa o servidor de desenvolvimento do Flask. Para produção, coloque atrás de Gunicorn/uWSGI (`gunicorn -w 4 -b 0.0.0.0:3000 app:flask_app`).
**Fila assíncrona**: o Slack exige resposta em até 3s; hoje o `ack()` já é a primeira linha de cada handler, mas em alto volume mova o trabalho pesado (criação de canal, chamadas ao ERP) para uma fila (Celery/RQ) depois do `ack()`.
**Integração VBA/ERP legado**: `servicos/erp.py` grava um XML por evento em `ERP_XML_DROP_FOLDER` — aponte essa pasta para um compartilhamento de rede lido pela macro (`Workbook_Open` ou `Application.OnTime`).
**Segredos**: em produção, troque o `.env` por um cofre (Vault, AWS/GCP Secrets Manager).
