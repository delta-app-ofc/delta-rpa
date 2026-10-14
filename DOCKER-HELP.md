# Docker — delta-rpa

## Objetivo

Executar o pipeline de migração contra os bancos de fixture locais.

## Pré-requisitos

Docker Engine em execução e Docker Compose v2. Para o ambiente de integração, o arquivo `.env.test` deve existir. Execute os comandos na raiz deste repositório. Os exemplos usam uma identificação de projeto própria para isolar containers e volumes.

## Executar

```bash
docker compose -p delta-rpa-test -f docker-compose.test.yml config --quiet
docker compose -p delta-rpa-test -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from rpa
# Consultar o resultado antes de remover os containers:
docker compose -p delta-rpa-test -f docker-compose.test.yml logs rpa
# Copiar logs para um diretório separado, se necessário:
docker compose -p delta-rpa-test -f docker-compose.test.yml cp rpa:/app/logs ./docker-test-logs
# Ao terminar:
docker compose -p delta-rpa-test -f docker-compose.test.yml down
```

## Conferir o resultado e encerrar

O arquivo `.env.test` precisa existir para as opções locais do runner. O Compose define as duas conexões com banco, usuário, senha, host e porta dos próprios serviços de teste; não use dados de produção.

Confira o código de saída do RPA, os registros migrados e o registro em `tb_log_rpa`. Os bancos ficam acessíveis no host em `127.0.0.1:5433` e `127.0.0.1:5434`. Logs e mapa de IDs persistem em volumes do projeto. O primeiro uso desses volumes começa sem o estado dos diretórios `logs/` e `state/` do host. Para repetir desde o início, confira e remova apenas os volumes desse projeto descartável; preserve os diretórios antigos.

Para diagnosticar falhas de um serviço Compose, use `docker compose -p <projeto> -f <arquivo> ps -a` e `docker compose -p <projeto> -f <arquivo> logs <serviço>`, com o mesmo projeto e arquivo da execução.

`down` preserva volumes nomeados. Só use `down -v` depois de conferir o nome do projeto e confirmar que seus dados são descartáveis. Não remova volumes de outros ambientes.

## Executar a imagem com configuração própria

Para usar bancos já provisionados, configure suas conexões em `.env` antes de executar a imagem. Esse fluxo é separado dos bancos de fixture do Compose. Os comandos abaixo usam Bash e preservam os logs no diretório do host.

```bash
docker build -t delta-rpa .
docker run --env-file .env -v "$(pwd)/logs:/app/logs" delta-rpa
```

Sem um volume para `/app/state`, o mapa de IDs fica associado ao container dessa execução. Para ciclos repetidos, planeje a persistência do estado junto com os bancos usados.
