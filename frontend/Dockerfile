# Mipham Quant Frontend — nginx serving prebuilt dist
# Build context: repository root (see docker-compose.yml)
#
# Frontend source is built locally (pnpm build in apps/frontend/)
# and output to frontend/dist/. This Dockerfile only serves.
FROM nginx:1.25-alpine
RUN apk add --no-cache curl
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/dist/ /usr/share/nginx/html/

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost/health || exit 1
CMD ["nginx", "-g", "daemon off;"]
