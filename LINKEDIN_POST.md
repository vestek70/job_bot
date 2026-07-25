# Post para o LinkedIn (PT-BR)

> Copie o texto entre as linhas. Ajuste o que quiser antes de publicar.

---

Procurar vaga de dev tem uma parte que ninguém comenta: o trabalho manual.
Sete abas abertas, a mesma descrição relida três vezes, o currículo adaptado de
novo para cada vaga.

Automatizei. E virou projeto open source.

**Job Bot** busca em 7 fontes de uma vez — cada uma cobre um pedaço diferente
do mercado:

🇧🇷 **Adzuna** — a base para o Brasil. Rastreia e deduplica job boards em 16+
países. (O instituto de estatística do Reino Unido usa os dados dela em
relatórios de mercado de trabalho.)

🌍 **Jooble** — o maior alcance bruto: indexa 140 mil+ fontes em ~69 países.
Traz vaga que não está em nenhum board de tecnologia.

💼 **Remotive** — remoto curado à mão. Não é volume, é filtro: pouquíssimo lixo.

💰 **RemoteOK** — o board remoto de maior tráfego, e o que mais leva a sério
transparência salarial.

🇪🇺 **Arbeitnow** — API aberta, sem chave, forte presença europeia.

🏠 **Jobicy** — remoto; sobrepõe em parte, mas sempre traz alguma exclusiva.

🏢 **The Muse** — o diferencial não é a vaga, é a empresa: perfis com cultura,
fotos e depoimentos. Ajuda a decidir se você *quer* trabalhar ali.

Depois o bot gera um currículo sob medida para a vaga escolhida.

Essa foi a parte tecnicamente mais interessante. É fácil fazer uma IA escrever
currículo que passa em ATS — basta deixar ela mentir. O desafio foi o contrário:
otimizar agressivamente usando **só fatos verdadeiros**. Ele alinha o vocabulário
ao da vaga e reordena as competências, mas o prompt proíbe adicionar qualquer
tecnologia que não esteja no meu currículo base. Se a vaga pede algo que eu não
tenho, ele não escreve que eu tenho.

Três decisões que tomei de propósito:

→ Zero scraping e zero login automático em plataformas. Só APIs públicas —
automatizar login em LinkedIn/Gupy violaria os termos de uso deles.
→ Nada é enviado sem eu confirmar. Não existe modo "candidatar-se a tudo".
→ Roda 100% local.

Python, Flask, DeepSeek. README em português e russo:
👉 https://github.com/vestek70/job_bot

Está procurando vaga também? Clona e usa — licença MIT, e todas as APIs têm
plano gratuito.

E se olhar o código e tiver sugestão, feedback de quem tem mais estrada é o que
mais acelera quem está começando. 🙏

#devbr #python #opensource #buscadeemprego #inteligenciaartificial

---

## Dicas rápidas

- Publique terça a quinta, 8h–10h (Brasília).
- A primeira linha é o gancho — é só ela que aparece antes do "ver mais".
- Adicione um print do painel ou GIF curto (buscar → gerar currículo → PDF).
  Post com imagem performa bem melhor.
- Responda os comentários nas primeiras 2 horas: é o que mais impulsiona alcance.
- Se quiser cortar mais, os 7 itens podem virar 3 linhas: "Adzuna e Jooble para
  volume no Brasil, Remotive/RemoteOK/Arbeitnow/Jobicy para remoto, The Muse
  para cultura da empresa."

## Fontes dos números (verificados em julho/2026)

- Adzuna: https://developer.adzuna.com/ · https://jobspipe.dev/blog/adzuna-api
- Jooble: https://jooble.org/how-jooble-works
- Remotive: https://jobboardsearch.com/job-boards/remotive
- RemoteOK: https://topremotejobboards.com/review/remotive
- The Muse: https://publicapi.dev/the-muse-api
