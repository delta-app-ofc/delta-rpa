# CI técnico

Em pull requests e na execução manual, o workflow instala as dependências de desenvolvimento com Python 3.12, executa `pytest` e roda o pipeline contra os dois bancos PostgreSQL de fixture do Compose. Ao terminar, remove os containers e volumes descartáveis do projeto `delta-rpa-ci`.

Para executar localmente na raiz do repositório:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
docker compose -p delta-rpa-ci -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from rpa
docker compose -p delta-rpa-ci -f docker-compose.test.yml down -v
```

O Compose usa somente os dados e credenciais de teste do repositório. A execução verifica o código de saída do pipeline; não compara automaticamente os registros migrados com resultados esperados. Os testes unitários usam conexões simuladas onde aplicável. Essas verificações não comprovam o funcionamento com bancos de produção.
