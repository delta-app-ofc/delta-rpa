
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
   - Substituição de valores (ex.: `APARTAMENTO` → `PRÉDIO` em `tb_property.type`).
4. **Carga** (`app/modules/load.py`)
   Insere os dados transformados no banco novo, respeitando a ordem de dependência das tabelas (`LOAD_PRIORITY`), remapeando chaves estrangeiras (IDs antigos → novos) e utilizando `INSERT ... ON CONFLICT DO UPDATE` para tabelas com restrições de unicidade. Toda a carga ocorre dentro de uma única transação: em caso de falha, é feito **rollback** completo; em caso de sucesso, **commit**.
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
│       ├── load.py               # Carga no banco novo com controle transacional
│       └── logs.py               # Configuração e helpers de logging
├── tests/
│   ├── test_validation.py
│   └── test_transformation.py
├── test/
│   ├── init-legacy/             # Scripts SQL para popular o banco legado (testes)
│   └── init-new/                # Scripts SQL para popular o banco novo (testes)
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
 
Cada execução gera um arquivo de log diário em `logs/rpa_AAAA-MM-DD.log`, contendo as informações de cada etapa do pipeline (extração, validação, transformação, carga) e o resultado final (commit ou rollback).