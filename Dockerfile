# ==========================
# Etapa 1: dependencias y pruebas
# ==========================
FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Fail-fast: si una prueba falla, la imagen no se construye
RUN npm test

# Conserva solo dependencias necesarias para produccion
RUN npm prune --omit=dev


# ==========================
# Etapa 2: runtime minimo y sin root
# ==========================
FROM gcr.io/distroless/nodejs22-debian13:nonroot AS runtime

ARG APP_VERSION=v1
ARG APP_COLOR=blue
ARG SIMULATE_FAILURE=false

ENV NODE_ENV=production
ENV PORT=3000
ENV APP_VERSION=${APP_VERSION}
ENV APP_COLOR=${APP_COLOR}
ENV SIMULATE_FAILURE=${SIMULATE_FAILURE}

# Solo se copia lo necesario para ejecutar la aplicacion
COPY --chown=nonroot:nonroot --from=build /app/package*.json /app/
COPY --chown=nonroot:nonroot --from=build /app/node_modules /app/node_modules
COPY --chown=nonroot:nonroot --from=build /app/server.js /app/server.js
COPY --chown=nonroot:nonroot --from=build /app/db.js /app/db.js
COPY --chown=nonroot:nonroot --from=build /app/public /app/public
COPY --chown=nonroot:nonroot --from=build /app/data/.gitkeep /app/data/.gitkeep

WORKDIR /app
USER nonroot:nonroot

EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD ["/nodejs/bin/node", "-e", "require('http').get('http://localhost:3000/health', r => process.exit(r.statusCode === 200 ? 0 : 1)).on('error', () => process.exit(1))"]

# La imagen distroless ya usa Node.js como ENTRYPOINT
CMD ["server.js"]
