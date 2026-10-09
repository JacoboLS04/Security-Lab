# Pruebas de carga, estrés y "fuerza bruta" sobre el balanceador `opc-lb`

> Complemento de `infraestructura/README.md` (§12.1–§12.3) y de `redes.md`.
> Contiene un **plan de pruebas amplio** sobre el balanceador: ráfagas,
> concurrencia, diferentes endpoints y tamaños de datos, carga sostenida,
> failover bajo carga y una variante "fuerza bruta" con `curl` puro (sin
> instalar nada). **Los umbrales de aprobado/fallo los define el responsable**:
> las tablas traen un valor orientativo y una columna editable.

> **Ámbito y seguridad:** todo se lanza contra `localhost:8080` (balanceador
> local del laboratorio). **No** dirigir estas pruebas a un servicio externo.

---

## 1. Objetivo

Demostrar bajo carga que:

1. El balanceador **reparte** entre ambas réplicas (round-robin, ~50/50) aunque
   aumente el volumen.
2. No se degrada por encima de umbrales razonables para el hardware previsto
   (VM 1 vCPU/1 GiB, límites: réplicas 0.5 CPU/256 MB, `lb` 0.10 CPU/64 MB).
3. El **failover** funciona también bajo carga (detener `app1` a mitad de la
   prueba sin error fatal).
4. Se tienen **métricas medibles** (RPS, latencia, errores, uso CPU/RAM) para el
   informe con umbrales del responsable.

---

## 2. Herramientas

| Herramienta | Instalación en la VM | Ventaja |
|---|---|---|
| **`curl` (bash puro)** | ya disponible | "fuerza bruta" con un bucle, sin instalar nada (§5.1) |
| **`hey`** (Go) | `go install …` o binario | RPS, latencias p50/p95/p99, concurrencia (`-c`, `-n`, `-q`) |
| **`ab`** (Apache Bench) | Debian: `apt-get install apache2-utils` · Rocky: `dnf install httpd-tools` | clásico, `-n`/`-c`/`-k` |
| **`wrk`** | compilar desde GitHub | throughput muy alto, scripting Lua |
| **`siege`** | paquete del SO | modo concurrencia con duración (`-c -t`) |

> En el **host Windows** no hace falta nada: ejecuta las pruebas dentro de la VM
> por SSH (o usa PowerShell, pero `hey`/`ab`/`wrk` son más legibles para latencias).
> Instalar las herramientas **no cambia** el resultado del balanceo; solo lo mide.

---

## 3. Cómo leer los resultados y qué medir

Recoge siempre en tu informe (pantallazo o `tee`):

1. **Peticiones/seg (RPS)** y **tiempos** (p50/p95/p99) que reporta la
   herramienta (`hey`, `ab`).
2. **% de errores** (HTTP no-2xx, timeouts de conexión).
3. **Reparto por réplica** — del `access.log` de Nginx (`$upstream_addr`):
   ```bash
   docker compose logs lb | grep -oE '172\.19\.0\.[0-9]+:5000' | sort | uniq -c
   ```
4. **Uso de CPU/memoria por contenedor** durante la prueba (segundo plano):
   ```bash
   docker stats --no-stream opc-app-1 opc-app-2 opc-lb
   # o en vivo:  watch -n1 'docker stats --no-stream --format "{{.Name}} {{.CPUPerc}} {{.MemUsage}}"'
   ```
5. Estado de los healthchecks antes/después (`docker compose ps`).

### Formato de captura mínimo

```bash
# en 2 terminales de la VM:
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"   # terminal 1
hey -n 5000 -c 50 http://localhost:8080/api/health | tee informe-hey.txt  # terminal 2
```

---

## 4. Plan de pruebas (matriz)

> Valores orientativos. **Columna "umbral que dispongo"** = criterio tuyo de
> aprobado/fallo (se recomienda fijarlo ANTES de correr la prueba).

| ID | Prueba | Comando de referencia (o herramienta) | Qué registrar | Umbral sugerido (editame) | Umbral que dispongo |
|---|---|---|---|---|---|
| P01 | Smoke / correctitud | 10 peticiones secuenciales `for` + `grep X-Replica` | alternancia `.2/.3` | 5/5 (o equilibrio 40–60%) | |
| P02 | Ráfaga básica ("fuerza bruta" curl) | §5.1 (bash/xargs) | total 200, errores, reparto | 0 % err · reparto ~50/50 | |
| P03 | Concurrencia media | `hey -n 2000 -c 25` `/api/health` | RPS, p50/p95/p99, err | p99 < 500 ms · err 0 % | |
| P04 | Concurrencia alta | `hey -n 5000 -c 100 -q 300` `/api/health` | idem + CPU de lb | p99 < 1 s · err < 1 % | |
| P05 | Endpoint pesado (listado) | `hey -n 1000 -c 20` `/api/tickets` | latencia, tamaño resp. | err < 1 % | |
| P06 | Búsquedas distintas | `hey -n 1000 -c 20 'localhost:8080/api/tickets/buscar?q=S360'` | latencia vs query | err < 1 % | |
| P07 | Escritura (POST tickets) | `hey -n 300 -c 10 -m POST -H 'Content-Type: application/json' -d {...}` | respuestas 201, DB por réplica | err < 1 % | |
| P08 | Payloads grandes | `-d` con 100 KB/1 MB (JSON) + `ab -b` | rechazos (413/400), timeouts | acepta hasta 25 m (nginx) | |
| P09 | Carga sostenida (soak) | `hey -n 20000 -c 50` (o `siege -c 25 -t 10m`) | curva de latencia/mem a lo largo del tiempo | sin OOM · latencia estable | |
| P10 | Failover bajo carga | §6: arrancar carga + `stop app1` | errores durante el corte, reintento Nginx | err < 1 % durante 8 s | |
| P11 | `/healthz` bajo carga | `hey -n 5000 -c 100 /healthz` durante P04/P10 | siempre 200 (no toca backend) | siempre 200 | |
| P12 | Estabilidad post-prueba | `docker compose ps` + `docker stats --no-stream` | healthy, sin OOM, métricas base | los 3 healthy | |

> **Nota de interpretación:** con 1 vCPU y el límite del lb en 0.10 CPU, **no
> esperes throughput de producción**. Si P04 te da errores, primero revisa
> CPU/mem del lb (`docker stats`) y luego decide si subes el límite
> (`compose.yaml → lb.deploy.resources`) — cualquier cambio de umbral del
> proyecto queda anotado como decisión del responsable.

### 4.1 Diferentes datos (matriz de cargas)

| Categoría | Ejemplos a probar | Efecto esperado |
|---|---|---|
| Rutas ligeras | `/healthz` (lb propio) · `/api/health` | mínimo; `/healthz` sin backend |
| Lectura | `/api/tickets`, `/api/tickets/buscar?q=<términos distintos>` | SQL por réplica (cada una su DB) |
| Escritura | `POST /api/tickets` (JSON) | 201; **queda en la réplica que la atendió** (bases separadas) |
| Adjuntos | `POST /api/adjuntos` multipart (tamaños 10 KB, 1 MB, 10 MB) | comprueba el límite de Nginx `client_max_body_size 25m` y el de la API |
| Concurrentes mixtos | mezclar GET/POST con `xargs` o scripting Lua de `wrk` | comportamiento realista |

---

## 5. Comandos listos para usar

### 5.1 Fuerza bruta clásica con `curl` (sin instalar nada)

```bash
# [SSH · VM] Bucle simple (secuencial): observa X-Replica
for i in $(seq 1 10); do
  curl -si http://localhost:8080/api/health | grep -i x-replica
done

# [SSH · VM] Fuerza bruta en paralelo (200 peticiones, 20 procesos):
seq 1 200 | xargs -P 20 -I{} curl -s -o /dev/null -w "%{http_code}\n" \
  http://localhost:8080/api/health | sort | uniq -c

# Con peticiones "sucias" (headers varios, de estudiante de pentest):
seq 1 500 | xargs -P 50 -I{} curl -s -o /dev/null -w "%{http_code} %{time_total}\n" \
  -H "X-Test: {}" -H "User-Agent: brute-lab" http://localhost:8080/api/health \
  | awk '{s+=$2; if($1!=200)e++} END{print "media(s):",s/NR,"errores:",e}'
```

### 5.2 `hey` (recomendado para latencias)

```bash
hey -n 5000 -c 100 http://localhost:8080/api/health
#   -n  total de peticiones · -c  concurrencia · -q  RPS objetivo por worker · -m método
hey -n 2000 -c 50 "http://localhost:8080/api/tickets/buscar?q=S360"
hey -n 1000 -c 50 -m POST -H "Content-Type: application/json" \
    -d '{"codigo":"STRESS-HN","solicitante":"lab","desarrollador":"qa","estado":"demo"}' \
    http://localhost:8080/api/tickets
```

### 5.3 `ab` (Apache Bench)

```bash
ab -n 5000 -c 100 -k http://localhost:8080/api/health
ab -n 1000 -c 20 -p cuerpo.json -T application/json http://localhost:8080/api/tickets
```

### 5.4 `siege` (duración fija)

```bash
siege -c 25 -t 5m http://localhost:8080/api/health
```

---

## 6. Failover bajo carga (P10)

```bash
# Terminal 1 (carga): 30 s de tráfico constante
hey -n 20000 -c 50 http://localhost:8080/api/health > /tmp/lb-carga.txt &

# Terminal 2 (corte):
sleep 5 && docker compose stop app1
# esperar que Nginx marque fallo (max_fails/fail_timeout por defecto) y:
docker compose logs lb | grep -E '172\.19\.0\.2.*172\.19\.0\.3|connect.*failed' | head
# Terminal 1 termina -> errores esperados de % bajo; comprobar en el log el reintento

docker compose start app1 && sleep 20
hey -n 1000 -c 25 http://localhost:8080/api/health   # reparto 50/50 de nuevo
docker compose logs lb | grep -oE '172\.19\.0\.[0-9]+:5000' | sort | uniq -c
```

Comportamiento esperado: Nginx **reintenta en la otra réplica** (log
`172.19.0.2:5000, 172.19.0.3:5000`); pueden aparecer unos pocos 502 en plena
ventana de detección (`fail_timeout`), que es la **limitación pasiva** ya
documentada en la guía — y el dato justo para el umbral del informe.

---

## 7. Umbrales tipo (plantilla de informe)

| Métrica | Valor que se mide | Umbral sugerido | Umbral dispuesto por mí | Resultado |
|---|---|---|---|---|
| Disponibilidad | % respuestas 2xx (P04/P10) | ≥ 99 % | | |
| Latencia | p95 `/api/health` (P03) | < 500 ms | | |
| Latencia pico | p99 `/api/health` (P04) | < 1 s | | |
| Reparto | desvío de 50/50 entre réplicas (P01/P02) | ± 10 puntos | | |
| Errores en failover | % no-2xx durante `stop app1` (P10) | < 1 % de la ventana | | |
| Salud | `docker compose ps` post-prueba (P12) | 3× `healthy` | | |
| Estabilidad | CPU/mem del lb tras el test (P12) | vuelve a niveles base | | |

---

## 8. Riesgos y advertencias

- **Recursos de la VM:** 1 vCPU/1 GiB. Test con `-c` alto + `docker stats` puede
  agotar la RAM de la VM (kernel mata procesos). Empieza por `-c 25` y sube
  gradualmente.
- **Destructivo:** P07/P08 escriben datos **en una sola réplica** (lo verás en
  el reparto de `$upstream_addr`). Si quieres estado limpio:
  `docker compose down -v && docker compose up -d` (borra volúmenes).
- **Solo local:** apuntar siempre a `localhost:8080`. No abras el balanceador a
  la LAN para estas pruebas.
- **P12 / OOM:** si algún contenedor muere por memoria durante P09, el
  `/healthz` de su `docker compose ps` lo mostrará; es información válida para
  el informe de umbrales (y motivo documentado para subir límites en
  `compose.yaml`, decisión del responsable).