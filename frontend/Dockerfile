# Etapa 1: build do React com o Vite (Vite 7 pede Node 20.19+ ou 22.12+)
FROM node:22-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .
# Endereço do backend visto pelo navegador (sem /api). Fica gravado no JS no momento do build.
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# Etapa 2: só os arquivos estáticos, servidos pelo nginx
FROM nginx:1.28-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
