# Konstantin Borisov
Desenvolvedor de Software — Fullstack / Backend / Frontend

Email: vestek70@gmail.com
Localização: Florianópolis, SC, Brasil (aberto a remoto)
GitHub: github.com/vestek70

## Resumo
Desenvolvedor de software que aprende construindo produto de verdade. Coloquei um
SaaS no ar do zero à produção (React + Supabase/PostgreSQL + Stripe), com assinantes
pagantes reais, e cuido dele ponta a ponta: front-end, API, banco de dados,
pagamentos e segurança. Trabalho num fluxo apoiado por IA (Claude Code, Kilo Code)
para implementar e depurar mais rápido, mas as decisões de arquitetura, a revisão e a
validação de cada mudança antes do deploy são minhas. Já lidei com o que dá trabalho
de verdade: bugs de cobrança em produção, correção de falhas de segurança (RLS, IDOR,
price tampering) e testes automatizados. Confortável tanto no back-end (Postgres,
APIs, autenticação) quanto no front-end (React, JavaScript, PWA), e me adapto rápido a
novas linguagens e ferramentas.

## Projetos

### Plataforma Albina Borisova — albinaborisova.com.br
SaaS educacional completo para imigrantes russófonos no Brasil (adultos e crianças):
simuladores de exames oficiais (CELPE-Bras, ENCCEJA), guias interativos, jogos para
crianças e assistente de IA para situações do dia a dia (documentos, saúde, moradia).
Do zero à produção, com assinaturas pagantes ativas. Desenvolvido em fluxo AI-augmented
(Claude Code, Kilo Code) — eu defino arquitetura, prompts, reviso e valido cada mudança
antes do deploy.

**Arquitetura:**
- Front-end React/Vite (PWA com service worker), múltiplos fluxos (adultos, crianças,
  emergência/SOS, assistente de IA, perfil/planos)
- Back-end Supabase: PostgreSQL com Row Level Security, Edge Functions (Deno/TypeScript)
- Autenticação via Google Sign-In (Firebase Auth)
- Deploy contínuo na Vercel

**Pagamentos (Stripe):**
- Assinatura recorrente + créditos avulsos + Pix, com webhooks
  (`checkout.session.completed`, `invoice.payment_succeeded`,
  `customer.subscription.deleted/updated`) e idempotência nos checkouts
- Depuração de bugs reais de billing em produção: perda de dias no upgrade, créditos
  não creditados na renovação, drift de data de expiração — corrigidos e cobertos
  por 22 testes unitários

**Segurança:**
- Row Level Security em todas as tabelas sensíveis; funções RPC que ocultam dados
  restritos (ex.: gabarito de provas) até checagem de plano do usuário
- Correção de vulnerabilidade IDOR (usuário não conseguia mais forjar checkout em
  nome de outro usuário) e de price tampering (preço sempre recalculado no servidor)
- Rate limiting / proteção contra burst nas chamadas de IA
- Verificação de JWT via Supabase Auth (substituiu decodificação insegura anterior)

**IA / RAG:**
- Assistente com RAG próprio: busca full-text no Postgres + matching por Levenshtein
  para ligar perguntas ao conteúdo certo
- Correção automática de redações (CELPE-Bras/ENCCEJA) calibrada aos critérios
  oficiais do INEP, com validação server-side das notas geradas pela IA

**Testes e infraestrutura:**
- E2E com Playwright (fluxos free-tier e paid-tier) e CI/CD via GitHub Actions
- Correções de SEO/prerendering (integridade de hashes de assets, 404 reais,
  liberação controlada de crawlers de IA)
- Conformidade com a LGPD: retenção de dados, transferência internacional,
  proteção de menores (ECA Digital)

### SkillMatch Web — github.com/vestek70/skillmatch
SPA em JavaScript puro (sem frameworks/bundlers) que ajuda RH e candidatos a comparar
o perfil de habilidades de um candidato com os requisitos de vagas de tecnologia
(foco Front-End), classificando o nível de compatibilidade (Alta/Média/Baixa) e
destacando habilidades encontradas e faltantes por vaga. Projeto de estudo que
evoluiu de um script de console para uma aplicação web completa.
- HTML5 semântico e CSS3 com Flexbox (layout responsivo, mobile-first)
- JavaScript Vanilla em ES Modules (`import`/`export`), Programação Orientada a
  Objetos (classes, herança), métodos de array (`map`/`filter`/`reduce`)
- Assíncrono: Closures, Promises, `async/await` e `fetch` para consumo de catálogo
  de vagas (JSON)
- Manipulação dinâmica de DOM e persistência do perfil do candidato com `localStorage`
- Versionamento com Git/GitHub (GitFlow) e organização com Kanban (Trello)
- Auditoria Lighthouse: 100/100/100/100 em Performance, Acessibilidade, Boas
  Práticas e SEO

## Habilidades técnicas
Desenvolvimento fullstack em fluxo AI-augmented — ferramentas agênticas de IA
(Claude Code, Kilo Code com orquestração multi-agente) para implementação, mantendo
decisões de arquitetura, revisão e validação sob meu controle. Experiência prática com:
- Front-end: HTML, CSS, JavaScript (Vanilla JS/ES Modules e POO), React/Vite, PWA
- Back-end: PostgreSQL, Supabase (Row Level Security, Edge Functions/Deno), APIs REST
- Pagamentos: Stripe (assinaturas, créditos, Pix, webhooks, idempotência)
- Segurança: Row Level Security, prevenção de IDOR e price tampering, rate limiting,
  verificação de JWT
- IA/LLM: integração de RAG, prompt engineering, ferramentas agênticas de
  desenvolvimento
- Testes e CI/CD: Playwright (E2E), GitHub Actions
- Qualidade e acessibilidade: auditorias Lighthouse, HTML semântico, WCAG básico
- Boas práticas: SEO técnico, LGPD/consentimento de cookies, analytics
- Versionamento com Git/GitHub

## Formação acadêmica
Bacharelado em Gestão e Economia
Universidade Estadual de Cultura e Artes de Kazan — 2003–2008

## Idiomas
- Russo: nativo
- Português: avançado
- Inglês: básico (leitura técnica)

## Contato
Email: vestek70@gmail.com
