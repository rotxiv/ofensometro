# Compila la aplicación con Node y la sirve con nginx. La imagen final no lleva Node.
#
#   docker build -t ofensometro-web .
#   docker run -p 8080:80 -e API_UPSTREAM=http://host.docker.internal:8000 ofensometro-web
#
# API_UPSTREAM es la dirección de la API, sin barra final. Se lee al ARRANCAR el contenedor, no al
# construir la imagen: la misma imagen sirve para cualquier entorno.

FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
# La imagen oficial procesa /etc/nginx/templates/*.template al arrancar y escribe el resultado en conf.d
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
ENV API_UPSTREAM=http://host.docker.internal:8000
EXPOSE 80
