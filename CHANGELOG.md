# Changelog

Todas as mudanças relevantes deste plugin. O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e as versões seguem o [SemVer](https://semver.org/lang/pt-BR/).

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
- README: comandos de instalação no Claude Code corrigidos (`/plugin marketplace add` + `/plugin install academic-peer-review@labiomics`).
