"""Executa os JSONs de uma pasta, um de cada vez, com o mesmo limite de tempo."""
import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("pasta", type=Path)
p.add_argument("--tempo", type=float, default=30)
p.add_argument("--saida", type=Path, default=Path("resultados"))
a = p.parse_args()
a.saida.mkdir(parents=True, exist_ok=True)
programa = Path(__file__).with_name("coloracao.py")
linhas = []
arquivos = sorted(
    a.pasta.glob("*.json"),
    key=lambda caminho: (
        len(json.loads(caminho.read_text(encoding="utf-8-sig"))["vertices"]),
        caminho.stem,
    ),
)
if not arquivos:
    p.error("Nenhum arquivo JSON encontrado na pasta.")
for arquivo in arquivos:
    destino = a.saida / arquivo.stem
    comando = [sys.executable, str(programa), str(arquivo), "--tempo", str(a.tempo),
               "--saida", str(destino)]
    subprocess.run(comando, check=True, stdout=subprocess.DEVNULL)
    r = json.loads((destino / "resultado.json").read_text(encoding="utf-8"))
    linha = {"id": arquivo.stem, **{k:v for k,v in r.items() if k not in ("coloracao", "coloracao_gulosa", "instancia")}}
    linhas.append(linha)
    with (a.saida / "resumo.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(linha)); w.writeheader(); w.writerows(linhas)
    print(f"{arquivo.stem}: {r['status']}; UB={r['objetivo_UB']}; "
          f"LB={r['limite_inferior_LB']}; tempo={r['tempo_resolucao_s']:.3f}s", flush=True)
