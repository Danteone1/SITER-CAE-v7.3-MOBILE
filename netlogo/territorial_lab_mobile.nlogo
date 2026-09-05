; SITER-CAE v7.3 — Territorial ABM / BehaviorSpace REAL
; Entrada: territorial.csv, network.csv
; Salida: BehaviorSpace metrics -> netlogo_results.csv
; No usa resultados dummy.

extensions [csv]

globals [
  beta-voter epsilon mu epsilon-repulsion mu-rep
  coupling-saf field-pressure p-intra p-inter shock
  budget-dinero budget-horas fatigue-factor seed
  entropy polarization fragmentation consensus gini-influence density
  mean-opinion variance-opinion
]

turtles-own [
  territorial-id alcaldia poblacion opinion temperatura
  capital-social acceso-info influencia-liderazgo arraigo
  nivel-movilizacion desconfianza exposicion-problema saf-skill
  influencia resistencia prioridad lat lon fatiga capacidad-coord
]

links-own [weight]

to setup
  clear-all
  if not is-number? seed [ set seed 42 ]
  random-seed seed
  load-territorial
  load-network
  if count links = 0 and count turtles > 1 [
    ask turtles [
      let k min (list 6 (count other turtles))
      if k > 0 [ create-links-with n-of k other turtles ]
    ]
  ]
  update-metrics
  reset-ticks
end

to load-territorial
  if not file-exists? "territorial.csv" [ stop ]
  file-open "territorial.csv"
  let header csv:from-row file-read-line
  while [not file-at-end?] [
    let row csv:from-row file-read-line
    if length row >= 18 [
      create-turtles 1 [
        set territorial-id item 0 row
        set alcaldia item 1 row
        set poblacion read-from-string item 2 row
        set opinion read-from-string item 3 row
        set temperatura read-from-string item 4 row
        set capital-social read-from-string item 5 row
        set acceso-info read-from-string item 6 row
        set influencia-liderazgo read-from-string item 7 row
        set arraigo read-from-string item 8 row
        set nivel-movilizacion read-from-string item 9 row
        set desconfianza read-from-string item 10 row
        set exposicion-problema read-from-string item 11 row
        set saf-skill read-from-string item 12 row
        set influencia read-from-string item 13 row
        set resistencia read-from-string item 14 row
        set prioridad read-from-string item 15 row
        set lat read-from-string item 16 row
        set lon read-from-string item 17 row
        set fatiga 0
        set capacidad-coord 0.5
        setxy random-xcor random-ycor
      ]
    ]
  ]
  file-close
end

to load-network
  if not file-exists? "network.csv" [ stop ]
  file-open "network.csv"
  let header csv:from-row file-read-line
  while [not file-at-end?] [
    let row csv:from-row file-read-line
    if length row >= 2 [
      let src item 0 row
      let tgt item 1 row
      let w 0.5
      if length row >= 3 [ set w read-from-string item 2 row ]
      let a one-of turtles with [territorial-id = src]
      let b one-of turtles with [territorial-id = tgt]
      if a != nobody and b != nobody and a != b [
        ask a [
          if not link-neighbor? b [ create-link-with b [ set weight w ] ]
        ]
      ]
    ]
  ]
  file-close
end

to go
  if count turtles = 0 [ stop ]
  if budget-dinero <= 0 or budget-horas <= 0 [ stop ]
  ask turtles [
    let target one-of link-neighbors
    if target != nobody [
      let diff opinion - [opinion] of target
      let attraction-threshold epsilon * (1 + coupling-saf * [capital-social] of target * 0.25)
      if abs diff < attraction-threshold [
        if resistencia < 0.6 or (count link-neighbors > 0 and (count link-neighbors with [opinion > 0.33] / count link-neighbors) >= (resistencia * 0.7 + 0.3)) [
          let delta beta-voter * mu * diff
          ask target [ set opinion opinion + delta * 0.5 ]
          set fatiga min (list 1 (fatiga + fatigue-factor))
        ]
      ]
      if abs diff > epsilon-repulsion [
        ask target [ set opinion opinion - mu-rep * diff * 0.5 ]
      ]
    ]
    set opinion max (list -1 (min (list 1 (opinion + field-pressure * 0.01 + shock * (random-float 2 - 1) * 0.01))))
  ]
  ask turtles [ set fatiga fatiga * 0.95 ]
  update-metrics
  tick
  if ticks >= 100 [ stop ]
end

to update-metrics
  if count turtles = 0 [
    set mean-opinion 0
    set variance-opinion 0
    set entropy 0
    set polarization 0
    set fragmentation 0
    set consensus 0
    set gini-influence 0
    set density 0
    stop
  ]
  set mean-opinion mean [opinion] of turtles
  set variance-opinion variance [opinion] of turtles
  set polarization variance-opinion
  let simpat count turtles with [opinion > 0.33]
  let opos count turtles with [opinion < -0.33]
  let indec count turtles - simpat - opos
  let total count turtles
  let p1 simpat / total
  let p2 opos / total
  let p3 indec / total
  set entropy 0
  if p1 > 0 [ set entropy entropy - p1 * ln p1 ]
  if p2 > 0 [ set entropy entropy - p2 * ln p2 ]
  if p3 > 0 [ set entropy entropy - p3 * ln p3 ]
  set fragmentation (ifelse-value (p1 > 0.1 and p2 > 0.1 and p3 > 0.1) [3] [ifelse-value (p1 > 0.1 and p2 > 0.1) [2] [1]])
  set consensus (ifelse-value (max (list p1 p2 p3) > 0.6) [1] [0])
  ifelse count turtles > 1 [
    set density (count links / (count turtles * (count turtles - 1) / 2))
  ] [ set density 0 ]
  set gini-influence gini-list [influencia] of turtles
end

to-report gini-list [values]
  let xs sort values
  let n length xs
  if n = 0 [ report 0 ]
  let s sum xs
  if s = 0 [ report 0 ]
  let weighted 0
  let i 1
  foreach xs [x ->
    set weighted weighted + i * x
    set i i + 1
  ]
  report ((2 * weighted) / (n * s)) - ((n + 1) / n)
end

; Variables controladas por BehaviorSpace:
; beta-voter epsilon mu epsilon-repulsion mu-rep coupling-saf field-pressure
; p-intra p-inter shock budget-dinero budget-horas fatigue-factor seed@#$#@#$#@GRAPHICS-WINDOW
210
10
760
560
-1
-1
12.0
1
10
1
1
1
0
1
1
1
-16
16
-16
16
0
0
1
ticks
30.0

BUTTON
10
10
100
43
SETUP
setup
NIL
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

BUTTON
110
10
200
43
GO
T
NIL
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

MONITOR
10
60
200
105
MEAN OPINION
mean-opinion
3
1
11

MONITOR
10
115
200
160
POLARIZATION
polarization
3
1
11

MONITOR
10
170
200
215
FRAGMENTATION
fragmentation
0
1
11

MONITOR
10
225
200
270
CONSENSUS
consensus
0
1
11
@#$#@#$#@## SITER-CAE v7.3-MOBILE

Modelo basado en agentes para exploración sociofísica territorial.

## CÓMO FUNCIONA
Los agentes representan unidades territoriales sintéticas y actualizan opinión, interacción, fatiga e influencia mediante reglas de atracción y repulsión.

## CÓMO USARLO
Pulse SETUP para inicializar y GO para ejecutar la dinámica. Los indicadores se muestran en los monitores.

## NOTA CIENTÍFICA
Los datos incluidos son sintéticos y sirven para validar la arquitectura del modelo. No constituyen predicciones electorales ni inferencias sobre personas reales.
@#$#@#$#@default
false
0
polygon -7500403 true true 0 0 4 0
@#$#@#$#@NetLogo 6.4.0@#$#@#$#@setup
go
@#$#@#$#@@#$#@#$#@<experiments></experiments>@#$#@#$#@@#$#@#$#@default
true
0
line -7500403 true 0 1 0
@#$#@#$#@false@#$#@#$#@
