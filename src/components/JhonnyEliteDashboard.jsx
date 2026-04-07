export default function JhonnyEliteLiveDashboard() { const matches = [ { league: "Superliga Argentina", country: "Argentina", minute: 67, status: "2T", home: "Instituto Córdoba", away: "Defensa y Justicia", score: "2 - 1", signal: "FUERTE", signalScore: 84, momentum: "Caliente", market: "OVER_MATCH_DYNAMIC", odd: 1.82, expanded: true, }, { league: "Brasil Serie B", country: "Brasil", minute: 58, status: "2T", home: "Goiás", away: "Criciúma", score: "0 - 0", signal: "ACEPTABLE", signalScore: 61, momentum: "Controlado", market: "UNDER_MATCH_DYNAMIC", odd: 1.74, expanded: false, }, { league: "Chile Primera División", country: "Chile", minute: 33, status: "1T", home: "Huachipato", away: "U. de Concepción", score: "1 - 1", signal: "PREMIUM", signalScore: 91, momentum: "Explosivo", market: "OVER_NEXT_15_DYNAMIC", odd: 1.95, expanded: false, }, ];

const signalBadge = { PREMIUM: "bg-emerald-500/15 text-emerald-400 border-emerald-400/30", FUERTE: "bg-sky-500/15 text-sky-400 border-sky-400/30", BUENA: "bg-violet-500/15 text-violet-400 border-violet-400/30", ACEPTABLE: "bg-amber-500/15 text-amber-400 border-amber-400/30", };

const momentumColor = { Explosivo: "text-rose-400", Caliente: "text-orange-400", Controlado: "text-slate-300", };

return ( <div className="min-h-screen bg-[#0b1220] text-white"> <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8"> <header className="sticky top-0 z-20 mb-4 rounded-3xl border border-white/10 bg-[#111827]/90 p-4 shadow-2xl backdrop-blur"> <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between"> <div> <div className="flex items-center gap-3"> <div className="h-11 w-11 rounded-2xl bg-emerald-500/20 p-2 text-emerald-400"> <svg viewBox="0 0 24 24" fill="none" className="h-full w-full" stroke="currentColor" strokeWidth="1.8"> <path d="M4 14l4-4 3 3 7-7" /> <path d="M20 10v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h6" /> </svg> </div> <div> <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">JHONNY_ELITE V16</h1> <p className="text-sm text-slate-400">Panel visual en vivo estilo marcador, optimizado para PC y celular</p> </div> </div> </div>

<div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:w-[520px]">
          {[
            ["Sistema", "Operativo"],
            ["Partidos", "10"],
            ["Señales", "3"],
            ["Top", "6 máximo"],
          ].map(([label, value]) => (
            <div key={label} className="rounded-2xl border border-white/10 bg-white/5 p-3">
              <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
              <div className="mt-1 text-sm font-semibold sm:text-base">{value}</div>
            </div>
          ))}
        </div>
      </div>
    </header>

    <div className="grid gap-4 lg:grid-cols-[290px_minmax(0,1fr)]">
      <aside className="rounded-3xl border border-white/10 bg-[#111827] p-4 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold">Filtros</h2>
          <span className="rounded-full bg-emerald-500/15 px-2.5 py-1 text-xs text-emerald-400">En vivo</span>
        </div>

        <div className="space-y-3">
          <input
            className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none placeholder:text-slate-500"
            placeholder="Buscar partido o liga"
          />

          <select className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none">
            <option>Todas las ligas</option>
            <option>Argentina</option>
            <option>Brasil</option>
            <option>Chile</option>
          </select>

          <select className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none">
            <option>Todas las señales</option>
            <option>Premium</option>
            <option>Fuerte</option>
            <option>Buena</option>
            <option>Aceptable</option>
          </select>

          <select className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none">
            <option>Ordenar por score</option>
            <option>Ordenar por minuto</option>
            <option>Ordenar por cuota</option>
          </select>
        </div>

        <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-4">
          <div className="text-sm font-medium">Resumen operativo</div>
          <div className="mt-3 space-y-2 text-sm text-slate-300">
            <div className="flex items-center justify-between"><span>Ventanas activas</span><span>25-45 / 60-75</span></div>
            <div className="flex items-center justify-between"><span>Mercados</span><span>Over / Under</span></div>
            <div className="flex items-center justify-between"><span>Modo</span><span>Flexible controlado</span></div>
          </div>
        </div>
      </aside>

      <main className="space-y-4">
        {matches.map((match, index) => (
          <section key={`${match.home}-${match.away}`} className="overflow-hidden rounded-3xl border border-white/10 bg-[#111827] shadow-xl">
            <div className="border-b border-white/5 px-4 py-3 sm:px-5">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-400">{match.country}</div>
                  <div className="text-sm font-semibold text-slate-200 sm:text-base">{match.league}</div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`rounded-full border px-3 py-1 text-xs font-medium ${signalBadge[match.signal]}`}>{match.signal}</span>
                  <span className="rounded-full bg-white/5 px-3 py-1 text-xs text-slate-300">Score {match.signalScore}</span>
                  <span className="rounded-full bg-rose-500/10 px-3 py-1 text-xs text-rose-300">{match.status} {match.minute}'</span>
                </div>
              </div>
            </div>

            <div className="px-4 py-4 sm:px-5">
              <div className="grid gap-4 lg:grid-cols-[1.3fr_.9fr]">
                <div>
                  <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 rounded-3xl bg-[#0b1220] p-4">
                    <div>
                      <div className="text-sm text-slate-400">Local</div>
                      <div className="mt-1 text-base font-semibold sm:text-lg">{match.home}</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold tracking-tight sm:text-3xl">{match.score}</div>
                      <div className="mt-1 text-xs text-slate-400">Rank #{index + 1}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm text-slate-400">Visitante</div>
                      <div className="mt-1 text-base font-semibold sm:text-lg">{match.away}</div>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-2 xl:grid-cols-4">
                  <InfoCard label="Mercado" value={match.market} />
                  <InfoCard label="Cuota" value={String(match.odd)} />
                  <InfoCard label="Momentum" value={match.momentum} valueClass={momentumColor[match.momentum]} />
                  <InfoCard label="Estado" value="Activa" valueClass="text-emerald-400" />
                </div>
              </div>

              <details className="group mt-4 rounded-2xl border border-white/10 bg-white/5" open={match.expanded}>
                <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 text-sm font-medium text-slate-200">
                  <span>Ver análisis desplegable</span>
                  <span className="text-slate-400 transition group-open:rotate-180">⌄</span>
                </summary>
                <div className="grid gap-3 border-t border-white/10 px-4 py-4 sm:grid-cols-2 xl:grid-cols-4">
                  <PanelStat title="Lectura IA" value={match.momentum} subtitle="Contexto táctico actual" />
                  <PanelStat title="Riesgo" value={index === 0 ? "3/10" : "5/10"} subtitle="Riesgo operativo" />
                  <PanelStat title="Value" value={index === 0 ? "+9.4%" : "+4.1%"} subtitle="Ventaja estimada" />
                  <PanelStat title="Recomendación" value={match.signal} subtitle="Clasificación final" />
                </div>
              </details>
            </div>
          </section>
        ))}
      </main>
    </div>
  </div>
</div>

); }

function InfoCard({ label, value, valueClass = "text-white" }) { return ( <div className="rounded-2xl border border-white/10 bg-white/5 p-3"> <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div> <div className={mt-1 text-sm font-semibold break-words ${valueClass}}>{value}</div> </div> ); }

function PanelStat({ title, value, subtitle }) { return ( <div className="rounded-2xl border border-white/10 bg-[#0b1220] p-4"> <div className="text-xs uppercase tracking-wide text-slate-400">{title}</div> <div className="mt-2 text-lg font-semibold">{value}</div> <div className="mt-1 text-sm text-slate-400">{subtitle}</div> </div> ); }
