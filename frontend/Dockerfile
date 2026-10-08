# Frontend & Maps Eng. — production image for the TripAgent SPA.
# Multi-stage: build with Node, serve the static bundle with nginx.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund
COPY . .

# Only the URL-restricted public token is baked into the bundle (SRS 11).
ARG VITE_DEMO_MODE=true
ARG VITE_MAPBOX_PUBLIC_TOKEN=""
ENV VITE_DEMO_MODE=$VITE_DEMO_MODE
ENV VITE_MAPBOX_PUBLIC_TOKEN=$VITE_MAPBOX_PUBLIC_TOKEN
RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost/healthz || exit 1
CMD ["nginx", "-g", "daemon off;"]
