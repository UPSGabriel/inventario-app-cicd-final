# Evidencias de verificacion

Fecha de revalidacion: 26 de julio de 2026.

Este archivo separa evidencia ejecutada de afirmaciones pendientes. No sustituye las
capturas requeridas por el docente.

## 1. Pruebas locales

Comando:

```powershell
npm ci
npm test
```

Resultado:

```text
tests 5
pass 5
fail 0
duration_ms 3688.3988
```

## 2. Docker multi-stage y endpoints

Comando de build:

```powershell
docker build -t inventario-app:codex-verification .
```

Resultado relevante:

```text
[build 6/7] RUN npm test
tests 5
pass 5
fail 0
exporting manifest sha256:8ab232f9dee8510193b914e7e5fbd781d55b08ff5b87a2ddeb7d9b1c6e1af5a5
```

La imagen se ejecuto temporalmente como `nonroot:nonroot`. El smoke test valido:

```text
[OK] Health status=ok
[OK] Version=vtest Color=green
[OK] Products respondio correctamente (3 producto(s))
[OK] GET /, /health, /version y /api/products respondieron correctamente.
```

El contenedor temporal `inventario-codex-verify` se elimino al terminar.

## 3. GitHub Actions y GHCR

La API publica de GitHub confirmo:

| Run | Commit | Resultado |
|---:|---|---|
| [29980646258](https://github.com/UPSGabriel/inventario-app-cicd-final/actions/runs/29980646258) | `f42eb46` | failure |
| [30054762604](https://github.com/UPSGabriel/inventario-app-cicd-final/actions/runs/30054762604) | `285e565` | success |
| [30215997268](https://github.com/UPSGabriel/inventario-app-cicd-final/actions/runs/30215997268) | `77faaf7` | success |

Los 12 runs mas recientes consultados estaban en `success`. El repositorio fue
confirmado como publico:

<https://github.com/UPSGabriel/inventario-app-cicd-final>

`docker manifest inspect` confirmo que existen en GHCR:

```text
ghcr.io/upsgabriel/inventario-app-cicd-final:latest
ghcr.io/upsgabriel/inventario-app-cicd-final:285e565d1dee3f98c0b4e4df7a32101a86895390
ghcr.io/upsgabriel/inventario-app-cicd-final:a07b96493f7dbe1042062875efafc9cf9371c3f1
```

Paquete: <https://github.com/UPSGabriel/inventario-app-cicd-final/pkgs/container/inventario-app-cicd-final>

## 4. Scripts de Jordy

Se verifico sintaxis de PowerShell para ambos archivos.

`smoke-test.ps1` se ejecuto contra el contenedor Docker real y valido los tres
endpoints JSON. `switch-blue-green.ps1` se ejecuto con una interfaz `kubectl`
simulada y comprobo el flujo completo: contexto fijado, espera del Deployment,
cambio de selector, convergencia asincrona de `EndpointSlice` y etiquetas `slot=green`.
Tambien se simulo un fallo de convergencia y se confirmo el rollback automatico a BLUE.

## 5. Kubernetes: estado de la revalidacion

El perfil `minikube` local estaba detenido. Al intentar iniciarlo, el contenedor
arranco pero su API server no respondio en `https://127.0.0.1:58760`; los addons
fallaron al obtener OpenAPI y el proceso alcanzo el timeout. El contenedor se detuvo
sin eliminar el perfil ni sus datos. No se desplego sobre el contexto activo
`kind-ticket-cluster`, porque pertenece a otro proyecto.

Por tanto, la evidencia Kubernetes actual que puede usarse es la ya registrada por
Gabriel en el README y sus capturas originales. Antes de entregar se necesita una de
estas dos opciones:

1. adjuntar las capturas originales de `kubectl rollout status`, pods y corte
   Blue-Green; o
2. reparar/recrear Minikube con autorizacion del propietario y repetir los comandos
   del README para obtener capturas nuevas.

No se debe afirmar que la revalidacion actual de Minikube fue exitosa.

## 6. Versionado y pendientes externos antes de enviar

La identidad Git configurada corresponde a Jordy y esta contribucion se versiona en su
rama propia. Antes de la entrega todavia se debe:

- Subir la rama o integrar los commits en `main`.
- Confirmar que el nuevo run de Actions queda en verde y publica la nueva etiqueta.
- Adjuntar capturas de Kubernetes/Blue-Green o recuperar las capturas originales.
- Subir el PDF `output/pdf/informe-reflexion-cicd.pdf` junto con el enlace publico.
