 Liberação Escolar

Sistema web para gerenciamento de agendas e autorizações de liberação de alunos em **uma única instituição de ensino**. O responsável autenticado consulta a programação escolar efetiva do aluno e pode autorizar a liberação **a partir do início de uma atividade**, corrigir o horário ou cancelar a autorização. A administração organiza alunos, turmas, matrículas, vínculos, grades e eventos, consulta as liberações e acompanha o histórico auditável.

**Status:** MVP funcional em finalização, com validação local dos fluxos principais. **Deploy público ainda não configurado.** O desenvolvimento adotou TDD nas etapas anteriores; a priorização atual é estabilização, interface e entrega.

> **Uso de demonstração:** utilize apenas dados fictícios. Uma implantação com dados reais de estudantes exige revisão de segurança, conformidade com a LGPD, políticas de acesso, backup e operação.

## Tecnologias

| Camada | Tecnologia |
| --- | --- |
| Frontend | Next.js, React, TypeScript e CSS global |
| Backend | FastAPI, Python, SQLAlchemy 2.x e Pydantic |
| Banco de dados | PostgreSQL |
| Migrações | Alembic |
| Ambiente local | Docker Compose, `uv`, Node.js e npm |
| Testes | Pytest, Vitest e Testing Library |

## Funcionalidades do MVP

### Administração

- Autenticação com perfil administrativo.
- Cadastro e gerenciamento de alunos, turmas, anos letivos e matrículas.
- Cadastro e gestão de vínculos entre responsáveis e alunos, incluindo revogação.
- Importação de **grades semanais por turma via CSV**, com vigência e horário de término.
- Cadastro de eventos escolares informativos e eventos de substituição parcial ou integral da programação.
- Consulta da agenda efetiva de uma turma em uma data.
- Consulta de liberações por turma e data, com filtros por estado e pesquisa por aluno/matrícula.
- Visualização do **horário de liberação autorizado** e do histórico de alterações.
- Correção administrativa com motivo registrado e auditoria.

### Responsáveis

- Autenticação e acesso apenas aos alunos com vínculo vigente.
- Consulta da agenda escolar efetiva do aluno, incluindo aulas, intervalos e eventos substitutivos; avisos informativos aparecem separadamente.
- Autorização de liberação **somente para a data escolar atual**, a partir de um horário válido da programação efetiva.
- Correção do horário de liberação e cancelamento da autorização, com registro de histórico.
- Consulta da situação atual da liberação, incluindo o horário autorizado quando aplicável.

### Regras importantes

- A data escolar é calculada no fuso definido por `SCHOOL_TIMEZONE`, sem depender do fuso da máquina.
- Horários permitidos são derivados do início de atividades efetivas elegíveis; intervalos não são opções de liberação.
- Aplicam-se os limites definidos para os turnos e as regras de vínculo e matrícula vigentes.
- Uma liberação é identificada por **aluno + data**; alterações de estado ou horário são auditadas.
- Acesso e alterações são restritos ao perfil autenticado.

## Estrutura do projeto

```text
.
├── backend/
│   ├── app/
│   │   ├── api/          # Endpoints e dependências
│   │   ├── domain/       # Regras de negócio
│   │   ├── models/       # Modelos SQLAlchemy
│   │   ├── schemas/      # Contratos Pydantic
│   │   └── services/     # Consultas e orquestração
│   ├── migrations/       # Migrações Alembic
│   └── tests/
├── frontend/
│   └── src/
│       ├── app/          # Rotas Next.js
│       ├── components/   # Componentes de interface
│       └── lib/          # Clientes HTTP e utilitários
├── .github/workflows/ci.yml
└── docker-compose.yml
```

> A representação destaca os diretórios relevantes; arquivos de configuração adicionais podem existir no repositório.

## Pré-requisitos

- Docker e Docker Compose (para PostgreSQL local).
- [`uv`](https://docs.astral.sh/uv/) e Python compatível com o `pyproject.toml` do backend (o projeto foi iniciado com Python 3.12+).
- Node.js 22+ e npm.

## Configuração inicial

Na raiz do repositório:

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

Revise as variáveis dos três arquivos para seu ambiente. Utilize credenciais diferentes das de exemplo e não versione arquivos `.env`.

Pontos a conferir:

- `DATABASE_URL`: banco de desenvolvimento usado pelo FastAPI e Alembic.
- `TEST_DATABASE_URL`: banco isolado para testes, terminando em `_test`.
- `SECRET_KEY`: chave secreta com pelo menos 32 caracteres.
- `SCHOOL_TIMEZONE`: fuso oficial da escola.
- `COOKIE_SECURE=false`: apenas em desenvolvimento local sem HTTPS.
- Endereço da API utilizado pelo frontend: mantenha o nome da variável conforme a implementação de `frontend/src/lib/api.ts` e o arquivo `frontend/.env.example`.

Gere uma chave para desenvolvimento com:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**Atenção:** a configuração de autenticação utiliza cookie de sessão HttpOnly e token CSRF. Em produção, revise `Secure`, domínio, política `SameSite`, CORS, proxy e HTTPS; não replique automaticamente os parâmetros de desenvolvimento.

## Execução local

### 1. Subir o PostgreSQL

Na raiz do projeto:

```bash
docker compose up -d db
docker compose ps
```

Na primeira criação do volume, a configuração local prevê dois bancos isolados:

- `liberacao_dev`: desenvolvimento;
- `liberacao_test`: testes.

**Cuidado:** `docker compose down -v` **remove os volumes e seus dados**. Utilize apenas quando quiser reinicializar intencionalmente um ambiente descartável.

### 2. Iniciar o backend

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Por padrão, o backend local é acessado em:

- API: <http://localhost:8000>
- Documentação interativa: <http://localhost:8000/docs>
- Health check, se disponível na aplicação: <http://localhost:8000/health>

Confirme que `DATABASE_URL` aponta para `liberacao_dev` **antes** de executar as migrations.

### 3. Iniciar o frontend

Em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

Interface: <http://localhost:3000>

O backend precisa estar acessível no endereço configurado no cliente HTTP do frontend.

## Principais fluxos de utilização

1. Entrar como administrador e cadastrar ano letivo, turma e aluno.
2. Matricular o aluno na turma e vincular um responsável.
3. Importar a grade semanal CSV, definindo vigência e horário final.
4. Cadastrar eventos informativos ou substitutivos, caso necessário.
5. Entrar como responsável e consultar a agenda efetiva do aluno.
6. Selecionar o início de uma atividade e registrar a liberação do dia.
7. Corrigir o horário ou cancelar a autorização, se necessário.
8. Voltar ao painel administrativo para consultar estado, horário autorizado e histórico.

### Endpoints de referência

| Método | Endpoint | Uso |
| --- | --- | --- |
| `POST` | `/auth/login` | Autenticação e obtenção do token CSRF |
| `GET` | `/auth/me` | Sessão atual |
| `POST` | `/auth/logout` | Encerramento da sessão |
| `GET` | `/responsavel/liberacoes/hoje` | Situação atual dos alunos vinculados |
| `POST` | `/responsavel/alunos/{aluno_id}/liberacao` | Liberar, corrigir ou cancelar |
| `GET` | `/responsavel/agenda/alunos/{aluno_id}/agenda-efetiva?data=AAAA-MM-DD` | Agenda efetiva do aluno |
| `GET` | `/admin/liberacoes?turma_id=1&data=AAAA-MM-DD` | Consulta administrativa |
| `GET` | `/admin/alunos/{aluno_id}/liberacoes/historico` | Histórico de liberação |
| `GET` | `/admin/turmas/{turma_id}/agenda?data=AAAA-MM-DD` | Agenda efetiva da turma |

A especificação completa e os parâmetros dos endpoints estão disponíveis em `/docs` com o backend executando. Os endpoints autenticados exigem a sessão adequada; operações que alteram estado também exigem `X-CSRF-Token`.

## Domínio e persistência

As regras centrais ficam em `backend/app/domain/`, separadas dos detalhes de infraestrutura:

| Módulo | Responsabilidade |
| --- | --- |
| `relogio.py` | Relógio injetável, data oficial e fuso da escola |
| `turno.py` | Limites de operação por turno (13h e 19h, exclusivos, conforme regra implementada) |
| `vinculo.py` | Validade e revogação dos vínculos |
| `estados.py` | Estados, ações e transições de liberação |
| `avaliacao.py` | Avaliação de data, vínculo, turno e transição |

Serviços adicionais consolidam as aulas recorrentes e os eventos especiais na **agenda efetiva**, consultam a situação dos alunos e validam horários elegíveis de liberação.

No banco:

- `UNIQUE (aluno_id, data)` impede duas liberações distintas para o mesmo aluno e dia.
- Restrições de vínculo e matrícula preservam a consistência relacional.
- As tabelas de histórico e auditoria foram projetadas como **append-only**, com proteção por triggers contra alterações ou exclusões.
- A tabela `liberacoes` armazena `horario_inicio_liberacao`.
- O histórico registra `horario_anterior` e `horario_novo`, permitindo auditar correções de horário mesmo quando o estado continua `LIBERADO`.

## Migrações

Os modelos SQLAlchemy estão em `backend/app/models/` e as migrações Alembic em `backend/migrations/`.

```bash
cd backend
uv run alembic current
uv run alembic heads
uv run alembic upgrade head
uv run alembic check
```

`current` deve alcançar a revisão indicada por `heads`. Execute `upgrade head` apenas no banco pretendido. **Não execute `downgrade base` em bancos com dados que devam ser preservados.**

## Testes e qualidade

### Backend

```bash
cd backend
uv run pytest -m "not integration"
uv run pytest
uv run ruff check .
```

Para testes específicos, conforme a estrutura existente:

```bash
uv run pytest tests/unit/domain -q
uv run pytest tests/integration -q
```

A suíte de integração utiliza `TEST_DATABASE_URL` e foi configurada para recusar bancos cujo nome não termine em `_test`. Os testes podem recriar schemas: utilize apenas o banco de testes descartável.

### Frontend

```bash
cd frontend
npx tsc --noEmit
npx vitest run
npm run lint
npm run build
```

> Os testes automatizados foram utilizados durante o desenvolvimento por TDD. Na fase final do MVP, a prioridade é corrigir regressões e validar o fluxo completo antes da demonstração.

### Integração contínua

O workflow `.github/workflows/ci.yml` foi concebido para executar verificações do backend com PostgreSQL de serviço e validações de lint, tipos, testes e build do frontend. Confira o resultado do workflow no GitHub antes de criar a tag de entrega.

## Autenticação e segurança

- Perfis: **ADMIN** e **RESPONSAVEL**.
- Sessão mantida no servidor, com cookie `sessao` (`HttpOnly`, `SameSite=Lax` e `Secure` conforme ambiente).
- Apenas o **hash do token de sessão** é armazenado no banco.
- Operações autenticadas que alteram estado exigem o cabeçalho `X-CSRF-Token`.
- Sessão de até 8 horas e expiração por inatividade após 30 minutos (configuráveis).
- Proteção contra tentativas repetidas de login, incluindo bloqueio temporário e resposta HTTP 429.
- Auditoria de operações relevantes sem armazenamento de senhas ou tokens em claro.
- O responsável só pode consultar e alterar registros de alunos com vínculo vigente.

Antes de qualquer uso real, reavalie proteção de dados pessoais, retenção de logs, backups, política de senhas, gestão de segredos e privilégios administrativos.

## Possível deploy gratuito (ainda não configurado)

Para demonstração remota, a arquitetura considerada é:

| Camada | Plataforma candidata |
| --- | --- |
| Frontend Next.js | Vercel |
| API FastAPI | Render |
| PostgreSQL | Neon |

Essa é **uma proposta de implantação**, não uma infraestrutura já provisionada. Verifique as cotas, políticas de uso e disponibilidade dos planos gratuitos antes de publicar. Serviços gratuitos podem suspender por inatividade, e condições comerciais podem mudar.

Uma implantação precisa contemplar, nesta ordem:

1. Criar um PostgreSQL de demonstração e configurar o acesso seguro.
2. Configurar o backend e aplicar as migrações no banco correto.
3. Publicar o frontend com a URL da API configurada.
4. Ajustar proxy, cookies de sessão, CSRF, CORS e HTTPS para a origem pública.
5. Validar login, agenda, liberação, cancelamento e consulta administrativa com **dados fictícios**.

**Não publique** arquivos `.env`, banco de testes ou credenciais em um repositório público.

## Checklist de entrega do MVP

- [ ] Banco local inicializa e as migrations estão atualizadas.
- [ ] Backend inicia sem exceções e apresenta `/docs`.
- [ ] Frontend passa em `npx tsc --noEmit` e `npm run build`.
- [ ] Administrador cadastra aluno, matrícula, turma e vínculo.
- [ ] Grade CSV e eventos aparecem corretamente na agenda efetiva.
- [ ] Responsável consulta apenas alunos vinculados.
- [ ] Liberação por horário, correção e cancelamento funcionam.
- [ ] Painel administrativo exibe horário autorizado e histórico.
- [ ] Dados persistem após reinicialização dos serviços.
- [ ] Variáveis sensíveis estão fora do Git.
- [ ] Dados de demonstração não contêm informações reais de estudantes.

## Convenções

- Preservar separação entre domínio, serviços, API e interface.
- Utilizar o fuso da escola configurado explicitamente.
- Manter dados fictícios nos ambientes de desenvolvimento, testes e demonstração pública.
- Manter segredos em variáveis de ambiente não versionadas.
- Registrar alterações relevantes de liberação em histórico auditável.
