# Changelog

Todas as mudanças relevantes deste plugin. O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e as versões seguem o [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

### Adicionado
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
- Revisões bibliométricas eram classificadas pela abordagem do vocabulário da literatura revisada (ex.: `computational_in_silico` com confiança de 0,97 num estudo bibliométrico sobre metagenômica). Agora recebem `bibliometric_scientometric`.
- Revisões bibliométricas não recebem mais as checagens de estudo primário da área (réplicas, efeito de lote, acessos, poder, FDR, tamanho de efeito, sementes aleatórias), e a aprovação ética aparece como não exigida.
- O critério *Clinical/Bio-AI* (TRIPOD+AI/CLAIM) exige um modelo de IA ou uma diretriz de IA no texto; antes, qualquer artigo de Biológicas com abordagem computacional o ativava. A palavra comum "*claim*" deixou de ativar a diretriz CLAIM, e o SAGER não se aplica mais a revisões bibliométricas, ensaios e artigos de software.
- A aderência ao escopo do periódico comparava os tópicos com o texto inteiro, inclusive as referências, e contava palavras comuns a quase todos os tópicos do periódico (ex.: "ecology" numa revista de ecologia). Um artigo sobre resistência antimicrobiana em insetos chegava a 83% e "Low Risk" na *Ecología Austral* por tópicos sem relação. Agora a comparação usa só o corpo do texto e descarta essas palavras.
- O cabeçalho do PDF não sobrepõe mais o título da seção ao texto central.
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
- A confiança da abordagem considera a quantidade de evidência: poucos termos soltos (ex.: "mice" num artigo de modelagem) pedem confirmação. Corrigido o padrão "quadrat", que casava com "quadratically".
- O cálculo interno da semente não vaza mais para a lente/postura dos pareceristas no relatório.
- O tipo de artigo ignora a lista de referências, exige evidência mínima para sair de "pesquisa original" e passa pelo passo de confirmação quando incerto (antes, um título citado como "revisão de escopo" reclassificava um estudo empírico).
- DOIs ausentes do OpenAlex são confirmados no registro do doi.org antes de serem tratados como inexistentes (antes, um DOI legítimo de preprint da JMIR foi acusado de alucinação).
- README: comandos de instalação no Claude Code corrigidos (`/plugin marketplace add` + `/plugin install academic-peer-review@labiomics`).
