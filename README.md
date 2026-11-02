# Delta - RPA
 
RPA (Robotic Process Automation) responsável por orquestrar a **migração de dados entre o banco legado (Primeiro Ano) e o novo banco normalizado (Segundo Ano)**, garantindo a integridade dos dados e tratando falhas durante o processo de carga.
 
O projeto implementa um pipeline **ETL (Extract, Transform, Load)** com uma etapa adicional de **validação**, aplicando regras de negócio antes de mover os dados para o banco de destino.
 

## Visão geral
 
O `delta-rpa` conecta-se a dois bancos PostgreSQL:
 
- **Banco do Primeiro Ano** (`FIRST_YEAR_*`): base legada, de onde os dados são extraídos.
- **Banco do Segundo Ano** (`SECOND_YEAR_*`): base normalizada, para onde os dados válidos e transformados são carregados.
O processo é executado de ponta a ponta pelo script `app/main.py`, que orquestra as quatro etapas do pipeline (extração, validação, transformação e carga) e registra cada etapa em log.
 
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
 
```
delta-rpa/
├── app/
│   ├── main.py                  # Orquestra o pipeline ETL
│   ├── database/
│   │   └── connections.py       # Conexões com os dois bancos
│   └── modules/
│       ├── extraction.py        # Extração dos dados do banco legado
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
├── Dockerfile
├── docker-compose.test.yml      # Sobe bancos de teste + executa o RPA
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
├── .env.example
└── LICENSE
```
 
## Pré-requisitos
 
- Python 3.12+
- PostgreSQL (bancos legado e novo já provisionados) **ou** Docker + Docker Compose para o ambiente de testes
- pip
## Configuração
 
Copie o arquivo de exemplo e preencha as variáveis de ambiente:
 
```bash
cp .env.example .env
```
 
Variáveis disponíveis:
 
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
 
### Localmente
 
```bash
# criar e ativar o ambiente virtual
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
 
# instalar dependências
pip install -r requirements.txt
 
# configurar variáveis de ambiente
cp .env.example .env
# edite o .env com as credenciais dos bancos
 
# executar o RPA
python app/main.py
```
 
## Testes
 
O projeto possui testes unitários (`tests/`) e um ambiente Docker para integração, cujo uso está documentado no guia abaixo.
 
Testes unitários:
 
```bash
pip install -r requirements-dev.txt
pytest
```
 
Consulte [DOCKER-HELP.md](DOCKER-HELP.md) para usar o ambiente Docker local.

## Logs
 
Cada execução gera um arquivo de log diário em `logs/rpa_AAAA-MM-DD.log`, contendo as informações de cada etapa do pipeline (extração, validação, transformação, carga, exclusão) e o resultado final (commit ou rollback).

Além do log em arquivo, cada execução grava uma linha na tabela `tb_log_rpa` do banco novo, com início, fim, status (`SUCCESS`/`ERROR`), quantidade de registros inseridos, atualizados e excluídos, quantidade de erros de validação e a mensagem de erro quando houver. O script de criação dessa tabela está em `test/init-new/01-schema.sql`.

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
