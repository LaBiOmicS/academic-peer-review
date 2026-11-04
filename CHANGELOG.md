# Changelog

Todas as mudanças relevantes deste plugin. O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e as versões seguem o [SemVer](https://semver.org/lang/pt-BR/).

## [1.3.2] — 2026-11-04

### Corrigido
- No PDF, o cabeçalho de cada parecer (`SEED`, `LENS`/`AXIS`, `STANCE`) vinha em bloco de código, que o LaTeX não quebra; um eixo longo do crítico red-team passava da margem direita. O cabeçalho agora sai como lista.

## [1.3.1] — 2026-11-04

### Corrigido
- Menu da página visível em telas estreitas (celular e janelas com menos de 980 px), em uma segunda linha rolável; antes ele sumia e o guia e os prompts só eram alcançados rolando a página.
- Redação em português na página, nos READMEs e no CHANGELOG ("num/numa", "~9.000", "todos em paralelo"), com o ajuste equivalente em inglês e espanhol.

## [1.3.0] — 2026-11-04

### Adicionado
- Página do projeto refeita para quem não tem experiência com IA ou terminal: manual de oito passos com seletores de sistema (Windows, macOS, Linux) e de IA (Claude Code, Antigravity), que mostram só os comandos da escolha; prompts prontos para os casos mais comuns (rodada de revisão do autor, rascunho de parecer, revisão econômica, tipologia informada, retomada, explicação do resultado, painel com vários modelos, comando direto); perguntas frequentes e solução de problemas. O botão de copiar leva só a variante visível, sem marcas de prompt nem comentários.
- A página e os READMEs apresentam os dois usos da ferramenta: rascunho para o parecerista e rodada de revisão proativa para o próprio autor.

### Corrigido
- Tabelas largas do relatório em PDF (como a de verificação dos bloqueantes, com várias colunas de texto) eram ilegíveis na página retrato. Agora vão para páginas paisagem, no LaTeX (`pdflscape`) e no ReportLab. As colunas passam a ter largura proporcional ao conteúdo: antes, todas tinham a mesma largura no pandoc, e a coluna da crítica ficava espremida. No ReportLab, as tabelas deixaram de sair como texto corrido separado por `|`.
- A Parte II do PDF afirmava que todos os pareceristas usam o mesmo modelo mesmo em um painel com modelos diferentes; o texto agora segue o `results.json`.

## [1.2.0] — 2026-11-04

### Documentação
- README separado em três arquivos: inglês (`README.md`), português (`README.pt-BR.md`) e espanhol (`README.es.md`), com seletor de idioma no topo. A página do projeto ganhou a versão em espanhol e um seletor PT · EN · ES; o idioma inicial segue o do navegador. O texto foi reescrito em tom técnico: tabela de visão geral, diagrama do fluxo, definição dos níveis de severidade, módulos da auditoria, modelo de segurança, parâmetros, limitações e citação em BibTeX.
- As descrições em `plugin.json`, `.claude-plugin/plugin.json` e `pyproject.toml` deixaram de citar o painel fixo de quatro pareceristas e o Gemini, e passaram a descrever o painel de 3 a 8 papéis, os modelos misturados e a auditoria atual.

### Corrigido
- O runner `agy` falhava em todo painel headless: a versão atual lê o prompt como valor de `-p` e tomava `--effort` por prompt. O `-p` vai agora no fim do comando, seguido do prompt; um prompt grande demais para um argumento (128 KiB no Linux) é trocado por uma instrução para ler o arquivo do prompt.
- Repetir o `spawn_reviewers.py` para completar pareceristas que falharam sorteava os papéis de novo. Os pareceres já prontos ficavam com papéis antigos, e o painel podia terminar com dois críticos *red-team* e sem advogado do autor. Agora a nova execução mantém os papéis e as sementes do manifesto anterior (`--overwrite` começa um painel novo).
- As lentes 3 e 4 do auditor de reprodutibilidade dependem do perfil do manuscrito. Uma revisão bibliométrica não recebe mais pedidos de acessos SRA/GEO nem de aprovação CEUA: são cobrados o depósito do corpus e dos parâmetros dos mapas e os itens do BIBLIO. Revisões de literatura não recebem normas de pesquisa com animais, e a lente normativa cita as diretrizes da tipologia e da abordagem.
- A auditoria distingue a string de busca ausente da string publicada apenas em um protocolo externo (protocols.io, OSF, PROSPERO) ou no material suplementar.
- Periódicos sem perfil curado não recebem mais alertas genéricos ("Failure to meet standard reporting…"). A auditoria diz que os requisitos não foram verificados, indica a página do periódico e cita seus tópicos mais frequentes. Quando o OpenAlex não lista a editora, aparece a sociedade ou o país e a plataforma, em vez de "Unknown Publisher".
- O SAGER deixou de se aplicar a todo artigo de Biológicas: agora exige menção a pessoas ou animais (um estudo de solo ou de plantas não tem sujeitos). Experimentos de campo com parcelas, testemunhos de solo e safras passaram a ser reconhecidos como abordagem de campo.
- Testes para `extract_paper.py` e `literature_search.py` (cobertura total de 70% para 81%).

## [1.1.0] — 2026-11-04

### Adicionado
- Página do projeto no GitHub Pages (`site/`, publicada pelo workflow `pages.yml`), em português e inglês.
- Opção `--no-ai-disclosure` em `compile_results.py` e `generate_pdf_report.py` para gerar o PDF sem o aviso de revisão assistida por IA. O aviso continua ativo por padrão.
- Abordagem de pesquisa `bibliometric_scientometric` (13ª). Ela é atribuída automaticamente às revisões bibliométricas e audita a delimitação do corpus, a origem das palavras-chave, as regras de contagem e de atribuição de país, a normalização de citações e os parâmetros dos mapas. A auditoria pré-revisão ganhou checagens próprias para ela e para a string e a data de busca.
- Calibração de severidade em todos os pareceres. Cada preocupação maior é marcada como `Blocking`, `Essential` ou `Optional`, com no máximo 5 bloqueantes, e só é bloqueante se o parecerista citar a conclusão que cai sem a correção. Os pareceristas passam a procurar as ressalvas que os autores já fizeram, conferir a direção de cada viés e tratar a lente sorteada como hipótese a testar.
- Parecerista advogado do autor (`reviewer_author_advocate.md`), contrapeso do crítico *red-team*. Ele testa as críticas prováveis contra o texto e lista exigências desproporcionais. Entra por padrão; `--no-author-advocate` o remove. O painel padrão passa de 4 para 5 pareceristas.
- A metarrevisão ganhou a seção `## Blocking-concern verification`, que confere cada bloqueante contra o manuscrito, e o roteiro passou a ter três níveis (Blocking, Essential, Optional). A concordância entre pareceristas deixou de contar como evidência, já que todos rodam no mesmo modelo.
- A matriz de preocupações registra o nível de cada uma e distingue, por parecerista, crítica maior (`major`) de menção de passagem (`minor`). Matrizes antigas, com booleanos, continuam sendo lidas.
- O `compile_results.py` insere na metarrevisão os números da auditoria (escopo, risco, DOIs, `statcheck`, IA, dados), grava o hash da auditoria em `results.json` e avisa quando a metarrevisão cita números que a contradizem ou foi escrita antes dela. Também gera `author_letter.md`, uma carta curta aos autores só com os itens bloqueantes e essenciais.
- Painel com modelos misturados (`--panel-models claude:opus,agy,claude:sonnet`). Cada parecerista recebe um par runner:modelo, registrado no manifesto e em `results.json`. Na metarrevisão, a concordância só ganha peso quando vem de modelos diferentes.
- O `compile_results.py` verifica o contrato de severidade: confere se cada preocupação maior tem nível e se há no máximo 5 bloqueantes, e se a metarrevisão tem a tabela de verificação e o roteiro em três níveis. Avisa com `SEVERITY CONTRACT NOT MET` e registra o resultado em `results.json` (`severity_contract`).
- A auditoria reversa de citações verifica também os identificadores arXiv citados pelos pareceristas, na API do arXiv (`arxiv_lookup.py`). Antes, só os DOIs eram conferidos. Identificadores que aparecem no próprio manuscrito não são verificados, e falhas de rede deixam o identificador como não verificado, sem acusá-lo de alucinação.
- As revisões bibliométricas têm lentes e eixos de *red-team* próprios: artefato de corpus, efeito de grupo dominante, artefato de indexação, ano final incompleto, mapas instáveis, leis bibliométricas aplicadas a corpus pequeno, extrapolação narrativa e corpus heterogêneo. Antes, recebiam as lentes da área, pensadas para estudos primários.

### Corrigido
- README: a composição do painel por número de pareceristas está documentada (com 3 ou 4 não há parecerista de domínio), os papéis aparecem como sorteados entre os codinomes, e a tabela de artefatos inclui `author_letter.md`, a matriz com níveis de severidade e o painel com modelos misturados.
- Revisões bibliométricas eram classificadas pela abordagem do vocabulário da literatura revisada (ex.: `computational_in_silico` com confiança de 0,97 em um estudo bibliométrico sobre metagenômica). Agora recebem `bibliometric_scientometric`.
- Revisões bibliométricas não recebem mais as checagens de estudo primário da área (réplicas, efeito de lote, acessos, poder, FDR, tamanho de efeito, sementes aleatórias), e a aprovação ética aparece como não exigida.
- O critério *Clinical/Bio-AI* (TRIPOD+AI/CLAIM) exige um modelo de IA ou uma diretriz de IA no texto; antes, qualquer artigo de Biológicas com abordagem computacional o ativava. A palavra comum "*claim*" deixou de ativar a diretriz CLAIM, e o SAGER não se aplica mais a revisões bibliométricas, ensaios e artigos de software.
- A aderência ao escopo do periódico comparava os tópicos com o texto inteiro, inclusive as referências, e contava palavras comuns a quase todos os tópicos do periódico (ex.: "ecology" em uma revista de ecologia). Um artigo sobre resistência antimicrobiana em insetos chegava a 83% e "Low Risk" na *Ecología Austral* por tópicos sem relação. Agora a comparação usa só o corpo do texto e descarta essas palavras.
- O cabeçalho do PDF não sobrepõe mais o título da seção ao texto central.
- O PDF não falha mais quando um parecer tem uma linha `---` seguida de texto: o pandoc a lia como início de um bloco YAML (`Unknown alias`). No *fallback* ReportLab, itálico dentro de negrito (`**Fit with *Ecología Austral***`) gerava tags mal aninhadas e abortava o relatório inteiro; agora aninha corretamente, e uma linha malformada cai para texto simples em vez de derrubar o PDF.
- Quando uma engine do LaTeX falha e a seguinte gera o PDF (ex.: `lualatex` com cache de fontes quebrado), o `generate_pdf_report.py` informa em uma linha qual engine foi usada. Antes, imprimia o erro completo da engine que falhou, como se o PDF não tivesse sido gerado.
- O eixo de *red-team* "ano final incompleto" das revisões bibliométricas presumia um pico espúrio. Um ano truncado costuma subestimar a contagem, e o eixo agora pede que o parecerista confira essa direção.
- A auditoria reversa de citações não acusa mais como alucinação os DOIs que os pareceristas copiam do próprio manuscrito (por exemplo, para apontar um DOI malformado nas referências). Eles ficam em `manuscript_dois_quoted` no `results.json`, já que a auditoria pré-revisão verifica os DOIs do manuscrito.
- O `install.sh` informa ao final apenas os CLIs em que o plugin foi registrado. Quando falta o `agy` ou o `claude`, o resumo diz isso (a cópia de arquivos para `~/.gemini` não conta como instalação). Antes, anunciava sucesso para Antigravity e Claude Code mesmo quando um deles faltava.
- O `install.sh` refaz o registro do marketplace `labiomics` quando ele aponta para outro diretório (ex.: depois de mover o repositório). Antes, o plugin deixava de carregar no Claude Code com o erro `cache-miss`.

## [1.0.0] — 2026-10-26

Primeira versão pública e estável.

### Funcionalidades
- Painel de 3 a 8 pareceristas independentes (`alfa`, `beta`, `gamma`, …) com classificação em 3 eixos (5 áreas × 15 tipologias × 12 abordagens).
- Auditoria determinística pré-revisão: `statcheck`, checagens por tipologia/abordagem/área, FAIR e reprodutibilidade, proveniência de IA, citações e retratações via OpenAlex.
- Detecção de conteúdo oculto que tenta manipular a revisão (PDF, DOCX, HTML, Markdown, LaTeX).
- Auditoria de escopo do periódico-alvo e risco de *desk reject*.
- Metarrevisão editorial, matriz de preocupações (CSV/JSON), `results.json` e relatório em PDF (pandoc ou ReportLab).
- Execução por subagentes nativos (Claude Code e Antigravity) ou por subprocessos headless (`agy`, `gemini`, `claude`).

### Corrigido antes da release
- A detecção de texto oculto em PDF/DOCX não falha mais em silêncio quando faltam dependências: os scripts rodam via `uv run` (PEP 723) e a auditoria marca a verificação como incompleta.
- O passo 3 no Claude Code usa o nome correto do subagente (`academic-peer-review:peer-reviewer`).
- O risco de *desk reject* não é mais inferido sem evidência: periódicos sem perfil curado e sem correspondência de tópico/área ficam como "Not assessed". Requisitos genéricos não verificados não reduzem a nota, e periódicos alternativos só são sugeridos com risco alto ou crítico.
- Tentativas de manipulação no manuscrito são denunciadas ao editor nos comentários confidenciais e não decidem o veredito (antes, havia instruções contraditórias que mandavam rejeitar).
- O PDF não duplica mais a matriz de preocupações e lista os DOIs não resolvidos citados pelos pareceristas.
- As seções do relatório de auditoria são numeradas em sequência.
- Credenciais repassadas aos subprocessos dependem do runner escolhido.
- O texto oculto de tentativas de manipulação é substituído por um marcador na cópia do manuscrito lida pelos pareceristas, para que não o descrevam como texto visível.
- A classificação da abordagem de pesquisa dá precedência à declaração explícita de desenho (ex.: "cross-sectional study", "randomised controlled trial") e ignora a lista de referências.
- Classificação com confiança baixa (área ou abordagem) é marcada como `needs_confirmation`: o agente confirma os eixos pelo resumo e pelos métodos e, em sessão interativa, pergunta ao usuário antes de preparar o painel. Sem confirmação, a auditoria avisa os pareceristas.
- README: estimativa de custo e tempo por revisão.
- Extração de PDF escolhe o melhor extrator pela proporção de palavras coladas e usa o `pdftotext` em modo de leitura (o modo `-layout` misturava as colunas de PDFs em duas colunas).
- A confiança da abordagem considera a quantidade de evidência: poucos termos soltos (ex.: "mice" em um artigo de modelagem) pedem confirmação. Corrigido o padrão "quadrat", que casava com "quadratically".
- O cálculo interno da semente não vaza mais para a lente/postura dos pareceristas no relatório.
- O tipo de artigo ignora a lista de referências, exige evidência mínima para sair de "pesquisa original" e passa pelo passo de confirmação quando incerto (antes, um título citado como "revisão de escopo" reclassificava um estudo empírico).
- DOIs ausentes do OpenAlex são confirmados no registro do doi.org antes de serem tratados como inexistentes (antes, um DOI legítimo de preprint da JMIR foi acusado de alucinação).
- README: comandos de instalação no Claude Code corrigidos (`/plugin marketplace add` + `/plugin install academic-peer-review@labiomics`).
