"""Coloracao minima de vertices: modelo de atribuicao em PuLP 4.2.0.

Entrada JSON: {"vertices": [0, 1, 2], "arestas": [[0, 1], [1, 2]]}
Exemplo: python coloracao.py instancias/triangulo.json --tempo 30 --saida resultados/triangulo
O proprio PuLP escolhe o solver; a chamada e modelo.solve(), sem argumento.
"""
import argparse
import json
import math
import re
import hashlib
from pathlib import Path
from time import perf_counter

import pulp as pl


def ler_instancia(caminho):
    """Le IDs e arestas de um grafo simples; preserva vertices isolados."""
    dados = json.loads(caminho.read_text(encoding="utf-8-sig"))
    vertices = dados["vertices"]
    if not vertices or any(type(v) is not int or v < 0 for v in vertices):
        raise ValueError("Informe vertices nao vazios com IDs inteiros nao negativos.")
    if len(vertices) != len(set(vertices)):
        raise ValueError("Ha IDs de vertices repetidos.")

    conjunto = set(vertices)
    arestas = set()
    for par in dados["arestas"]:
        if len(par) != 2 or any(type(v) is not int for v in par):
            raise ValueError("Cada aresta deve conter dois IDs inteiros.")
        u, v = par
        if u not in conjunto or v not in conjunto:
            raise ValueError(f"Aresta com vertice nao cadastrado: {par}")
        if u == v:
            raise ValueError(f"Laco em {u}: nao existe coloracao propria.")
        aresta = tuple(sorted((u, v)))
        if aresta in arestas:
            raise ValueError(f"Aresta repetida: {par}")
        arestas.add(aresta)
    return sorted(vertices), sorted(arestas)


def limite_guloso(vertices, arestas):
    """Obtem K de uma coloracao valida, sem afirmar que ela seja otima."""
    vizinhos = {v: set() for v in vertices}
    for u, v in arestas:
        vizinhos[u].add(v)
        vizinhos[v].add(u)

    cores = {}
    # Maior grau primeiro; empate pelo menor ID.
    ordem = sorted(vertices, key=lambda v: (-len(vizinhos[v]), v))
    for v in ordem:
        proibidas = {cores[u] for u in vizinhos[v] if u in cores}
        c = 1
        while c in proibidas:
            c += 1
        cores[v] = c
    return max(cores.values()), cores


def construir_modelo(vertices, arestas, K):
    """Cada bloco abaixo corresponde a uma equacao da formulacao."""
    C = range(1, K + 1)
    modelo = pl.LpProblem("Coloracao_de_vertices", pl.LpMinimize)
    x = modelo.add_variable_dicts("x", (vertices, C), cat="Binary")
    y = modelo.add_variable_dicts("y", C, cat="Binary")

    # (1) Minimizar o numero de cores ativadas.
    modelo += pl.lpSum(y[c] for c in C), "numero_de_cores"

    # (2) Cada vertice recebe exatamente uma cor.
    for v in vertices:
        modelo += pl.lpSum(x[v][c] for c in C) == 1, f"uma_cor_{v}"

    # (3) Uma cor atribuida precisa estar ativada.
    for v in vertices:
        for c in C:
            modelo += x[v][c] <= y[c], f"ativacao_{v}_{c}"

    # (4) Vertices adjacentes nao compartilham uma cor.
    for u, v in arestas:
        for c in C:
            modelo += x[u][c] + x[v][c] <= 1, f"aresta_{u}_{v}_{c}"

    # (5) Quebra de simetria: ativar cores em ordem.
    for c in range(1, K):
        modelo += y[c] >= y[c + 1], f"ordem_{c}"

    return modelo, x, y


def configurar_padrao(tempo, pasta):
    """Configura o objeto ja escolhido pelo PuLP, sem escolher um solver pelo nome.

    A disponibilidade do backend e decidida pelo PuLP ao importar a biblioteca.
    Instalar pulp[cbc] disponibiliza CBC; isso nao instancia CBC neste programa.
    As demais opcoes do solver permanecem com seus valores padrao.
    """
    padrao = pl.apis.LpSolverDefault
    if padrao is None or not padrao.available():
        raise RuntimeError('Sem solver padrao disponivel. Instale: pip install "pulp[cbc]==4.2.0"')
    padrao.timeLimit = tempo
    padrao.msg = False
    padrao.optionsDict["logPath"] = str(pasta / "solver.log")
    if hasattr(padrao, "tmpDir"):
        padrao.tmpDir = str(pasta.resolve())


def verificar_solucao(vertices, arestas, K, x, y):
    """Confere a solucao inteira antes de apresentar suas cores."""
    def binario(var):
        valor = var.value()
        if valor is None or not math.isfinite(valor):
            raise RuntimeError("Variavel sem valor numerico valido.")
        arredondado = round(valor)
        if arredondado not in (0, 1) or abs(valor - arredondado) > 1e-5:
            raise RuntimeError("A solucao retornada nao e binaria.")
        return arredondado

    C = range(1, K + 1)
    ativadas = {c: binario(y[c]) for c in C}
    coloracao = {}
    for v in vertices:
        escolhidas = [c for c in C if binario(x[v][c]) == 1]
        if len(escolhidas) != 1:
            raise RuntimeError(f"Vertice {v} nao recebeu exatamente uma cor.")
        coloracao[v] = escolhidas[0]
        if ativadas[coloracao[v]] != 1:
            raise RuntimeError("Foi usada uma cor desativada.")
    if any(coloracao[u] == coloracao[v] for u, v in arestas):
        raise RuntimeError("Conflito de cores em uma aresta.")
    if any(ativadas[c] < ativadas[c + 1] for c in range(1, K)):
        raise RuntimeError("Ordem das cores desrespeitada.")
    return coloracao, sum(ativadas.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instancia", type=Path, help="Arquivo JSON do grafo")
    parser.add_argument("--tempo", type=float, default=30, help="Limite do solver, em segundos (padrao: 30)")
    parser.add_argument("--saida", type=Path, default=Path("resultados/execucao"),
                        help="Pasta desta execucao; arquivos de mesmo nome sao substituidos")
    args = parser.parse_args()
    if not math.isfinite(args.tempo) or args.tempo <= 0:
        parser.error("--tempo deve ser um numero positivo e finito")
    if pl.__version__ != "4.2.0":
        parser.error('Este codigo usa PuLP 4.2.0: pip install "pulp[cbc]==4.2.0"')

    vertices, arestas = ler_instancia(args.instancia)
    inicio = perf_counter()
    K, coloracao_gulosa = limite_guloso(vertices, arestas)
    assert all(coloracao_gulosa[u] != coloracao_gulosa[v] for u, v in arestas)
    modelo, x, y = construir_modelo(vertices, arestas, K)
    tempo_modelagem = perf_counter() - inicio

    args.saida.mkdir(parents=True, exist_ok=True)
    modelo.writeLP(str(args.saida / "modelo.lp"))
    log = args.saida / "solver.log"
    log.unlink(missing_ok=True)
    configurar_padrao(args.tempo, args.saida)
    inicio = perf_counter()
    stats = modelo.solve()  # O PuLP usa o solver padrao automaticamente.
    tempo_resolucao = perf_counter() - inicio

    coloracao = None
    objetivo = None
    if stats.has_solution:
        coloracao, objetivo = verificar_solucao(vertices, arestas, K, x, y)
        if not math.isclose(objetivo, stats.objective, abs_tol=1e-5):
            raise RuntimeError("Objetivo inconsistente com as variaveis y.")

    otimo = stats.status == pl.LpSolveStatus.Optimal and coloracao is not None
    # Nem todo backend fornece LB pela interface. null significa nao informado.
    LB = stats.best_bound
    if LB is not None and not math.isfinite(LB):
        LB = None
    if otimo:
        LB = float(objetivo)
    gap = None
    if objetivo is not None and LB is not None:
        gap = max(0.0, (objetivo - LB) / abs(objetivo))

    # Tempo do executavel, quando o log do backend o informa.
    # Nao se confunde com a duracao da chamada completa modelo.solve().
    tempo_solver = None
    if log.exists():
        texto_log = log.read_text(encoding="utf-8", errors="replace")
        medidas = re.findall(r"Total time \(Wallclock seconds\):\s*([0-9.]+)", texto_log)
        if medidas:
            tempo_solver = float(medidas[-1])
    resultado = {
        "instancia": str(args.instancia), "sha256_instancia": hashlib.sha256(args.instancia.read_bytes()).hexdigest(), "pulp": pl.__version__, "solver": modelo.solver.name,
        "solver_versao": stats.solver_version,
        "status": stats.status_str, "solucao_validada": coloracao is not None,
        "otimo_comprovado": otimo,
        "vertices": len(vertices), "arestas": len(arestas), "K_guloso": K,
        "variaveis": stats.num_variables, "restricoes": stats.num_constraints,
        "tempo_solver_log_s": tempo_solver,
        "tempo_modelagem_s": tempo_modelagem, "tempo_resolucao_s": tempo_resolucao,
        "limite_tempo_s": args.tempo, "objetivo_UB": objetivo, "limite_inferior_LB": LB,
        "gap_percentual": None if gap is None else 100 * gap,
        "cores_utilizadas": None if coloracao is None else len(set(coloracao.values())),
        "coloracao": coloracao, "coloracao_gulosa": coloracao_gulosa,
    }
    texto = json.dumps(resultado, indent=2, ensure_ascii=False, allow_nan=False)
    (args.saida / "resultado.json").write_text(texto, encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    main()
