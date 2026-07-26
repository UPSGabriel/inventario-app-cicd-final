# Inventario App — CI/CD y Kubernetes

Práctica de Sistemas Distribuidos: aplicación Node.js/Express con catálogo de inventario, Docker multi-stage, GitHub Actions, GHCR, Kubernetes sobre Minikube, RollingUpdate, Blue-Green y buenas prácticas de seguridad/disponibilidad.

## Arquitectura y componentes

- Aplicación Node.js/Express con interfaz web y API REST.
- Persistencia local en JSON (`data/products.json`).
- Dockerfile multi-stage: ejecuta `npm test` durante el build y usa runtime distroless sin root.
- GitHub Actions con dos jobs encadenados: pruebas y build/scan/push.
- Imagen publicada en `ghcr.io/upsgabriel/inventario-app-cicd-final` con tag SHA y `latest`.
- Kubernetes: 2 réplicas, RollingUpdate, readiness/liveness probes, recursos y contexto de seguridad.
- Estrategia adicional: Blue-Green con dos Deployments y un Service que cambia de selector.
- Tres componentes adicionales implementados: Secret, Trivy y arranque lento configurable.

## Requisitos

- Node.js y npm
- Docker Desktop
- Minikube
- kubectl
- PowerShell/Warp en Windows

## 1. Ejecutar y probar localmente

```powershell
npm ci
npm test
npm start
```

En otra terminal:

```powershell
curl.exe -s http://localhost:3000/health
curl.exe -s http://localhost:3000/version
curl.exe -s http://localhost:3000/api/products
```

## 2. Docker multi-stage

Construir la imagen local:

```powershell
docker build -t inventario-app:v1 --build-arg APP_VERSION=v1 --build-arg APP_COLOR=blue .
```

El build falla si `npm test` falla.

Ejecutar:

```powershell
docker rm -f inventario-demo 2>$null
docker run -d --name inventario-demo -p 3000:3000 inventario-app:v1
docker ps
```

Validar:

```powershell
curl.exe -s http://localhost:3000/
curl.exe -s http://localhost:3000/health
curl.exe -s http://localhost:3000/version
curl.exe -s http://localhost:3000/api/products
```

Eliminar contenedor de prueba:

```powershell
docker rm -f inventario-demo
```

## 3. Pipeline CI/CD

Workflow: `.github/workflows/ci-cd.yml`.

Cada push a `main` ejecuta:

1. `npm ci`
2. `npm test`
3. build de la imagen Docker
4. escaneo Trivy con fallo ante vulnerabilidades `CRITICAL`
5. login en GHCR
6. publicación con `${github.sha}` y `latest`

La imagen puede descargarse con:

```powershell
docker pull ghcr.io/upsgabriel/inventario-app-cicd-final:latest
```

## 4. Minikube y despliegue RollingUpdate

Iniciar Minikube:

```powershell
minikube start --driver=docker
kubectl get nodes
```

Aplicar manifiestos base:

```powershell
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl rollout status deployment/inventario-app
kubectl get pods -l app=inventario-app
```

Abrir el Service:

```powershell
minikube service inventario-app --url
```

Guardar la URL devuelta, por ejemplo:

```powershell
$env:URL = "http://127.0.0.1:PUERTO"
curl.exe -s "$env:URL/health"
curl.exe -s "$env:URL/version"
curl.exe -s "$env:URL/api/products"
```

## 5. Persistencia local y recreación de pod

La aplicación usa un JSON local dentro del pod. Para demostrar su comportamiento, crear un producto en un pod concreto mediante port-forward:

```powershell
$env:POD = (kubectl get pods -l app=inventario-app -o jsonpath="{.items[0].metadata.name}")
kubectl port-forward pod/$env:POD 3001:3000
```

En otra terminal:

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

Comprobar el producto y eliminar el pod:

```powershell
curl.exe -s http://127.0.0.1:3001/api/products
kubectl delete pod $env:POD
kubectl get pods -l app=inventario-app -w
```

Al recrearse el pod, el producto agregado al almacenamiento local del pod eliminado ya no existe. Esto es esperado con `emptyDir`/almacenamiento local y se documenta como observación de persistencia.

## 6. Componente adicional: Secret de Kubernetes

La credencial ficticia nunca se escribe en archivos versionados.

Crear un valor aleatorio y el Secret:

```powershell
$env:API_KEY_DEMO = [guid]::NewGuid().ToString("N")
kubectl create secret generic inventario-secret --from-literal=API_KEY=$env:API_KEY_DEMO
```

Verificar sin revelar el valor:

```powershell
kubectl get secret inventario-secret
kubectl describe secret inventario-secret
```

El Deployment consume el Secret con `secretKeyRef`. `/version` solo informa si está configurado, no devuelve la credencial.

## 7. Componente adicional: Trivy

El workflow escanea la imagen antes de publicarla:

```yaml
severity: CRITICAL
exit-code: "1"
```

Si Trivy encuentra una vulnerabilidad crítica, el job falla y la imagen no se publica. La imagen runtime usa distroless para reducir superficie de ataque.

## 8. Componente adicional: arranque lento y readiness

La aplicación acepta:

```text
STARTUP_DELAY_SECONDS
```

La versión v2 se desplegó con 12 segundos de arranque simulado. Durante ese intervalo `/health` devuelve HTTP 503 y luego cambia a 200.

Verificar:

```powershell
kubectl get pods -l app=inventario-app -w
kubectl describe pod NOMBRE_DEL_POD
curl.exe -s "$env:URL/version"
```

La evidencia esperada incluye un evento semejante a:

```text
Readiness probe failed: HTTP probe failed with statuscode: 503
```

seguido de pods `1/1 Running` y rollout exitoso. Aumentar solo el número de réplicas no corrige una readiness mal configurada: únicamente crearía más pods que aún no están listos; el probe debe representar correctamente cuándo la aplicación puede recibir tráfico.

## 9. Blue-Green

Manifiestos:

```text
k8s/blue-green/blue-deployment.yaml
k8s/blue-green/green-deployment.yaml
k8s/blue-green/service.yaml
```

Levantar ambos ambientes:

```powershell
kubectl apply -f k8s/blue-green/blue-deployment.yaml
kubectl apply -f k8s/blue-green/green-deployment.yaml
kubectl apply -f k8s/blue-green/service.yaml
kubectl rollout status deployment/inventario-app-blue
kubectl rollout status deployment/inventario-app-green
kubectl get pods -l app=inventario-bg --show-labels
```

El Service comienza en BLUE:

```powershell
kubectl get svc inventario-blue-green -o jsonpath="{.spec.selector.slot}"
kubectl get endpoints inventario-blue-green
minikube service inventario-blue-green --url
```

Guardar la URL:

```powershell
$env:BGURL = "http://127.0.0.1:PUERTO"
curl.exe -s "$env:BGURL/version"
```

BLUE debe responder `v1` / `blue`.

Probar GREEN antes del corte:

```powershell
kubectl port-forward deployment/inventario-app-green 3003:3000
```

En otra terminal:

```powershell
curl.exe -s http://127.0.0.1:3003/health
curl.exe -s http://127.0.0.1:3003/version
```

GREEN debe responder `v2` / `green`.

### Corte BLUE -> GREEN

```powershell
kubectl set selector service/inventario-blue-green app=inventario-bg,slot=green
kubectl get svc inventario-blue-green -o jsonpath="{.spec.selector.slot}"
kubectl get endpoints inventario-blue-green
curl.exe -s "$env:BGURL/version"
```

Varias peticiones demuestran que el tráfico llega únicamente a pods GREEN:

```powershell
1..4 | ForEach-Object {
  curl.exe -s "$env:BGURL/version"
  echo ""
}
```

### Rollback GREEN -> BLUE

```powershell
kubectl set selector service/inventario-blue-green app=inventario-bg,slot=blue
kubectl get svc inventario-blue-green -o jsonpath="{.spec.selector.slot}"
kubectl get endpoints inventario-blue-green
curl.exe -s "$env:BGURL/version"
```

El rollback es inmediato porque BLUE permanece desplegado y solo cambia el selector del Service.

## 10. Métricas DORA — cómo obtener evidencia verificable

Para cada cambio desplegado, registrar el timestamp del commit:

```powershell
git show -s --format="%H | %cI | %s" SHA_DEL_COMMIT
```

Y, justo cuando el cambio quedó corriendo correctamente en el clúster:

```powershell
Get-Date -Format o
```

Registros utilizados durante la práctica:

- Cambio `285e565...`: commit `2026-07-23T18:57:46-05:00`; ejecución verificada en el clúster `2026-07-25T21:34:57.195746-05:00`.
- Cambio `a07b964...`: commit `2026-07-26T00:44:14-05:00`; ejecución verificada en el clúster `2026-07-26T01:09:59.642816-05:00`.

Los cálculos finales de Lead Time for Changes, Deployment Frequency y Change Failure Rate se consolidan en el documento de reflexión con las capturas/timestamps de la práctica.

## 11. Problemas reales observados

Durante la implementación se documentaron, entre otros:

- fallo de Trivy por vulnerabilidades críticas de la imagen inicial; se redujo la superficie usando runtime distroless;
- permisos de escritura del volumen con runtime non-root; se corrigió mediante contexto de seguridad/grupo del pod;
- `kubectl rollout status` alcanzó el progress deadline durante una iteración y se diagnosticó con `kubectl describe pods`;
- un build de Actions falló por timeout al acceder a Docker Hub y el rerun posterior terminó correctamente;
- el JSON de `kubectl patch` fue interpretado incorrectamente por PowerShell; para el corte Blue-Green se usó `kubectl set selector`, que evita el problema de quoting.

Los errores forman parte de la evidencia del proceso de diagnóstico y corrección.

## Endpoints

| Método y ruta | Función |
|---|---|
| `GET /health` | Salud/readiness de la aplicación. |
| `GET /version` | Versión, color, hostname y datos de configuración no sensibles. |
| `GET /api/products` | Lista productos. |
| `GET /api/products/:id` | Obtiene un producto. |
| `POST /api/products` | Crea un producto. |
| `PATCH /api/products/:id` | Actualiza un producto. |
| `DELETE /api/products/:id` | Elimina un producto. |
| `GET /` | Interfaz web. |

## Variables de entorno

| Variable | Por defecto | Uso |
|---|---|---|
| `PORT` | `3000` | Puerto HTTP. |
| `APP_VERSION` | `v1` | Versión mostrada por la app. |
| `APP_COLOR` | `blue` | Color/identificador visual de la versión. |
| `SIMULATE_FAILURE` | `false` | Simulación de fallo. |
| `DB_PATH` | `./data/products.json` | Ruta del archivo JSON. |
| `STARTUP_DELAY_SECONDS` | `0` | Tiempo durante el cual `/health` devuelve 503 al iniciar. |
| `API_KEY` | vacío | Credencial ficticia consumida desde Kubernetes Secret. |
