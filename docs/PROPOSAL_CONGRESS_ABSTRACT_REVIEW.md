# Proposta Técnica: `congress-abstract-review`
## Plugin Dual-Engine para Avaliação e Auditoria de Resumos e Resumos Expandidos de Congressos Científicos

- **Instituição / Laboratório**: LaBiOmicS / Universidade de Mogi das Cruzes (UMC)
- **Coordenação**: Prof. Dr. Fabiano Bezerra Menegidio
- **Compatibilidade**: Google Antigravity CLI (`agy` / Gemini) e Claude Code (`claude`)

---

## 1. Visão Geral e Motivação

Avaliações de trabalhos submetidos a congressos e simpósios científicos possuem dinâmicas, restrições e objetivos substancialmente distintos da revisão por pares de periódicos tradicionais:

1. **Volume e Prazo**: Comissões científicas frequentemente precisam avaliar centenas de submissões em janelas curtas de 7 a 15 dias.
2. **Restrições Extremas de Espaço**: Limites estritos de palavras (ex.: 250 a 500 palavras) ou caracteres (com/sem espaços), número restrito de figuras/tabelas e limites de referências.
3. **Decisão Binária/Ternária de Alocação**: O objetivo do parecer não é solicitar revisões maiores de vários meses, mas definir a modalidade de apresentação (**Apresentação Oral / Podium**, **Pôster / Painel**, ou **Rejeição**) e a adequação ao eixo temático (*Track*).
4. **Vícios Típicos de Resumos**: Submissões prematuras com promessas de dados futuros (*"results will be presented during the conference"*), ausência de valores numéricos de suporte ou desconexão entre o objetivo formulado e a conclusão.

O plugin `congress-abstract-review` nasce como uma extensão direta da linhagem do `academic-peer-review`, adaptando a metodologia de subagentes independentes e scripts determinísticos em Python (`uv`) para o formato de eventos científicos.

---

## 2. Modos de Operação

O sistema operará em dois modos complementares:

```
                               ┌──────────────────────────────────────────────┐
                               │             Resumo do Autor                  │
                               │        (PDF, DOCX, TXT ou Markdown)          │
                               └──────────────────────┬───────────────────────┘
                                                      │
                       ┌──────────────────────────────┴──────────────────────────────┐
                       ▼                                                             ▼
         【 MODO 1: COM EDITAL / CFP 】                               【 MODO 2: PRÉ-SUBMISSÃO 】
       (Avaliadores e Comissões Científicas)                                (Autores e Pesquisadores)
                       │                                                             │
         Entrada: Edital / Call for Papers                               Entrada: Resumo Isolado
         (Regras, Barema, Limites e Eixos)                                           │
                       │                                                             │
         ▼                                                             ▼
  Gabarito de Conformidade Estrita:                             Boas Práticas Internacionais:
  • Limite exato de caracteres/palavras                         • Densidade de informação e concisão
  • Seções obrigatórias do evento                               • Eliminação de promessas sem dados
  • Preenchimento do barema oficial do edital                   • Polimento do inglês científico
  • Alocação de modalidade (Oral vs. Pôster)                    • Sugestões de cortes para enxugar texto
                       │                                                             │
                       └──────────────────────────────┬──────────────────────────────┘
                                                      ▼
                                       ┌──────────────────────────────┐
                                       │    Entregáveis Finais:       │
                                       │ 1. Ficha de Parecer (MD)     │
                                       │ 2. Relatório Formal em PDF   │
                                       │ 3. Sumário Executivo JSON    │
                                       └──────────────────────────────┘
```

### Modo 1: Avaliação da Comissão Científica (com Edital / Call for Papers)
- **Input**: Resumo do autor + Edital/Diretrizes do congresso (PDF, arquivo de texto ou colado no prompt).
- **Ação**: O edital é tratado como *Ground Truth* normativo. O sistema extrai:
  - Limite de tamanho (palavras/caracteres, com ou sem espaços, incluindo ou excluindo títulos/afiliações);
  - Seções obrigatórias (ex.: Introdução, Objetivos, Metodologia, Resultados, Conclusão, Apoio Financeiro);
  - Presença permitida ou proibida de figuras, tabelas e referências;
  - Idioma exigido (ex.: estritamente inglês);
  - Barema de pontuação e critérios de desempate estabelecidos no edital.

### Modo 2: Pré-Submissão do Autor (sem Edital)
- **Input**: Resumo do autor antes de submeter.
- **Ação**: Auditoria contra padrões internacionais de resumos biomédicos/científicos:
  - Caça a frases vazias e promessas sem dados;
  - Verificação de suficiência metodológica compacta;
  - Sugestões para atingir a contagem ideal e enriquecer o vocabulário científico.

---

## 3. Painel de Subagentes Especializados

Em vez de uma meta-revisão profunda de 4 estágios de periódico, o plugin emprega um comitê ágil de **3 avaliadores independentes**:

1. **Avaliador Alfa — Conformidade Normativa & Limites (Compliance Referee)**:
   - Executa a auditoria determinística de palavras e caracteres por seção;
   - Confere seções obrigatórias, afiliações e presença indevida de elementos (figuras extras, tabelas em resumos simples);
   - Valida formatação de agências de fomento (CNPq, FAPESP, CAPES, etc.).

2. **Avaliador Beta — Metodologia, Dados & Anti-Promessas (Data & Rigor Referee)**:
   - Detecta e pontua frases evasivas (*"serão discutidos"*, *"estão em andamento"*);
   - Audita a presença de métricas concretas ($n$, desvios, p-valores, tamanhos de efeito, limites de detecção);
   - Verifica se a conclusão é uma resposta direta ao objetivo declarado.

3. **Avaliador Gamma — Relevância, Inovação & Eixo Temático (Track & Impact Referee)**:
   - Avalia a relevância e originalidade do trabalho no contexto da área temática (*Track*);
   - Recomenda a modalidade mais justa de apresentação:
     - **Oral / Podium**: Dados maduros, novidade científica, conclusão robusta.
     - **Pôster / Painel**: Trabalho preliminar de mérito, ferramenta em validação, amostragem em expansão.
     - **Rejeição**: Escopo inadequado, violação grave de regras ou ausência de dados empíricos.

---

## 4. Scripts Auxiliares em Python (`uv`)

A ser implementado no diretório `scripts/` do novo plugin:

| Script | Função |
| :--- | :--- |
| `abstract_metrics.py` | Contagem exata de caracteres (com/sem espaços), palavras totais, palavras por seção, contagem de figuras e referências. |
| `edital_parser.py` | Parser de editais e Calls for Papers (extrai limites, seções obrigatórias e baremas em JSON). |
| `future_promise_detector.py` | Scanner léxico e semântico para detectar promessas de dados não apresentados no resumo. |
| `generate_congress_pdf.py` | Renderizador ReportLab/Pandoc de ficha de avaliação formal de congresso com selo e barema. |

---

## 5. Entregáveis do Parecer

O output gerado para o usuário consiste em:

1. **`congress_evaluation_sheet.md`**: Ficha oficial preenchida com notas por critério (0 a 10 ou conforme o edital), justificativas e veredito final (Oral / Pôster / Rejeição).
2. **`feedback_to_authors.md`**: Parecer construtivo e anônimo pronto para ser copiado no sistema de submissão do evento (ex.: JEMS, Even3, EasyChair, Morressier).
3. **`congress_evaluation_sheet.pdf`**: Relatório diagramado para arquivo da comissão científica.
4. **`evaluation_summary.json`**: Metadados estruturados para integração com planilhas de notas do evento.

---

## 6. Próximos Passos para Implementação

Quando for oportuno iniciar o desenvolvimento:
1. Criar o repositório ou módulo `congress-abstract-review` espelhando a estrutura do `academic-peer-review`.
2. Definir o `plugin.json` dual-engine (Antigravity + Claude Code).
3. Implementar `abstract_metrics.py` e `future_promise_detector.py`.
4. Incluir templates prontos de regras para os principais congressos da área (ex.: X-Meeting/AB3C, SBPC, ISMB).
