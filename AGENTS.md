# AGENTS.md — Contexto do repositório `delta-rpa`

Este arquivo orienta agentes de IA e pessoas desenvolvedoras que atuem no `delta-rpa`. Antes de alterar qualquer arquivo, confirme o estado da branch, leia as instruções locais e inspecione a implementação disponível. Não transforme intenções descritas na documentação em funcionalidades supostamente existentes.

## 1. Visão geral do Projeto Delta

O Projeto Delta é uma plataforma acadêmica de monitoramento inteligente do consumo de água residencial. Dispositivos IoT instalados em hidrômetros coletam pulsos para que a solução consolide consumo, detecte vazamentos, estime gastos e apresente informações por aplicações web e mobile, além de um chatbot.

A organização `delta-app-ofc` mantém repositórios Git independentes para documentação, bancos de dados e demais partes da solução. PostgreSQL é destinado aos dados cadastrais e transacionais, enquanto MongoDB atende telemetria e dados de maior volume. Redis e Neo4j são citados na documentação de arquitetura como planejados; não presuma que seus repositórios, integrações ou scripts existam neste workspace.

## 2. Contexto deste repositório

O `delta-rpa` foi criado para armazenar a integração RPA responsável por orquestrar a movimentação de dados entre um banco legado e um novo banco normalizado, preservando a integridade dos dados e tratando falhas de carga. Essa finalidade está registrada no `README.md`.

No estado atual, o repositório ainda não contém código-fonte de RPA, manifesto de dependências, testes automatizados, configuração de contêiner ou definição dos bancos de origem e destino. Portanto, não escolha linguagem, framework de RPA, driver, esquema, credencial, estratégia de carga ou mecanismo de recuperação sem que uma tarefa e os artefatos oficiais do projeto os definam.

As tecnologias efetivamente presentes são Markdown e YAML para GitHub Actions. O workflow atual apenas chama a automação centralizada da organização para validar Pull Requests; ele não executa a integração RPA nem comprova seu funcionamento.

### Estrutura atual

```text
.
├── .github/
│   └── workflows/
│       └── trigger_actions.yml
├── .gitignore
├── AGENTS.md
├── LICENSE
└── README.md
```

Responsabilidades dos arquivos:

- `README.md`: registra o objetivo inicial da integração RPA.
- `.github/workflows/trigger_actions.yml`: em Pull Requests abertos ou editados, reutiliza o workflow `delta-app-ofc/.github/.github/workflows/main.yml@main` para as verificações organizacionais.
- `.gitignore`: exclui configurações locais de IDE, arquivo `.env` e cache de Python do versionamento.
- `LICENSE`: contém a licença do repositório.
- `AGENTS.md`: reúne as instruções de contexto e atuação para este repositório.

## 3. Leitura obrigatória do `TASK.md`

Antes de executar qualquer tarefa, leia integralmente o arquivo `TASK.md` da raiz deste repositório, quando ele estiver presente. Seus critérios de aceite, limites e ordem de execução fazem parte obrigatória do escopo.

Não crie, copie ou improvise um `TASK.md`. Se ele não existir, trabalhe somente a partir da tarefa fornecida explicitamente e solicite esclarecimento quando não for possível determinar o escopo com segurança.

## 4. Padrão de branches e commits

Siga as convenções definidas em `delta-handbook/DEVOPS/convencoes-desenvolvimento.md`.

O nome de uma branch deve seguir:

```text
<tipo>/<descricao-da-alteracao>
```

Tipos permitidos:

| Tipo | Uso |
| --- | --- |
| `feat` | Nova funcionalidade |
| `fix` | Correção de bug |
| `refactor` | Refatoração |
| `docs` | Alteração de documentação |
| `test` | Criação ou manutenção de testes |
| `style` | Alteração de estilização |

Use uma descrição curta e identificável, como `docs/agents-md`. Crie a branch dentro do próprio repositório `delta-rpa`, sempre a partir da `main` atualizada. Não inicialize Git na pasta que apenas agrupa os repositórios locais do Delta.

Os commits seguem Conventional Commits no formato `<tipo>: descrição`, usando os mesmos tipos permitidos para branches. Mantenha cada commit objetivo, de escopo coeso e com uma mensagem que descreva a alteração realizada.

## 5. Padrão de documentação

Ao criar ou atualizar arquivos Markdown, acompanhe o padrão observado no `delta-handbook`:

- comece com um título principal claro usando `#`;
- apresente objetivo e contexto antes dos detalhes operacionais;
- organize o conteúdo em seções `##` e subseções `###`, em ordem lógica;
- use listas para responsabilidades, regras e etapas;
- use tabelas quando houver comparação ou mapeamento de informações;
- destaque nomes de arquivos, caminhos, branches, comandos e identificadores com crases;
- identifique a linguagem em blocos de código, como `text`, `yaml`, `python` ou `markdown`;
- use separadores horizontais apenas quando ajudarem a dividir blocos extensos;
- escreva em português claro, objetivo e tecnicamente correto;
- mantenha exemplos e descrições alinhados aos arquivos e comportamentos reais;
- diferencie explicitamente o que já foi implementado do que está planejado ou depende de decisão futura;
- atualize referências relacionadas quando uma alteração tornar a documentação anterior incorreta.

## 6. Limites de atuação

- Não invente ferramenta de RPA, linguagem, biblioteca, banco, tabela, fluxo de carga ou infraestrutura ainda não registrada em artefatos oficiais.
- Não suponha a estrutura interna de outros repositórios do Projeto Delta.
- Não trate o workflow de validação de PR como teste da integração RPA.
- Não crie o `TASK.md` nem amplie uma tarefa além de seus critérios de aceite.
- Não versione `.env`, credenciais, tokens, strings de conexão ou outros segredos.
- Restrinja alterações aos arquivos e ao repositório definidos pela tarefa.
- Antes de implementar a futura movimentação de dados, valide os contratos oficiais de origem e destino, as regras de integridade e o comportamento esperado diante de falhas.

## 7. Aviso de manutenção

A seção **Estrutura atual** será revisada e atualizada periodicamente nesta conversa após commits oficiais que alterem a organização do repositório. Antes de confiar nela, compare-a com os arquivos presentes na branch em uso e preserve somente informações verificáveis.
