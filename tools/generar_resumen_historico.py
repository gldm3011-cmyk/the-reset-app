"""Genera data/historico_resumen.csv a partir de adverse_reports_clean.csv (Prompt 1).
Se ejecuta una sola vez fuera de la app; la app solo lee el resumen (no incluye datos individuales)."""
import sys
import pandas as pd

src = sys.argv[1] if len(sys.argv) > 1 else "adverse_reports_clean.csv"
r = pd.read_csv(src, low_memory=False)
r["incompleto"] = ~(r.age_known & r.weight_known & r.any_outcome_known & r.patient_sex.ne("Unknown"))


def resumen(g):
    s = g[g.serious]; e = g[g.has_error_uso_del_producto]
    return pd.Series({"reportes": len(g), "pct_incompletos": 100 * g.incompleto.mean(), "pct_sin_peso": 100 * (~g.weight_known).mean(),
                      "pct_sin_edad": 100 * (~g.age_known).mean(), "pct_sin_desenlace": 100 * (~g.any_outcome_known).mean(),
                      "pct_graves": 100 * g.serious.mean(), "pct_graves_sin_desenlace": 100 * (~s.any_outcome_known).mean() if len(s) else float("nan"),
                      "pct_error_uso_sin_desenlace": 100 * (~e.any_outcome_known).mean() if len(e) else float("nan")})


tab = r.groupby("generic_name").apply(resumen).reset_index().rename(columns={"generic_name": "medicamento"})
tot = resumen(r).to_frame().T.assign(medicamento="TOTAL")
out = pd.concat([tab, tot], ignore_index=True).round(2)
out.to_csv("data/historico_resumen.csv", index=False)
print(out.to_string(index=False))
