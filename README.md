# Delta · RPA de migração PostgreSQL

![Python](https://img.shields.io/badge/Python-3.12-3776ab?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-origem%20e%20destino-356ce0?logo=postgresql&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-ETL-150458?logo=pandas&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-conexões-9dbdff)
![Docker](https://img.shields.io/badge/Docker-testes%20de%20integração-2496ed?logo=docker&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-testes%20unitários-0a9edc?logo=pytest&logoColor=white)

`delta-rpa` migra dados do banco legado do Primeiro Ano para o banco normalizado do Segundo Ano. O pipeline ETL extrai, valida, transforma e carrega os registros, mantendo as chaves relacionadas e registrando cada execução.

**Tags:** `rpa` · `etl` · `migração-de-dados` · `postgresql` · `python` · `pandas` · `sqlalchemy` · `docker-compose`

## Sumário

- [Visão geral](#visão-geral)
- [Como funciona o pipeline](#como-funciona-o-pipeline)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Pré-requisitos](#pré-requisitos)
- [Configuração](#configuração)
- [Como executar](#como-executar)
- [Testes](#testes)
- [Automação no GitHub](#automação-no-github)
- [Logs](#logs)
- [Referências relacionadas](#referências-relacionadas)

## Visão geral

| Aspecto | Implementação neste repositório |
|---|---|
| Origem e destino | Dois bancos PostgreSQL: base legada do Primeiro Ano e base normalizada do Segundo Ano. |
| Fluxo | Extração → validação → transformação → carga, orquestradas por `app/main.py`. |
| Integridade | Regras de idade, valores permitidos, unicidade e chaves estrangeiras antes da carga. |
| Sincronização | Remapeamento de IDs, inserções, atualizações e exclusões no destino dentro de uma transação. |
| Estado e auditoria | Mapa de IDs entre execuções, logs locais e registro em `tb_log_rpa` no banco novo. |
| Ambiente de teste | Compose com PostgreSQL 16 e dados de fixture; instruções em [`DOCKER-HELP.md`](DOCKER-HELP.md). |

O RPA conecta-se ao banco legado pelas variáveis `FIRST_YEAR_*` e ao banco novo pelas variáveis `SECOND_YEAR_*`. O script `app/main.py` orquestra as etapas e registra seus resultados.

## Como funciona o pipeline

1. **Extração** (`app/modules/extraction.py`): lê as tabelas permitidas em `ALLOWED_TABLES` com `pandas.read_sql` e retorna um dicionário de DataFrames.
2. **Validação** (`app/modules/validation.py`): aplica as regras definidas em `RULES`, `UNIQUE_COLUMNS` e `FOREIGN_KEYS`, como idade mínima, valores permitidos, datas mensais, unicidade e integridade referencial. Registros válidos seguem para a transformação; os demais são reportados.
3. **Transformação** (`app/modules/transformation.py`): normaliza dados conforme `TRANSFORMATIONS`, incluindo conversão para maiúsculas, substituição de valores e mapeamento de IDs do esquema novo.
4. **Carga** (`app/modules/load.py`): processa tabelas conforme `LOAD_PRIORITY`, remapeia chaves estrangeiras e sincroniza inserções, atualizações e exclusões no destino.
   - `state/id_map.json` mantém a relação entre IDs antigos e novos.
   - Registros existentes são atualizados; novos registros são inseridos.
   - IDs removidos da origem são excluídos do destino, em ordem inversa de dependência.
   - A carga usa uma transação: sucesso confirma as alterações e atualiza o mapa de IDs; falha executa rollback.
5. **Registro da execução** (`app/modules/execution_log.py`): grava em `tb_log_rpa` o início, o fim, o status, as quantidades processadas, os erros de validação e a mensagem de erro, quando houver.

Cada etapa também gera logs estruturados no console e em `logs/rpa_AAAA-MM-DD.log`.

## Estrutura do projeto

```text
delta-rpa/
├── .github/
│   └── workflows/
│       ├── rpa.yml              # Execução agendada ou manual do pipeline
│       └── trigger_actions.yml  # Verificações organizacionais de Pull Request
├── app/
│   ├── main.py                  # Orquestra o pipeline ETL
│   ├── database/connections.py  # Conexões com os dois bancos
│   └── modules/
│       ├── extraction.py        # Extração do banco legado
│       ├── validation.py        # Regras de validação e integridade
│       ├── transformation.py    # Transformação e normalização
│       ├── load.py              # Carga no banco novo
│       ├── state.py             # Mapa de IDs entre execuções
│       ├── execution_log.py     # Registro em tb_log_rpa
│       └── logs.py              # Configuração de logging
├── tests/                       # Testes unitários
├── test/                        # Scripts SQL para os bancos de teste
├── Dockerfile
├── docker-compose.test.yml
├── DOCKER-HELP.md               # Guia do ambiente de integração
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

## Pré-requisitos

- Python 3.12+
- PostgreSQL para os bancos legado e novo, ou Docker e Docker Compose para o ambiente de teste
- pip

## Configuração

Copie o arquivo de exemplo e preencha as variáveis de conexão:

```bash
cp .env.example .env
```

| Variável | Descrição |
|---|---|
| `FIRST_YEAR_DB_HOST` | Host do banco legado |
| `FIRST_YEAR_DB_PORT` | Porta do banco legado |
| `FIRST_YEAR_DB_NAME` | Nome do banco legado |
| `FIRST_YEAR_DB_USER` | Usuário do banco legado |
| `FIRST_YEAR_DB_PASSWORD` | Senha do banco legado |
| `SECOND_YEAR_DB_HOST` | Host do banco novo |
| `SECOND_YEAR_DB_PORT` | Porta do banco novo |
| `SECOND_YEAR_DB_NAME` | Nome do banco novo |
| `SECOND_YEAR_DB_USER` | Usuário do banco novo |
| `SECOND_YEAR_DB_PASSWORD` | Senha do banco novo |
| `BATCH_SIZE` | Tamanho de lote utilizado pelo RPA |

## Como executar

Crie um ambiente virtual, instale as dependências e inicie a migração:

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app/main.py
```

## Testes

Os testes unitários ficam em `tests/`. Para instalá-los e executá-los:

```bash
pip install -r requirements-dev.txt
pytest
```

Para a integração com PostgreSQL em Docker, siga [`DOCKER-HELP.md`](DOCKER-HELP.md).

## Automação no GitHub

- `.github/workflows/rpa.yml` executa `python app/main.py` diariamente ou por acionamento manual. Configure os secrets `FIRST_YEAR_DB_*` e `SECOND_YEAR_DB_*`, além de `BATCH_SIZE`, para os bancos de destino autorizados.
- `.github/workflows/trigger_actions.yml` chama as verificações organizacionais de Pull Request.

## Logs

Cada execução gera um arquivo diário `logs/rpa_AAAA-MM-DD.log` com os registros das etapas e o resultado da transação. A tabela `tb_log_rpa` armazena status (`SUCCESS`/`ERROR`), quantidades inseridas, atualizadas e excluídas, erros de validação e mensagens de erro. O esquema dessa tabela está em `test/init-new/01-schema.sql`.

O mapa de IDs entre execuções fica em `state/id_map.json`, mantido localmente.

## Referências relacionadas

- [delta-handbook](https://github.com/delta-app-ofc/delta-handbook) — convenções de desenvolvimento e documentação das regras de negócio.
- [delta-sql-database](https://github.com/delta-app-ofc/delta-sql-database) — scripts do banco PostgreSQL normalizado.
