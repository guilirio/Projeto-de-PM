# Otimização Combinatória em Redes Sociais: Aplicações do Problema de Coloração de Vértices

Trabalho Prático da disciplina **GCC118 – Programação Matemática**
Departamento de Ciência da Computação – Universidade Federal de Lavras (UFLA)
Semestre letivo 2026/2

- **Autor:** Guilherme Lirio Miranda
- **Docentes:** Mayron César O. Moreira (DCC) e Andreza C. Beezão Moreira (DMM)
- **Modalidade:** Opção A – problema real com dados públicos

---

## Sumário

1. [Sobre o projeto](#1-sobre-o-projeto)
2. [Status das fases](#2-status-das-fases)
3. [Base de dados](#3-base-de-dados)
4. [Formulação matemática (PLI)](#4-formulação-matemática-pli)
5. [Construção das instâncias](#5-construção-das-instâncias)
6. [Ambiente e dependências](#6-ambiente-e-dependências)
7. [Estrutura do repositório](#7-estrutura-do-repositório)
8. [Como reproduzir](#8-como-reproduzir)
9. [Resultados da Fase 2](#9-resultados-da-fase-2)
10. [Limitações](#10-limitações)
11. [Próximas etapas](#11-próximas-etapas)
12. [Referências](#12-referências)

---

## 1. Sobre o projeto

O projeto modela e resolve o **Problema de Coloração de Vértices** sobre uma rede social de desenvolvedores de software (GitHub). O objetivo é atribuir uma cor a cada vértice de modo que vértices adjacentes tenham cores distintas, minimizando o número de cores utilizadas (número cromático, χ(G)).

Cada classe de cor é um **conjunto independente**: um grupo de usuários sem conexão direta entre si. Minimizar o número de cores equivale a particionar a rede no menor número possível desses grupos.

> **Observação:** essa interpretação é estrutural. Ela não garante independência estatística entre usuários nem elimina influências indiretas, por exemplo em testes A/B.

O trabalho percorre o ciclo completo da Programação Matemática: coleta de dados, modelagem exata em PLI, métodos heurísticos, validação e análise de incertezas.

## 2. Status das fases

| Fase | Entregável | Prazo | Status |
|------|-----------|-------|--------|
| 0 | Proposta (problema e fonte de dados) | até 28/08 | Concluída |
| 1 | Análise exploratória dos dados | até 09/10 | Concluída |
| 2 | Modelagem matemática (PLI) e testes em solver | até 30/10 | Concluída |
| 3 | Métodos heurísticos e comparação com o exato | até 17/11 | Em andamento |
| 4 | Validação exata e análise de incertezas (entrega final) | até 04/12 | Pendente |
| 5 | Apresentação oral | 10/12 e 11/12 | Pendente |

## 3. Base de dados

Os dados vêm da **Stanford Large Network Dataset Collection (SNAP)**, dataset **MUSAE GitHub Social Network**, gerado a partir da API pública do GitHub. Cada vértice é um desenvolvedor e cada aresta indica que dois desenvolvedores se seguem mutuamente.

| Característica | Valor |
|----------------|-------|
| Tipo de grafo | Não direcionado |
| Vértices (\|V\|) | 37.700 |
| Arestas (\|E\|) | 289.003 |
| Densidade | ≈ 0,000407 (rede esparsa) |
| Grau médio / mediano / máximo | ≈ 15,33 / 6 / 9.458 |
| Componentes conexas | 1 |

Arquivos utilizados:

- `musae_git_edges.csv`: lista de arestas do grafo.
- `musae_git_target.csv`: cadastro de vértices (apenas os IDs são usados na coloração).
- `musae_git_features.json`: usado somente para conferir a correspondência dos IDs; os atributos não entram no modelo.

**Verificações de qualidade:** não há arestas duplicadas, laços (self-loops) nem vértices isolados. Os IDs formam o intervalo contínuo de 0 a 37.699. Essas verificações confirmam a consistência estrutural dos arquivos, mas não demonstram ausência de ruído na rede observada.

## 4. Formulação matemática (PLI)

Seja G = (V, E) um grafo simples, não direcionado e não vazio, com n = |V| e m = |E|. Seja C = {1, …, K} o conjunto de cores disponíveis, onde K é obtido por uma **coloração gulosa válida** (vértices por grau decrescente, desempate pelo menor ID, menor cor livre). Assim, χ(G) ≤ K. A coloração gulosa só define a cota K e **não** é fornecida como solução inicial ao solver.

**Variáveis**

- `x[v,c]` ∈ {0,1}: vale 1 se o vértice v recebe a cor c.
- `y[c]` ∈ {0,1}: vale 1 se a cor c está ativada.

**Modelo**

```
min  z = Σ_{c ∈ C} y[c]                                   (1)

s.a. Σ_{c ∈ C} x[v,c] = 1             ∀ v ∈ V              (2)
     x[v,c] ≤ y[c]                    ∀ v ∈ V, c ∈ C      (3)
     x[u,c] + x[v,c] ≤ 1              ∀ {u,v} ∈ E, c ∈ C  (4)
     y[c] ≥ y[c+1]                    c = 1, …, K-1       (5)
     x[v,c], y[c] ∈ {0,1}                                  (6)
```

- (1) minimiza o número de cores ativadas.
- (2) atribui exatamente uma cor a cada vértice.
- (3) ativa qualquer cor que tenha sido atribuída.
- (4) impede conflitos entre vizinhos.
- (5) é a quebra de simetria: ordena as ativações sem excluir o ótimo.

**Tamanho do modelo (antes do presolve)**

```
N_variáveis = (n + 1) · K
N_restrições = n + n·K + m·K + (K - 1)
```

Para a rede completa com a cota ingênua K = n = 37.700, seriam 1.421.327.700 variáveis e 10.895.413.100 restrições apenas de incompatibilidade em arestas. Isso motiva a **restrição de escopo** adotada: o modelo exato é testado em subgrafos induzidos.

**Relaxação linear:** para K ≥ 2, x[v,c] = y[c] = 1/K é viável e dá objetivo 1, o que explica os limites inferiores fracos (LB = 1) observados em instâncias maiores. Isso não implica que exista coloração inteira com uma cor.

## 5. Construção das instâncias

Em vez de resolver a rede inteira, o modelo é avaliado em **subgrafos induzidos** G[S], mantendo todas as arestas originais com ambos os extremos em S.

| Conjunto | Vértices por instância | Seleção | Sementes | Total |
|----------|-----------------------|---------|----------|-------|
| Principal | 25, 50, 100, 200 e 400 | BFS e fronteira | 3 por combinação | 30 |
| Exploratório | 800 e 1.600 | BFS | 2 por tamanho | 4 |

- **BFS:** raiz sorteada uniformemente; a lista de vizinhos é embaralhada a cada expansão; a busca para ao atingir n vértices.
- **Fronteira:** raiz sorteada; a cada passo escolhe-se uniformemente um vértice entre os vizinhos ainda não incluídos.
- **Sementes (principal):** `10000(a+1) + 100(b+1) + r`, com a = 0 (BFS) ou 1 (fronteira), b = 0,…,4 (tamanhos) e r = 1,2,3.
- **Sementes (exploratório):** `30000 + n + r`.
- Cada JSON registra a raiz, a semente, os IDs originais e as arestas.

Um triângulo (n = 3, m = 3, K = 3; 12 variáveis e 23 restrições) é usado apenas como teste didático da tradução do modelo e não entra na contagem das instâncias.

## 6. Ambiente e dependências

| Item | Versão / detalhe |
|------|------------------|
| Python | 3.12.14 |
| PuLP | 4.2.0 |
| Solver | COIN_CMD / CBC (selecionado automaticamente pelo PuLP) |
| Pacote CBC | `cbcbox` 2.929 (executável CBC Devel, compilado em 23/03/2026) |
| Sistema | Windows 11 |
| Processador | AMD Ryzen 5 3600 |

Instalação sugerida:

```bash
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

pip install pulp==4.2.0 cbcbox==2.929
```

> Ajuste a lista de dependências conforme o `requirements.txt` do seu repositório.

## 7. Estrutura do repositório

> Estrutura sugerida. Adapte os nomes às pastas e scripts reais do projeto.

```
.
├── README.md
├── requirements.txt
├── data/
│   ├── raw/                  # musae_git_edges.csv, musae_git_target.csv, musae_git_features.json
│   └── instancias/           # subgrafos gerados (JSON) e hashes de conferência
├── src/
│   ├── analise_exploratoria  # Fase 1
│   ├── geracao_instancias    # BFS e fronteira (Fase 2)
│   ├── modelo_pli            # Formulação PuLP (Fase 2)
│   └── heuristicas           # Fase 3
├── resultados/
│   ├── piloto/               # execuções de 30/60/120 s com logs
│   ├── principal/            # resumo.csv e resultado.json por instância
│   └── exploratorio/
└── relatorio/                # Relatório consolidado (Fases 0 a 4)
```

## 8. Como reproduzir

1. Baixe o dataset **MUSAE GitHub Social Network** no SNAP e coloque os três arquivos em `data/raw/`.
2. Execute a análise exploratória para validar os arquivos (duplicatas, laços, IDs, isolados, componentes).
3. Gere os 34 subgrafos com as sementes descritas na [seção 5](#5-construção-das-instâncias). A geração é determinística para o ambiente documentado; os hashes dos arquivos permitem conferir as entradas.
4. Resolva cada instância com o modelo PLI, com limite de tempo de **30 s** por instância.
5. Consulte `resumo.csv` e `resultado.json` de cada instância para tempos e resultados.

**Verificação de cada solução retornada:** integralidade (tolerância de 10⁻⁵), atribuição única, ativação das cores, ausência de conflitos em todas as arestas, ordem de `y` e consistência do objetivo. Um ótimo só é declarado com término `Optimal` e solução validada.

## 9. Resultados da Fase 2

### Escolha do orçamento de tempo

Um piloto com 6 casos testou 30, 60 e 120 s. Pela regra de decisão registrada (só aumentar o tempo se houvesse mais soluções inteiras ou ótimos), os três orçamentos resultaram em 3 soluções e 2 ótimos, e foi escolhido o limite de **30 s**. O piloto justifica uma escolha prática, mas não prova que o orçamento seja ideal.

### Visão geral (34 instâncias, limite de 30 s)

| Situação | Instâncias |
|----------|-----------|
| Ótimo comprovado | 27 |
| Solução inteira sem prova de ótimo | 1 (BFS_200_1: UB = 8, LB = 7, gap 12,5%) |
| Sem solução inteira retornada | 6 |

A ausência de solução devolvida **não** significa inviabilidade: toda instância possui a coloração gulosa válida com K cores.

### Comparação por tamanho e seleção (conjunto principal)

| n | BFS: ótimos | BFS: mediana t (s) | Fronteira: ótimos | Fronteira: mediana t (s) |
|---|-------------|--------------------|-------------------|--------------------------|
| 25 | 3/3 | 0,17 | 3/3 | 0,10 |
| 50 | 3/3 | 0,52 | 3/3 | 0,13 |
| 100 | 3/3 | 0,97 | 3/3 | 0,23 |
| 200 | 2/3 | 3,62 | 3/3 | 0,68 |
| 400 | 1/3 | 33,13 | 3/3 | 4,27 |

Principais observações:

- As instâncias de fronteira são esparsas e foram todas resolvidas ao ótimo.
- As amostras BFS são mais densas (para n = 400, entre 1.626 e 2.556 arestas, contra 518 a 593 na fronteira) e concentram as instâncias sem solução.
- Em 4 das 30 instâncias principais o solver encontrou menos cores que a cota gulosa K, mostrando que K não deve ser lido como ótimo.
- Nas instâncias resolvidas ao ótimo com UB = K, a PLI fornece a certificação que a gulosa sozinha não oferece.
- As 4 instâncias exploratórias (n = 800 e 1.600) terminaram por limite de tempo sem solução inteira.

Os resultados completos por instância (n, m, K, número de variáveis e restrições, UB, LB, gap, término e tempo) estão nas tabelas do relatório e em `resumo.csv`.

## 10. Limitações

- A seleção de subgrafos é local, usa uma única rede e admite sobreposição de vértices: as 34 instâncias **não** são observações independentes nem amostras uniformes.
- Houve uma execução por instância e orçamento; não foram feitas repetições para estimar a variabilidade temporal.
- Os resultados **não** sustentam generalização para outras redes, comparação entre solvers ou afirmação de impossibilidade de resolver a rede completa.
- A avaliação é exata por subgrafo: o número cromático da rede completa não é determinado.
- Os tempos medidos (chamada Python, executável CBC) e o limite solicitado são grandezas diferentes. O backend pode ultrapassar o limite antes de verificar a parada.
- O tempo do piloto foi guiado por testes preliminares e reutiliza casos da bateria; não é validação independente.

## 11. Próximas etapas

- **Fase 3:** heurísticas construtivas (coloração sequencial por grau e por saturação) e busca local/metaheurística, avaliadas nos subgrafos e no grafo completo.
- **Fase 4:** análise experimental completa, comparação heurística × exato e discussão de como a metodologia se adapta às incertezas do problema.
- **Entrega final:** relatório consolidado e gráfico obrigatório de **qualidade da solução × tempo** (heurística × exato).

## 12. Referências

- Stanford Large Network Dataset Collection (SNAP): *MUSAE GitHub Social Network*.
- Enunciado do Trabalho Prático, GCC118 – Programação Matemática, UFLA, 2026/2.
