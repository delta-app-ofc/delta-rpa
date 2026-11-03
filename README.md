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
 
1. **Extração** (`app/modules/extraction.py`)
   Lê as tabelas permitidas (`ALLOWED_TABLES`) do banco legado via `pandas.read_sql`, retornando um dicionário `{tabela: DataFrame}`.
2. **Validação** (`app/modules/validation.py`)
   Aplica regras de negócio configuradas em `RULES`, `UNIQUE_COLUMNS` e `FOREIGN_KEYS`, entre elas:
   - Idade mínima (ex.: usuário maior de 18 anos);
   - Valores permitidos em determinadas colunas (ex.: `tb_property.type` deve ser `CASA` ou `APARTAMENTO`);
   - Datas que devem representar o primeiro dia do mês (ex.: `tb_last_water_bill.month`);
   - Duplicidade de registros (restrições `UNIQUE`);
   - Integridade referencial (chaves estrangeiras) entre as tabelas já validadas.
   Registros inválidos são removidos do conjunto de dados e reportados; os registros válidos seguem para a próxima etapa.
3. **Transformação** (`app/modules/transformation.py`)
   Normaliza os dados válidos conforme regras em `TRANSFORMATIONS`, como:
   - Conversão de colunas para maiúsculas (ex.: `name`, `email`, `city`, `state`);
   - Substituição de valores (ex.: `APARTAMENTO` → `PRÉDIO` em `tb_property.type`);
   - Mapeamento pro id da tabela nova (ex.: `tb_property.classification` do legado, texto livre `RESIDENCIAL`/`COMERCIAL`, é convertido pro `classification_id` correspondente em `tb_property_classification` e a coluna é renomeada).
4. **Carga** (`app/modules/load.py`)
   Sincroniza o banco novo com o legado, respeitando a ordem de dependência das tabelas (`LOAD_PRIORITY`) e remapeando chaves estrangeiras (IDs antigos → novos):
   - **Mapa de IDs transacional**: `tb_rpa_state.id_map` guarda a relação `id_legado → id_novo` de cada tabela no PostgreSQL. O mapa é confirmado na mesma transação das inserções, atualizações e exclusões. `state/id_map.json` é uma cópia auxiliar (`app/modules/state.py`).
   - **Inserção x atualização (upsert real)**: registro do legado que ainda não está no mapa de ids é **inserido**; registro que já está é **atualizado** em todas as colunas, pelo `id` do banco novo. Tabelas com chave natural usam `INSERT ... ON CONFLICT DO UPDATE` como rede de segurança contra duplicatas.
   - **Replicação de exclusão**: todo id que estava no mapa de ids e não veio mais na extração foi apagado no legado e é apagado no banco novo, na ordem inversa de `LOAD_PRIORITY`. O RPA nunca apaga nada no banco legado.
   - Toda a carga, incluindo o mapa no banco, ocorre em uma única transação: falhas antes do commit provocam **rollback** dos registros e do estado. A cópia JSON é atualizada depois; uma falha nessa cópia gera aviso e a próxima execução recupera o mapa do PostgreSQL.
5. **Registro da execução**
   Cada execução grava uma linha na tabela `tb_log_rpa` do banco novo (`app/modules/execution_log.py`): início, fim, status, quantidade de registros inseridos/atualizados/excluídos e de erros de validação, e a mensagem de erro quando houver.
Cada etapa gera logs estruturados (`app/modules/logs.py`), tanto em console quanto em arquivo (`logs/rpa_AAAA-MM-DD.log`).
 
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
│       ├── transformation.py    # Regras de transformação/normalização
│       ├── load.py              # Carga no banco novo (upsert + exclusão + transação)
│       ├── state.py             # Mapa de ids persistido entre execuções
│       ├── execution_log.py     # Registro de cada execução em tb_log_rpa
│       └── logs.py              # Configuração e helpers de logging
├── tests/
│   ├── test_validation.py
│   ├── test_transformation.py
│   ├── test_load.py
│   └── test_state.py
├── test/
│   ├── init-legacy/             # Scripts SQL para popular o banco legado (testes)
│   └── init-new/                # Scripts SQL para popular o banco novo (testes)
├── state/                       # Cópia auxiliar do mapa de IDs — não versionada
├── logs/                        # Logs gerados em tempo de execução
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

O mapa de IDs autoritativo fica em `tb_rpa_state`, uma tabela técnica com uma linha JSONB. Na primeira execução, o RPA cria a tabela e importa o `state/id_map.json` existente. O usuário do banco precisa de permissão de criação de tabela nessa ativação e de leitura/escrita na tabela nas execuções seguintes. Caso a equipe provisione a tabela previamente, as permissões de leitura e escrita são suficientes para seu uso.

Um bloqueio transacional (`pg_advisory_xact_lock`) serializa as cargas do RPA no mesmo banco, impedindo que duas execuções carreguem um estado antigo ao mesmo tempo. O PostgreSQL libera esse bloqueio automaticamente no commit ou rollback.

Depois da primeira ativação, o arquivo local pode estar ausente, antigo ou inválido: o estado confirmado no banco continua sendo usado, sem tratar CEP como identificador único. O RPA só grava o mapa local como cópia auxiliar. Se existem execuções anteriores registradas, mas nem o estado no banco nem um mapa JSON recuperável estão disponíveis nessa primeira ativação, a carga é interrompida antes das inserções; restaure o mapa da execução anterior para continuar com segurança.

### Testes do estado transacional

Os testes opcionais de integração usam um PostgreSQL local descartável chamado `rpa_state_test`:

```powershell
$env:RPA_TEST_DATABASE_URL='postgresql+psycopg2://postgres:rpa_test_only@127.0.0.1:57619/rpa_state_test'
python -m pytest -q tests/test_database_state.py
```

Esses testes recriam apenas as tabelas do banco de teste indicado; o teste verifica explicitamente o host local e o nome `rpa_state_test`. Exercitam arquivo ausente, antigo ou corrompido, falha de disco após commit, rollback do mapa junto com os dados, importação do JSON antigo e serialização das cargas.
- [delta-handbook](https://github.com/delta-app-ofc/delta-handbook) — convenções de desenvolvimento e documentação das regras de negócio.
- [delta-sql-database](https://github.com/delta-app-ofc/delta-sql-database) — scripts do banco PostgreSQL normalizado.
