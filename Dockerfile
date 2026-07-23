# ==========================
# Etapa 1: build y pruebas
# ==========================
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Fail-fast: si una prueba falla, la imagen no se construye
RUN npm test


# ==========================
# Etapa 2: imagen de runtime
# ==========================
FROM node:20-alpine AS runtime

WORKDIR /app

ARG APP_VERSION=v1
ARG APP_COLOR=blue
ARG SIMULATE_FAILURE=false

ENV NODE_ENV=production
ENV PORT=3000
ENV APP_VERSION=${APP_VERSION}
ENV APP_COLOR=${APP_COLOR}
ENV SIMULATE_FAILURE=${SIMULATE_FAILURE}

COPY --from=build /app/package*.json ./
RUN npm ci --omit=dev && npm cache clean --force

# Solo se copia lo necesario para ejecutar la aplicación
COPY --from=build /app/server.js ./server.js
COPY --from=build /app/db.js ./db.js
COPY --from=build /app/public ./public

# La base JSON se creará aquí al iniciar
RUN mkdir -p /app/data && chown -R node:node /app

USER node

EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/health', r => process.exit(r.statusCode === 200 ? 0 : 1)).on('error', () => process.exit(1))"

CMD ["node", "server.js"]
