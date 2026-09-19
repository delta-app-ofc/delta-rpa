
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
   - **Mapa de ids persistido**: `state/id_map.json` guarda, entre execuções, a relação `id_legado → id_novo` de cada tabela (`app/modules/state.py`).
   - **Inserção x atualização (upsert real)**: registro do legado que ainda não está no mapa de ids é **inserido**; registro que já está é **atualizado** em todas as colunas, pelo `id` do banco novo. Tabelas com chave natural usam `INSERT ... ON CONFLICT DO UPDATE` como rede de segurança contra duplicatas.
   - **Replicação de exclusão**: todo id que estava no mapa de ids e não veio mais na extração foi apagado no legado e é apagado no banco novo, na ordem inversa de `LOAD_PRIORITY`. O RPA nunca apaga nada no banco legado.
   - Toda a carga (exclusões + inserções + atualizações) ocorre em uma única transação: em caso de falha, **rollback** completo e o mapa de ids não é regravado; em caso de sucesso, **commit** e o mapa de ids é atualizado.
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
├── state/                       # Mapa de ids (state/id_map.json) — estado local, não versionado
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
 
### Com Docker
 
```bash
docker build -t delta-rpa .
docker run --env-file .env -v $(pwd)/logs:/app/logs delta-rpa
```
 
## Testes
 
O projeto possui testes unitários (`tests/`) e um ambiente de teste completo via Docker Compose, que sobe dois bancos PostgreSQL (legado e novo, populados pelos scripts em `test/init-legacy` e `test/init-new`) e executa o RPA de ponta a ponta.
 
Testes unitários:
 
```bash
pip install -r requirements-dev.txt
pytest
```
 
Teste de integração (bancos + RPA via Docker):
 
```bash
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
```
 
Isso sobe:
- `legacy-db`: banco legado, na porta `5433`;
- `new-db`: banco novo, na porta `5434`;
- `rpa`: executa o pipeline completo contra os dois bancos acima, usando as variáveis definidas em `.env.test`.
## Logs
 
Cada execução gera um arquivo de log diário em `logs/rpa_AAAA-MM-DD.log`, contendo as informações de cada etapa do pipeline (extração, validação, transformação, carga, exclusão) e o resultado final (commit ou rollback).

Além do log em arquivo, cada execução grava uma linha na tabela `tb_log_rpa` do banco novo, com início, fim, status (`SUCCESS`/`ERROR`), quantidade de registros inseridos, atualizados e excluídos, quantidade de erros de validação e a mensagem de erro quando houver. O script de criação dessa tabela está em `test/init-new/01-schema.sql`.

O mapa de ids usado entre execuções fica em `state/id_map.json` (estado local, não versionado).