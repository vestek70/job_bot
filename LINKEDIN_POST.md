# Post para o LinkedIn (PT-BR)

> Copie o texto abaixo. Ajuste o que quiser antes de publicar.
> Lembre-se de trocar o link se o repositório mudar de nome.

---

Procurar emprego como dev tem uma parte que ninguém comenta: o trabalho manual.

Abrir sete abas de sites de vaga. Reler a mesma descrição pela terceira vez.
Adaptar o currículo para cada vaga — de novo. E ainda tentar lembrar em quais
eu já tinha me candidatado.

Então fiz o que dev faz: automatizei o processo. E aproveitei para transformar
isso num projeto de verdade.

**Job Bot** — uma ferramenta local que:

🔎 Busca vagas em 7 fontes públicas ao mesmo tempo (Adzuna, Jooble, Remotive,
RemoteOK, Arbeitnow, Jobicy, The Muse)

🧹 Filtra o que não serve: fora de desenvolvimento, acima do meu nível, ou
"remoto" que na verdade é presencial em outra cidade

📄 Gera um currículo sob medida para cada vaga usando IA — alinhando o
vocabulário ao da descrição para passar na triagem por ATS, mas **sem inventar
nada**: o prompt proíbe explicitamente qualquer tecnologia ou experiência que
não esteja no meu currículo base

📊 Acompanha tudo: favoritas, arquivo de candidaturas enviadas, vagas
descartadas

✉️ Envia por e-mail — sempre com confirmação explícita minha

O que mais me interessou tecnicamente foi o problema do "currículo honesto".
É fácil fazer uma IA escrever um currículo que passa em qualquer ATS — basta
deixar ela mentir. O desafio real foi o contrário: fazer com que ela otimize
agressivamente para a vaga usando **somente** fatos verdadeiros. Se a vaga pede
uma tecnologia que eu não tenho, o bot não escreve que eu tenho. Ponto.

Algumas decisões que tomei de propósito:

→ Zero login automático em plataformas de emprego. Zero scraping. Só APIs
públicas. Automatizar login em LinkedIn/Gupy/Catho violaria os termos de uso
deles — e não vale o risco nem o atalho.

→ Nenhuma candidatura sai sem eu clicar e confirmar. Não existe modo
"candidatar-se a tudo".

→ Roda 100% local. Meus dados não vão para lugar nenhum.

Stack: Python, Flask, APIs REST, DeepSeek para a geração de texto. Interface
bilíngue (PT/RU), testes rodando offline.

O código está aberto, com README em português e russo:
👉 https://github.com/vestek70/job_bot

Se você também está procurando vaga de dev, pode clonar e usar — é só colocar
suas próprias chaves de API (todas têm plano gratuito) e seu currículo base.

E se olhar o código e tiver sugestão de melhoria, mando um abraço antecipado —
feedback de quem tem mais estrada é o que mais acelera quem está começando. 🙏

#desenvolvimento #python #opensource #buscadeemprego #tecnologia #devbr
#programacao #inteligenciaartificial

---

## Dicas para publicar

- **Melhor horário**: terça a quinta, entre 8h e 10h (horário de Brasília).
- **Primeira linha é o que aparece antes do "ver mais"** — ela é o gancho. A
  atual já foi escrita pensando nisso.
- **Comente no próprio post** com um detalhe técnico extra (ex.: como funciona
  o filtro de vagas híbridas). Isso aumenta o alcance e mostra profundidade.
- **Responda todos os comentários** nas primeiras 2 horas — é o que mais
  impulsiona o alcance no LinkedIn.
- Se quiser, adicione um print do painel ou um GIF curto de 10-15 segundos
  mostrando o fluxo: buscar → gerar currículo → abrir PDF. Post com imagem
  costuma performar bem melhor que só texto.
