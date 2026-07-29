# Inventario App — Examen Final CI/CD y Kubernetes

**Sistemas Distribuidos — Universidad Politécnica Salesiana**  
**Integrantes:** Gabriel Alexander Córdova Solórzano y Jordy Espinoza  
**Repositorio:** `UPSGabriel/inventario-app-cicd-final`

Aplicación Node.js/Express de catálogo de inventario utilizada para implementar y demostrar un flujo completo de **Docker + CI/CD + GHCR + Kubernetes + RollingUpdate + Blue-Green**, incluyendo seguridad, probes de salud, pérdida de persistencia y métricas DORA.

---

## 1. Resumen de lo implementado

| Requisito | Implementación en este repositorio |
|---|---|
| Aplicación funcional | Node.js/Express + interfaz web + API REST + JSON local |
| Docker | Dockerfile multi-stage con pruebas durante el build |
| Runtime seguro | Distroless Node.js 22, usuario `nonroot` |
| CI/CD | GitHub Actions con jobs `build-test` y `build-push` |
| Fail-fast | `build-push` depende de `build-test` |
| Registry | GHCR con tag del SHA y `latest` |
| Kubernetes base | Deployment + Service sobre Minikube |
| Réplicas | `2` |
| RollingUpdate | `maxUnavailable: 1` y `maxSurge: 1` |
| Health checks | readiness + liveness sobre `/health` |
| Persistencia | `emptyDir` + JSON local; se demuestra pérdida al recrear el pod |
| Segunda estrategia | Blue-Green con BLUE v1 y GREEN v2 |
| Extra 1 | Kubernetes Secret mediante `secretKeyRef` |
| Extra 2 | Trivy bloquea imágenes con vulnerabilidades `CRITICAL` |
| Extra 3 | `STARTUP_DELAY_SECONDS` + readiness realista |
| Automatización | scripts para switch Blue-Green y smoke test |
| Métricas | Lead Time, Deployment Frequency y Change Failure Rate |

> Se implementaron **los tres componentes adicionales**: Secret, Trivy y readiness con arranque lento. Esto cumple la condición técnica del examen para optar por los **+2 puntos adicionales**.

---

## 2. Arquitectura

```text
Developer
   |
   | git push main
   v
GitHub Actions
   |
   +--> build-test
   |      - npm ci
   |      - npm test
   |
   +--> build-push
          - docker build
          - Trivy CRITICAL
          - push SHA
          - push latest
                  |
                  v
                 GHCR
                  |
                  v
              Minikube
                  |
        +---------+----------+
        |                    |
  RollingUpdate          Blue-Green
  inventario-app      BLUE v1 / GREEN v2
        |                    |
        +---------+----------+
                  |
               Service
                  |
             Navegador/API
```

La aplicación usa un archivo JSON como almacenamiento local. En Kubernetes se monta sobre un volumen `emptyDir`, por lo que cada pod mantiene su propio estado efímero.

---

## 3. Estructura principal del repositorio

```text
.
├── .github/
│   └── workflows/
│       └── ci-cd.yml
├── data/
├── docs/
│   ├── EVIDENCIAS_VERIFICACION.md
│   ├── GUIA_JORDY.md
│   └── INFORME_REFLEXION.md
├── k8s/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── blue-green/
│       ├── blue-deployment.yaml
│       ├── green-deployment.yaml
│       └── service.yaml
├── output/pdf/
│   └── informe-reflexion-cicd.pdf
├── public/
├── scripts/
│   ├── switch-blue-green.ps1
│   ├── smoke-test.ps1
│   └── generate-informe.py
├── Dockerfile
├── server.js
├── db.js
└── README.md
```

---

# GUÍA DE REPRODUCCIÓN PASO A PASO

## 4. Requisitos

- Git
- Node.js + npm
- Docker Desktop
- Minikube
- kubectl
- PowerShell / Warp en Windows

> **Importante:** los ejemplos usan el contexto `minikube`. Si hay otro clúster
> configurado, compruebe primero `kubectl config get-contexts` y añada
> `--context minikube` a los comandos para no modificar el clúster equivocado.

## Entregables principales

- Pipeline: [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml)
- Docker multi-stage: [`Dockerfile`](Dockerfile)
- RollingUpdate: [`k8s/deployment.yaml`](k8s/deployment.yaml) y
  [`k8s/service.yaml`](k8s/service.yaml)
- Blue-Green: [`k8s/blue-green/`](k8s/blue-green/)
- Automatización de Jordy: [`scripts/switch-blue-green.ps1`](scripts/switch-blue-green.ps1)
  y [`scripts/smoke-test.ps1`](scripts/smoke-test.ps1)
- Informe editable: [`docs/INFORME_REFLEXION.md`](docs/INFORME_REFLEXION.md)
- Informe final: [`output/pdf/EspinozaJordy_CordovaGabriel_InformeRelfexion_EXAMENFINAL.pdf`](output/pdf/EspinozaJordy_CordovaGabriel_InformeRelfexion_EXAMENFINAL.pdf)

Clonar:

```powershell
git clone https://github.com/UPSGabriel/inventario-app-cicd-final.git
cd inventario-app-cicd-final
```


Verificar herramientas:

```powershell
node --version
npm --version
docker --version
kubectl version --client
minikube version
```

---

## 5. Aplicación local

Instalar dependencias y ejecutar pruebas:

```powershell
npm ci
npm test
```

La suite actual contiene 5 pruebas que validan salud, versión, creación/listado, eliminación y validación de datos obligatorios.

Ejecutar:

```powershell
npm start
```

En otra terminal:

```powershell
curl.exe -s http://localhost:3000/health
curl.exe -s http://localhost:3000/version
curl.exe -s http://localhost:3000/api/products
```

Respuesta esperada de `/health` cuando la app está lista:

```json
{"status":"ok"}
```

---

## 6. Docker multi-stage y fail-fast

El `Dockerfile` utiliza dos etapas:

1. **build** con `node:22-alpine`: instala dependencias, copia el proyecto, ejecuta `npm test` y elimina dependencias de desarrollo;
2. **runtime** con `gcr.io/distroless/nodejs22-debian13:nonroot`: contiene únicamente lo necesario para ejecutar la aplicación con usuario sin privilegios.

La parte clave es:

```dockerfile
RUN npm ci
COPY . .
RUN npm test
RUN npm prune --omit=dev
```

Si las pruebas fallan, el build de Docker se detiene y no se genera una imagen de producción válida.

Construir localmente:

```powershell
docker build -t inventario-app:local .
```

Ejecutar:

```powershell
docker rm -f inventario-demo 2>$null
docker run -d --name inventario-demo -p 3000:3000 inventario-app:local
```

Validar:

```powershell
curl.exe -s http://localhost:3000/health
curl.exe -s http://localhost:3000/version
curl.exe -s http://localhost:3000/api/products
```

Limpiar:

```powershell
docker rm -f inventario-demo
```

---

## 7. Pipeline CI/CD con GitHub Actions

Workflow:

```text
.github/workflows/ci-cd.yml
```

Se ejecuta con cada `push` a `main` y también permite `workflow_dispatch`.

### Job 1 — `build-test`

```text
checkout
  -> setup Node 20
  -> npm ci
  -> npm test
```

### Job 2 — `build-push`

Está encadenado mediante:

```yaml
needs: build-test
```

Por tanto, si las pruebas fallan, este job no publica la imagen.

Flujo:

```text
docker build
   -> Trivy
   -> login GHCR
   -> push <SHA>
   -> push latest
```

La imagen se publica como:

```text
ghcr.io/upsgabriel/inventario-app-cicd-final:<SHA>
ghcr.io/upsgabriel/inventario-app-cicd-final:latest
```

Descargar la última imagen:

```powershell
docker pull ghcr.io/upsgabriel/inventario-app-cicd-final:latest
```

### Evidencia CI/CD

Durante el desarrollo hubo un run que falló por vulnerabilidades críticas detectadas por Trivy. Se cambió el runtime final a distroless y los siguientes runs completaron correctamente las pruebas, el escaneo y la publicación.

Los últimos cambios integrados por Jordy también ejecutaron el workflow correctamente en `main`.

---

## 8. Trivy — componente adicional 1

Trivy se ejecuta **después de construir la imagen y antes de publicarla**:

```yaml
- name: Escanear imagen con Trivy
  uses: aquasecurity/trivy-action@v0.36.0
  with:
    image-ref: ghcr.io/upsgabriel/inventario-app-cicd-final:${{ github.sha }}
    format: table
    exit-code: "1"
    vuln-type: os,library
    severity: CRITICAL
```

`exit-code: "1"` significa que una vulnerabilidad `CRITICAL` hace fallar el job; el push a GHCR no se ejecuta.

Para reproducir el pipeline basta realizar un cambio versionado y subirlo a `main`:

```powershell
git add .
git commit -m "Prueba de pipeline"
git push origin main
```

Luego revisar:

```text
GitHub -> Actions -> ci-cd
```

---

## 9. Minikube y Kubernetes base

Iniciar Docker Desktop y luego:

```powershell
minikube start --driver=docker
kubectl config current-context
kubectl get nodes
```

El contexto esperado es:

```text
minikube
```

### Crear el Secret antes del Deployment

```powershell
$env:API_KEY_DEMO = [guid]::NewGuid().ToString("N")

kubectl create secret generic inventario-secret `
  --from-literal=API_KEY=$env:API_KEY_DEMO `
  --dry-run=client -o yaml |
  kubectl apply -f -
```

Comprobar sin revelar la credencial:

```powershell
kubectl get secret inventario-secret
kubectl describe secret inventario-secret
```

### Desplegar

```powershell
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl rollout status deployment/inventario-app
kubectl get pods -l app=inventario-app
```

El Deployment usa:

```yaml
replicas: 2
progressDeadlineSeconds: 300
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 1
    maxSurge: 1
```

Comprobar directamente en el clúster:

```powershell
kubectl get deployment inventario-app -o jsonpath="{.spec.strategy.rollingUpdate}"
echo ""
kubectl get deployment inventario-app -o jsonpath="{.spec.progressDeadlineSeconds}"
echo ""
```

Resultado validado durante la práctica:

```text
{"maxSurge":1,"maxUnavailable":1}
300
```

### Abrir el Service

```powershell
minikube service inventario-app --url
```

Guardar la URL obtenida:

```powershell
$env:URL = "http://127.0.0.1:PUERTO"

curl.exe -s "$env:URL/health"
curl.exe -s "$env:URL/version"
curl.exe -s "$env:URL/api/products"
```

---

## 10. Secret de Kubernetes — componente adicional 2

El manifiesto **no contiene la credencial**. La variable se inyecta desde Kubernetes:

```yaml
- name: API_KEY
  valueFrom:
    secretKeyRef:
      name: inventario-secret
      key: API_KEY
```

La app únicamente devuelve en `/version`:

```json
{"secretConfigured":true}
```

Nunca devuelve el valor del Secret.

Además, la interfaz web muestra un indicador visual:

```text
Secret K8s: Activo
```

cuando la variable fue inyectada correctamente.

---

## 11. Readiness realista + arranque lento — componente adicional 3

La app implementa:

```text
STARTUP_DELAY_SECONDS
```

En la versión v2 Kubernetes configura:

```yaml
- name: STARTUP_DELAY_SECONDS
  value: "12"
```

Durante los primeros 12 segundos `/health` responde:

```text
HTTP 503
status: starting
```

Después responde `200` con `status: ok`.

El readiness probe consulta `/health`:

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: http
  initialDelaySeconds: 1
  periodSeconds: 2
  timeoutSeconds: 2
  failureThreshold: 10
```

La liveness comienza después:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: http
  initialDelaySeconds: 20
  periodSeconds: 10
```

Demostración:

```powershell
kubectl get pods -l app=inventario-app -w
```

En otra terminal:

```powershell
kubectl describe pod NOMBRE_DEL_POD
```

Durante la práctica se observó un evento de readiness con HTTP `503` durante el arranque y posteriormente el pod quedó `1/1 Running`.

### ¿Por qué más réplicas no solucionan una readiness incorrecta?

Porque crear más pods no hace que una instancia que todavía está inicializando pueda recibir tráfico. El readiness probe es el mecanismo que mantiene al pod fuera de los endpoints del Service hasta que realmente está preparado.

---

## 12. Prueba de persistencia

La aplicación usa:

```text
DB_PATH=/app/data/products.json
```

montado sobre:

```yaml
emptyDir: {}
```

El objetivo es demostrar que los datos escritos dentro de un pod desaparecen cuando ese pod es eliminado.

### Crear un producto en un pod concreto

Terminal 1:

```powershell
$env:POD = (kubectl get pods -l app=inventario-app -o jsonpath="{.items[0].metadata.name}")
kubectl port-forward pod/$env:POD 3001:3000
```

Terminal 2:

```powershell
$body = @{
  name  = "Producto prueba persistencia"
  sku   = "PERSIST-001"
  stock = 10
  price = 25.50
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://127.0.0.1:3001/api/products" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

Comprobar:

```powershell
curl.exe -s http://127.0.0.1:3001/api/products
```

Después eliminar el pod:

```powershell
kubectl delete pod $env:POD
kubectl wait --for=delete pod/$env:POD --timeout=120s
kubectl wait --for=condition=Ready pod -l app=inventario-app --timeout=120s
```

Conectarse al pod sustituto y consultar otra vez. El producto `PERSIST-001` ya no aparece.

### Explicación

`emptyDir` existe durante la vida del pod. Cuando Kubernetes elimina ese pod, también elimina ese volumen y el pod sustituto obtiene uno nuevo. Por eso esta arquitectura no ofrece persistencia real entre recreaciones.

---

# ESTRATEGIA ADICIONAL — BLUE-GREEN

## 13. ¿Por qué Blue-Green?

Se eligió Blue-Green porque nuestra aplicación permite identificar claramente la versión activa mediante `/version`:

```json
{
  "version": "v1",
  "color": "blue",
  "hostname": "..."
}
```

o:

```json
{
  "version": "v2",
  "color": "green",
  "hostname": "..."
}
```

BLUE permanece disponible mientras GREEN se valida. El cambio de tráfico se realiza modificando únicamente el selector del Service, por lo que el rollback también es inmediato.

Para esta práctica es más fácil demostrar un corte determinista del 100 % que un Canary, donde sería necesario observar una distribución estadística del tráfico.

### Desventaja

Durante Blue-Green ambas versiones consumen recursos al mismo tiempo. Además, con el JSON local/`emptyDir`, BLUE y GREEN no comparten estado. En producción sería recomendable utilizar una base de datos externa o persistencia compartida.

---

## 14. Desplegar BLUE y GREEN

Manifiestos:

```text
k8s/blue-green/blue-deployment.yaml
k8s/blue-green/green-deployment.yaml
k8s/blue-green/service.yaml
```

Aplicar:

```powershell
kubectl apply -f k8s/blue-green/blue-deployment.yaml
kubectl apply -f k8s/blue-green/green-deployment.yaml
kubectl apply -f k8s/blue-green/service.yaml

kubectl rollout status deployment/inventario-app-blue
kubectl rollout status deployment/inventario-app-green
kubectl get pods -l app=inventario-bg --show-labels
```

Se esperan cuatro pods:

```text
2 BLUE  -> version=v1, slot=blue
2 GREEN -> version=v2, slot=green
```

El Service inicia apuntando a BLUE:

```powershell
kubectl get svc inventario-blue-green -o jsonpath="{.spec.selector.slot}"
```

Resultado esperado:

```text
blue
```

---

## 15. Abrir el Service Blue-Green

En una terminal que debe permanecer abierta:

```powershell
minikube service inventario-blue-green --url
```

Ejemplo:

```text
http://127.0.0.1:49519
```

En otra terminal guardar la URL devuelta:

```powershell
$env:BGURL = "http://127.0.0.1:PUERTO"
```

No se debe copiar el puerto del ejemplo: Minikube puede asignar uno diferente en cada ejecución.

---

## 16. Automatización Blue-Green desarrollada por Jordy

### Cambiar BLUE -> GREEN

```powershell
.\scripts\switch-blue-green.ps1 -Target green -Context minikube
```

El script:

1. fija explícitamente el contexto y namespace;
2. espera que el Deployment destino esté disponible;
3. cambia el selector del Service;
4. confirma el nuevo selector;
5. espera la convergencia de `EndpointSlice`;
6. comprueba que todos los pods que reciben tráfico pertenezcan al slot destino;
7. ejecuta rollback automático si la validación posterior al corte falla.

Resultado real obtenido en Minikube:

```text
Selector activo: slot=green
Pods que reciben trafico:
  - inventario-app-green-...
  - inventario-app-green-...
Cambio Blue-Green completado correctamente.
```

---

## 17. Smoke test de GREEN

```powershell
.\scripts\smoke-test.ps1 `
  -BaseUrl $env:BGURL `
  -ExpectedVersion v2 `
  -ExpectedColor green
```

Resultado real validado:

```text
[OK] Health status=ok
[OK] Version=v2 Color=green Pod=inventario-app-green-...
[OK] Products respondio correctamente (3 producto(s))
Smoke test completado correctamente.
```

El mismo Service ahora entrega únicamente la versión GREEN.

---

## 18. Rollback GREEN -> BLUE

```powershell
.\scripts\switch-blue-green.ps1 -Target blue -Context minikube
```

Resultado real validado:

```text
Selector activo: slot=blue
Pods que reciben trafico:
  - inventario-app-blue-...
  - inventario-app-blue-...
Cambio Blue-Green completado correctamente.
```

Confirmar con el mismo Service:

```powershell
.\scripts\smoke-test.ps1 `
  -BaseUrl $env:BGURL `
  -ExpectedVersion v1 `
  -ExpectedColor blue
```

Resultado:

```text
[OK] Health status=ok
[OK] Version=v1 Color=blue Pod=inventario-app-blue-...
[OK] Products respondio correctamente (3 producto(s))
Smoke test completado correctamente.
```

Esto demuestra el ciclo completo:

```text
BLUE v1
   |
   | switch
   v
GREEN v2
   |
   | rollback
   v
BLUE v1
```

---

# MÉTRICAS DORA

## 19. Lead Time for Changes

Se utilizaron timestamps reales del historial Git y del momento en que cada cambio quedó disponible en Kubernetes.

### Cambio 1 — runtime distroless

```text
Commit:     285e565...
Commit at:  2026-07-23 18:57:46 -05:00
Disponible: 2026-07-25 21:34:57.195746 -05:00
Lead Time:  50 h 37 min 11 s
```

### Cambio 2 — arranque lento + Secret

```text
Commit:     a07b964...
Commit at:  2026-07-26 00:44:14 -05:00
Disponible: 2026-07-26 01:09:59.642816 -05:00
Lead Time:  25 min 46 s
```

Promedio aproximado:

```text
25.52 horas
```

---

## 20. Deployment Frequency

Se contabilizaron tres promociones exitosas durante dos días de trabajo de despliegue:

```text
1. v1 estable desplegada en Kubernetes
2. v2 promovida mediante RollingUpdate
3. v2 GREEN promovida al tráfico mediante Blue-Green
```

```text
Deployment Frequency = 3 promociones / 2 días
                     = 1.5 promociones por día
```

---

## 21. Change Failure Rate

Intentos considerados:

```text
1. despliegue inicial que requirió corrección    -> fallo
2. v1 corregida                                  -> éxito
3. v2 mediante RollingUpdate                     -> éxito
4. promoción GREEN mediante Blue-Green           -> éxito
```

```text
CFR = 1 / 4 * 100
    = 25 %
```

No se contabilizan como fallos de despliegue:

- el error de quoting de PowerShell al intentar `kubectl patch`;
- el `503` de readiness durante el arranque lento, porque fue intencional;
- el rollback BLUE-Green realizado como demostración controlada.

---

# PROBLEMAS REALES Y SOLUCIONES

## 22. Problemas encontrados

### Trivy bloqueó la imagen inicial

La imagen inicial presentó vulnerabilidades críticas. El pipeline falló antes del push.

**Solución:** cambiar el runtime a distroless y non-root.

### Permisos de `emptyDir` con distroless non-root

El proceso con UID/GID 65532 no podía escribir correctamente en `/app/data`.

**Solución:**

```yaml
runAsUser: 65532
runAsGroup: 65532
fsGroup: 65532
```

manteniendo `readOnlyRootFilesystem: true` y montando `/app/data` como volumen escribible.

### `progress deadline exceeded`

Durante una iteración Kubernetes superó el tiempo de progreso mientras se diagnosticaba el rollout.

**Solución:** revisar pods/eventos, corregir permisos y posteriormente establecer:

```yaml
progressDeadlineSeconds: 300
```

para tolerar mejor pulls iniciales de GHCR en el entorno local.

### Timeout temporal de Docker Hub en GitHub Actions

Un run encontró un timeout externo al descargar una imagen base. Un rerun posterior terminó correctamente.

### `kubectl patch` y PowerShell

El JSON del patch fue interpretado incorrectamente por PowerShell.

**Solución final:** usar `kubectl set selector`, y posteriormente automatizar el flujo mediante `scripts/switch-blue-green.ps1`.

---

# TRABAJO EN PAREJA

## 23. Contribuciones

### Gabriel

Implementación principal de:

- aplicación y pruebas;
- Docker multi-stage;
- pipeline CI/CD;
- Trivy/GHCR;
- Kubernetes base;
- RollingUpdate;
- Secret y readiness;
- persistencia;
- primera implementación y pruebas Blue-Green;
- documentación y evidencias iniciales.

### Jordy

Contribuciones versionadas en Git:

- `scripts/switch-blue-green.ps1`;
- `scripts/smoke-test.ps1`;
- integración de automatizaciones y documentación;
- mejora visual para mostrar el estado del Secret en la interfaz;
- ajuste de `progressDeadlineSeconds`;
- actualización del informe y documentación.

Los commits recientes aparecen en el historial con ambos autores, demostrando participación de los dos integrantes.

---

# DEMOSTRACIÓN RÁPIDA PARA EL PROFESOR

## 24. Secuencia recomendada

### 1. Mostrar CI/CD

Abrir:

```text
GitHub -> Actions -> ci-cd
```

Mostrar jobs verdes y explicar:

```text
build-test -> build-push
                 |
                 +-> Docker build
                 +-> Trivy
                 +-> GHCR
```

### 2. Mostrar RollingUpdate

```powershell
kubectl get deployment inventario-app
kubectl get deployment inventario-app -o jsonpath="{.spec.strategy.rollingUpdate}"
echo ""
```

Debe verse:

```text
2/2
{"maxSurge":1,"maxUnavailable":1}
```

### 3. Mostrar Secret

```powershell
kubectl get secret inventario-secret
kubectl describe secret inventario-secret
```

No mostrar el valor de la credencial.

### 4. Mostrar BLUE/GREEN

```powershell
kubectl get pods -l app=inventario-bg --show-labels
kubectl get svc inventario-blue-green -o jsonpath="{.spec.selector.slot}"
```

### 5. Cambiar a GREEN

```powershell
<<<<<<< HEAD
git show -s --format="%H | %cI | %s" SHA_DEL_COMMIT
```

Y, justo cuando el cambio quedó corriendo correctamente en el clúster:

```powershell
Get-Date -Format o
```

Registros utilizados durante la práctica:

- Cambio `285e565...`: commit `2026-07-23T18:57:46-05:00`; ejecución verificada en el clúster `2026-07-25T21:34:57.195746-05:00`.
- Cambio `a07b964...`: commit `2026-07-26T00:44:14-05:00`; ejecución verificada en el clúster `2026-07-26T01:09:59.642816-05:00`.

Resultados calculados:

- lead time de `285e565...`: **50 h 37 min 11.196 s**;
- lead time de `a07b964...`: **25 min 45.643 s**;
- lead time promedio: **25.5246 h**;
- frecuencia: **2 promociones exitosas / 2 días = 1 por día**;
- change failure rate simplificado: **1 intento corregido / 3 intentos
  registrados = 33.3 %**.

Los cambios de selector Blue-Green no cuentan como una nueva promoción porque no
cambian la imagen de los Deployments ya disponibles. El desarrollo completo y la
reflexión están en [`docs/INFORME_REFLEXION.md`](docs/INFORME_REFLEXION.md) y en
[`output/pdf/EspinozaJordy_CordovaGabriel_InformeRelfexion_EXAMENFINAL.pdf`](output/pdf/EspinozaJordy_CordovaGabriel_InformeRelfexion_EXAMENFINAL.pdf).

## 11. Problemas reales observados

Durante la implementación se documentaron, entre otros:

- fallo de Trivy por vulnerabilidades críticas de la imagen inicial; se redujo la superficie usando runtime distroless;
- permisos de escritura del volumen con runtime non-root; se corrigió mediante contexto de seguridad/grupo del pod;
- `kubectl rollout status` alcanzó el progress deadline durante una iteración y se diagnosticó con `kubectl describe pods`;
- un build de Actions falló por timeout al acceder a Docker Hub y el rerun posterior terminó correctamente;
- el JSON de `kubectl patch` fue interpretado incorrectamente por PowerShell; para el corte Blue-Green se usó `kubectl set selector`, que evita el problema de quoting.

Los errores forman parte de la evidencia del proceso de diagnóstico y corrección.

## 12. Contribución funcional de Jordy

Jordy agregó dos automatizaciones reproducibles:

```powershell
# Corte seguro con validación del Deployment y de los endpoints
=======
>>>>>>> d06967e11d8d28a089684e82c4fe3252424e6249
.\scripts\switch-blue-green.ps1 -Target green -Context minikube
```

### 6. Validar GREEN

```powershell
.\scripts\smoke-test.ps1 `
  -BaseUrl $env:BGURL `
  -ExpectedVersion v2 `
  -ExpectedColor green
```

### 7. Rollback a BLUE

```powershell
.\scripts\switch-blue-green.ps1 -Target blue -Context minikube
```

### 8. Validar BLUE

```powershell
.\scripts\smoke-test.ps1 `
  -BaseUrl $env:BGURL `
  -ExpectedVersion v1 `
  -ExpectedColor blue
```

Con esta secuencia se demuestra el pipeline, Kubernetes, los componentes adicionales, el corte Blue-Green y el rollback usando la misma URL del Service.

---

## 25. Endpoints

| Método | Ruta | Función |
|---|---|---|
| GET | `/health` | Salud/readiness de la aplicación |
| GET | `/version` | Versión, color, hostname, delay y estado del Secret |
| GET | `/api/products` | Lista productos |
| GET | `/api/products/:id` | Obtiene producto |
| POST | `/api/products` | Crea producto |
| PATCH | `/api/products/:id` | Actualiza producto |
| DELETE | `/api/products/:id` | Elimina producto |
| GET | `/` | Interfaz web |

---

## 26. Variables de entorno

| Variable | Default | Uso |
|---|---:|---|
| `PORT` | `3000` | Puerto HTTP |
| `APP_VERSION` | `v1` | Versión visible de la app |
| `APP_COLOR` | `blue` | Identificador visual BLUE/GREEN |
| `SIMULATE_FAILURE` | `false` | Fuerza fallo de `/health` |
| `DB_PATH` | `./data/products.json` | Ruta del JSON |
| `STARTUP_DELAY_SECONDS` | `0` | Simula arranque lento |
| `API_KEY` | vacío | Credencial ficticia inyectada desde Secret |

---

## 27. Entregables

- [`Dockerfile`](Dockerfile)
- [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml)
- [`k8s/deployment.yaml`](k8s/deployment.yaml)
- [`k8s/service.yaml`](k8s/service.yaml)
- [`k8s/blue-green/`](k8s/blue-green/)
- [`scripts/switch-blue-green.ps1`](scripts/switch-blue-green.ps1)
- [`scripts/smoke-test.ps1`](scripts/smoke-test.ps1)
- [`docs/INFORME_REFLEXION.md`](docs/INFORME_REFLEXION.md)
- [`output/pdf/informe-reflexion-cicd.pdf`](output/pdf/informe-reflexion-cicd.pdf)
- [`docs/EVIDENCIAS_VERIFICACION.md`](docs/EVIDENCIAS_VERIFICACION.md)

Regenerar el PDF del informe:

```powershell
py -m pip install -r requirements-report.txt
py scripts/generate-informe.py
```

---

## Resultado final

El proyecto demuestra un flujo completo y reproducible de entrega de software:

```text
Código
 -> pruebas
 -> build Docker
 -> escaneo de seguridad
 -> publicación GHCR
 -> despliegue Kubernetes
 -> RollingUpdate
 -> BLUE/GREEN
 -> smoke test
 -> rollback
```

El estado final verificado mantiene **BLUE v1** sirviendo tráfico, con GREEN v2 disponible para un nuevo corte cuando sea necesario.
