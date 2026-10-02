# 5LTEP-L4: kit de proveniência da Camada 4 do 5L-TEP

**Monitoramento de proveniência compatível com o W3C PROV-DM para portais de Dados Abertos Governamentais baseados em CKAN.**

[![Tests](https://github.com/lsp3cesarschool/5ltep-layer4/actions/workflows/tests.yml/badge.svg)](https://github.com/lsp3cesarschool/5ltep-layer4/actions/workflows/tests.yml)
[![Monitoring](https://github.com/lsp3cesarschool/5ltep-layer4/actions/workflows/monitor.yml/badge.svg)](https://github.com/lsp3cesarschool/5ltep-layer4/actions/workflows/monitor.yml)
[![Cross-Check](https://github.com/lsp3cesarschool/5ltep-layer4/actions/workflows/cross_check.yml/badge.svg)](https://github.com/lsp3cesarschool/5ltep-layer4/actions/workflows/cross_check.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

[English](README.md) · **Português**

<!-- CROSS_CHECK_STATUS:START -->
✅ **Verificação cruzada aprovada** — última verificação em 2026-09-27 09:27 UTC. Todos os 79 conjuntos de dados acessíveis estão sincronizados com o portal ao vivo (dadosabertos.ibama.gov.br); o snapshot mais recente tem 5,3 h.
<!-- CROSS_CHECK_STATUS:END -->

📄 **O que mudou no portal?** Veja [`changes.md`](changes.md) (em inglês): um registro legível de cada mudança detectada (quando, em qual conjunto de dados e como, por exemplo, arquivos transferidos para outro servidor ou trocados entre zip e formato simples), reconstruído automaticamente a cada ciclo de monitoramento.

## Visão geral

Este kit implementa a **Camada 4 (Observabilidade e Proveniência)** da Pirâmide de Engenharia de Confiança em Cinco Camadas (5L-TEP, *Five-Layer Trust Engineering Pyramid*) para a garantia de qualidade de Dados Abertos Governamentais. Ele monitora portais de dados baseados em CKAN (por exemplo, o do [IBAMA](https://dadosabertos.ibama.gov.br)), detecta mudanças por meio de impressões digitais SHA-256 e gera registros de proveniência em JSON-LD compatíveis com o W3C PROV-DM. Desde a v1.0.2, cada registro também descreve *como* o conjunto de dados mudou (campos alterados, mudanças de URL dos recursos, trocas entre zip e formato simples), e essa mesma descrição alimenta o [`changes.md`](changes.md).

> **Escopo**: este repositório contém **apenas** os módulos essenciais da Camada 4. As Camadas 1 a 3 (validação estrutural, semântica e de anomalias) e a Camada 5 (painéis de governança) estão fora do escopo desta implementação.

### Arquitetura

```
┌──────────────────────────────────────────────────┐
│            GitHub Actions (cron 6h)              │
│      ~15% da cota gratuita (medido)              │
└──────────────────────────┬───────────────────────┘
                           │ dispara
                           ▼
┌──────────────────────────────────────────────────┐
│  ① CKAN Harvester                                │
│     Consulta à API + nova tentativa com          │
│     backoff exponencial                          │
│     (package_list + package_show)                │
└──────────────────────────┬───────────────────────┘
                           │ snapshots de metadados
                           ▼
┌──────────────────────────────────────────────────┐
│  ② Hash Engine                                   │
│     Hashes SHA-256 do conteúdo e do manifesto    │
│     de recursos                                  │
│     Taxonomia de mudanças: 4 tipos de evento     │
│     (CLEAN_UPDATE, SCHEMA_DRIFT,                 │
│      RETRO_ALTER, CONTENT_MOD)                   │
└──────────────────────────┬───────────────────────┘
                           │ ChangeEvents
                           ▼
┌──────────────────────────────────────────────────┐
│  ★ ③ PROV-DM Mapper (NÚCLEO DA L4)  ★           │
│     Geração de JSON-LD W3C PROV-DM               │
│     URIs de entidade endereçadas por conteúdo    │
│     Modelo de dois agentes: observador +         │
│     custodiante                                  │
│     Cadeias de derivação + anotações de mudança  │
└──────────────────────────┬───────────────────────┘
                           │ registros de proveniência
                           ▼
┌──────────────────────────────────────────────────┐
│  Repositório Git (somente acréscimo, imutável)   │
│  logs de proveniência .jsonld por conjunto       │
│  violação evidenciada pelos hashes de commit     │
└──────────────────────────────────────────────────┘
```

## Taxonomia de detecção de mudanças


| Tipo de mudança | Severidade | Descrição |
|---|---|---|
| `CLEAN_UPDATE` | INFO | Nenhuma mudança detectada (linha de base ou inalterado) |
| `SCHEMA_DRIFT` | **CRITICAL** | Mudança estrutural — quantidade, nomes ou formatos dos recursos alterados |
| `RETRO_ALTER` | **CRITICAL** | Hash mudou SEM avanço do timestamp — edição retroativa não documentada |
| `CONTENT_MOD` | WARNING | Modificação de conteúdo com atualização adequada do timestamp |

### Lógica de detecção

```
Dados: h_t = SHA-256(canonical_json(stable_fields(metadata_t)))
       (title, notes, metadata_modified e, de cada recurso, name, format,
        URL, tamanho e última modificação; campos voláteis da API são excluídos)
       h_{t-1} = hash armazenado no ciclo anterior

1. Se h_{t-1} é NULL            → CLEAN_UPDATE (primeira observação)
2. Se h_t == h_{t-1}            → CLEAN_UPDATE (sem mudança)
3. Se manifest_hash difere      → SCHEMA_DRIFT (quebra estrutural)
4. Se timestamp_t ≤ timestamp_{t-1} → RETRO_ALTER (edição retroativa)
5. Caso contrário               → CONTENT_MOD (atualização normal)
```

## Estratégia de mapeamento para o PROV-DM

### Modelo de dois agentes

O kit implementa um modelo de proveniência com dois agentes, que distingue o **observador** do **custodiante dos dados**:

- **prov:SoftwareAgent** (observador): o kit 5L-TEP / runner do GitHub Actions
- **5ltep:DataCustodian** (custodiante): o órgão governamental de origem (do campo `organization` do CKAN)

Isso garante que a responsabilidade seja atribuída corretamente (cf. Simmhan et al., 2005), em consonância com as obrigações de transparência da LAI (Lei de Acesso à Informação).

### Identificação de entidades

Cada snapshot de um conjunto de dados se torna uma `prov:Entity` identificada por uma URI endereçada por conteúdo:
```
{portal_url}/dataset/{dataset_id}#{sha256_prefix}
```
Como qualquer mudança produz um identificador criptograficamente distinto, o requisito de imutabilidade de entidades do PROV-DM é satisfeito por construção.

### Cadeias de derivação

Quando um conjunto de dados muda, a nova entidade se liga à sua antecessora por `wasDerivedFrom`, formando uma cadeia de derivação imutável anotada com `5ltep:changeType` e `5ltep:severity`. Desde a v1.0.2, cada registro também descreve *como* o conjunto de dados mudou: `5ltep:changeSummary` (resumo de uma linha, em inglês), `5ltep:changedFields`, `5ltep:fieldsOutsideFingerprint`, `5ltep:resourceUrlChanges`, `5ltep:hostMoves` e `5ltep:packagingChanges`.

## Início rápido

### Pré-requisitos

- Python 3.10+
- Um portal de dados abertos baseado em CKAN

### Instalação

```bash
git clone https://github.com/lsp3cesarschool/5ltep-layer4.git
cd 5ltep-layer4
pip install -r requirements.txt
```

### Execução local

```bash
# Monitora 5 conjuntos de dados do portal do IBAMA
python main.py --portal https://dadosabertos.ibama.gov.br --max-datasets 5

# Execução de teste (sem gravar arquivos)
python main.py --portal https://dadosabertos.ibama.gov.br --max-datasets 3 --dry-run

# Execução completa (todos os conjuntos de dados de uma organização)
python main.py --portal https://dadosabertos.ibama.gov.br --org ibama
```

### Execução dos testes

```bash
pytest tests/ -v
# 38 testes cobrindo: determinismo do hash, os 4 tipos de mudança, modelo de dois
# agentes, cadeias de derivação, persistência somente por acréscimo, pipeline de
# ponta a ponta, alertas de mudança crítica (SCHEMA_DRIFT/RETRO_ALTER) e sinalização
# para a CI, interoperabilidade PROV-O com a biblioteca `prov` (requer:
# pip install prov rdflib), detalhes das mudanças (mudanças de servidor, empacotamento)
# e geração do changes.md
```

### Implantação no GitHub Actions

O kit roda automaticamente a cada 6 horas via GitHub Actions (cerca de 15% da cota gratuita de 2.000 minutos, medido ao longo de 30 dias; repositórios públicos não são cobrados). Veja `.github/workflows/monitor.yml`.

Os alertas não custam nada e não precisam de servidor de e-mail: diante de um evento crítico (`SCHEMA_DRIFT` ou `RETRO_ALTER`), o workflow primeiro faz commit dos registros de proveniência e depois falha de propósito, e o GitHub envia um e-mail ao mantenedor sobre a execução que falhou. A verificação cruzada diária alerta da mesma forma quando a cobertura do portal cai abaixo de 90% ou quando divergências ficam sem reconciliação por mais de 7 h.

## Exemplo de saída PROV-DM

Quando uma alteração retroativa é detectada:

```json
{
  "@context": {
    "prov": "http://www.w3.org/ns/prov#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "5ltep": "https://5ltep.example.org/ontology#",
    "ckan": "https://ckan.org/schema#",
    "portal": "https://dadosabertos.ibama.gov.br/"
  },
  "@graph": [
    {
      "@id": "https://dadosabertos.ibama.gov.br/dataset/abc123#a1b2c3d4e5f6",
      "@type": ["prov:Entity", "5ltep:DatasetSnapshot"],
      "prov:wasGeneratedBy": {"@id": "5ltep:run-20260607T100000Z"},
      "prov:wasAttributedTo": {"@id": "https://dadosabertos.ibama.gov.br/organization/ibama"},
      "prov:wasDerivedFrom": {"@id": "https://dadosabertos.ibama.gov.br/dataset/abc123#f6e5d4c3b2a1"},
      "5ltep:changeType": "RETRO_ALTER",
      "5ltep:severity": "CRITICAL",
      "5ltep:contentHash": "a1b2c3d4e5f6...",
      "5ltep:detectedAt": {"@value": "2026-06-07T10:00:00+00:00", "@type": "xsd:dateTime"},
      "5ltep:changeSummary": "Description edited",
      "5ltep:changedFields": ["notes"],
      "5ltep:fieldsOutsideFingerprint": [],
      "5ltep:resourceUrlChanges": 0,
      "5ltep:hostMoves": 0,
      "5ltep:packagingChanges": 0
    },
    {
      "@id": "5ltep:run-20260607T100000Z",
      "@type": ["prov:Activity", "5ltep:MonitoringRun"],
      "prov:startedAtTime": {"@value": "2026-06-07T10:00:00+00:00", "@type": "xsd:dateTime"},
      "prov:endedAtTime": {"@value": "2026-06-07T10:00:02+00:00", "@type": "xsd:dateTime"},
      "prov:wasAssociatedWith": {"@id": "https://github.com/lsp3cesarschool/5ltep-layer4@abc1234"},
      "prov:used": {"@id": "https://dadosabertos.ibama.gov.br/api/3/action/package_show?id=abc123"}
    },
    {
      "@id": "https://github.com/lsp3cesarschool/5ltep-layer4@abc1234",
      "@type": ["prov:Agent", "prov:SoftwareAgent"],
      "rdfs:label": "5L-TEP Toolkit v1.0.2 (Layer 4 — Observability & Provenance)",
      "5ltep:repositoryUrl": "https://github.com/lsp3cesarschool/5ltep-layer4",
      "5ltep:commitSha": "abc1234567890"
    },
    {
      "@id": "https://dadosabertos.ibama.gov.br/organization/ibama",
      "@type": ["prov:Agent", "5ltep:DataCustodian"],
      "rdfs:label": "ibama",
      "5ltep:portalUrl": "https://dadosabertos.ibama.gov.br"
    }
  ]
}
```

## Estrutura do projeto

```
5ltep-layer4/
├── main.py                          # Orquestrador do pipeline da L4 (ponto de entrada)
├── requirements.txt                 # Dependências Python
├── LICENSE                          # Licença MIT
├── README.md                        # Este documento, em inglês
├── LEIAME.md                        # Este documento
├── changes.md                       # Registro legível das mudanças (gerado a cada ciclo)
├── compress_snapshots.py            # Compactação gzip semanal dos snapshots com mais de 90 dias
├── cross_check.py                   # Validador independente contra o portal CKAN ao vivo
├── .github/
│   └── workflows/
│       ├── monitor.yml              # Monitoramento agendado (a cada 6h)
│       ├── compress.yml             # Compactação semanal dos snapshots (dom 03:00 UTC)
│       ├── cross_check.yml          # Validação independente diária (03:30 UTC, fora do pico)
│       └── tests.yml                # Execução dos testes na CI/CD
├── src/
│   ├── __init__.py
│   ├── ckan_harvester.py            # Cliente da API do CKAN com novas tentativas
│   ├── hash_engine.py              # Impressões digitais SHA-256 e detecção de mudanças
│   ├── change_summary.py           # Detalhes das mudanças (campos, mudanças de servidor) + changes.md
│   └── prov_mapper.py              # ★ Gerador de JSON-LD W3C PROV-DM (núcleo da L4)
├── tests/
│   ├── __init__.py
│   └── test_toolkit.py             # 38 testes unitários e de integração
├── evaluation/                      # Scripts e resultados que reproduzem a avaliação do artigo
├── data/                            # Dados de execução (commit feito pelo bot)
│   ├── hash_store.json
│   ├── cross_check_report.json
│   └── snapshots/
│       ├── manifest.json
│       └── snapshot_*.json[.gz]
└── provenance_logs/                 # Logs JSON-LD PROV-DM (versionados no git)
    └── {dataset_id}.jsonld
```

## Configuração

| Variável de ambiente | Padrão | Descrição |
|---|---|---|
| `CKAN_PORTAL_URL` | `https://dadosabertos.ibama.gov.br` | Portal CKAN monitorado (no GitHub Actions: variável do repositório, veja abaixo) |
| `CKAN_ORG_FILTER` | _(vazio)_ | Filtra por organização |
| `MAX_DATASETS` | `0` (todos) | Limita a quantidade de conjuntos de dados coletados |
| `GITHUB_REPOSITORY` | `local` | Usada na identificação do agente de software |
| `GITHUB_SHA` | `local` | Usada na identificação do agente de software |

### Monitorando outro portal CKAN

O monitoramento contínuo (a cada 6 h, com e-mails de falha enviados pelo GitHub) e
a verificação cruzada diária leem o portal de um único lugar: a variável de
repositório `CKAN_PORTAL_URL`. Quando ela não está definida, monitoram o IBAMA.
Nenhuma mudança de código é necessária:

1. Faça um **fork** deste repositório.
2. No fork, vá em *Settings → Secrets and variables → Actions → Variables* e
   crie `CKAN_PORTAL_URL` com a URL raiz do portal
   (por exemplo, `https://dados.recife.pe.gov.br`).
3. **Comece com um histórico limpo:** apague as pastas `data/` e
   `provenance_logs/` inteiras e o arquivo `changes.md` herdados deste
   repositório, e faça commit. Eles são recriados automaticamente.
4. Habilite os workflows na aba **Actions** do fork (o GitHub desabilita workflows
   agendados em forks até que você faça isso). Os e-mails de falha vão para o dono
   do fork.
5. Opcionalmente, execute o *5L-TEP Layer 4 Monitoring Workflow* uma vez manualmente
   (*Actions → Run workflow*) para registrar a linha de base imediatamente, em vez de
   esperar o próximo horário de 6 horas. Até o primeiro ciclo, a verificação cruzada
   diária apenas informa que ainda não há nada para comparar.

Não mude o portal neste repositório: seu histórico de proveniência e o
[`changes.md`](changes.md) se referem ao IBAMA, e misturar portais os corromperia.
Para experimentar um portal uma única vez, sem o GitHub, execute
`python main.py --portal <url>` em uma cópia de trabalho separada.

## Avaliação

A avaliação relatada no artigo do WFA/WebMedia 2026 (conferência dos eventos
registrados contra a verdade de referência, injeção de falhas, interoperabilidade
com a biblioteca `prov`, estatísticas operacionais) pode ser reproduzida com os
scripts em [`evaluation/`](evaluation/).

## Referências acadêmicas

- Pinheiro, L. S., et al. (2026). *Towards Trust Engineering in Open Data Systems: A Layered Conceptual Framework Integrating Quality Assurance and Governance Perspectives*. SOFTENG 2026, IARIA, pp. 21–28.
- Pinheiro, L. S. & Sérgio, A. T. (2026). *5LTEP-L4: An Open-Source CKAN Toolkit for Provenance-Enabled Observability of Open Government Data*. XXV Workshop de Ferramentas e Aplicações (WFA), Anais Estendidos do WebMedia 2026, Lavras/MG, Brasil (no prelo).
- Moreau, L. & Missier, P. (Eds.) (2013). *PROV-DM: The PROV Data Model*. W3C Recommendation. https://www.w3.org/TR/prov-dm/
- Groth, P. & Moreau, L. (2013). *PROV-Overview*. https://www.w3.org/TR/prov-overview/
- Simmhan, Y. L. et al. (2005). *A survey of data provenance in e-science*. ACM SIGMOD Record.

## Licença

MIT — veja [LICENSE](LICENSE).
