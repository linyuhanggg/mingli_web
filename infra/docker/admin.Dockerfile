# syntax=docker/dockerfile:1.7
FROM node:24-alpine AS dependencies
WORKDIR /srv/admin
COPY admin/package.json admin/package-lock.json ./
RUN npm ci

FROM dependencies AS build
ARG BACKEND_INTERNAL_URL=http://api:8000
ENV BACKEND_INTERNAL_URL=$BACKEND_INTERNAL_URL \
    NEXT_TELEMETRY_DISABLED=1
COPY ui /srv/ui
COPY admin/ ./
RUN npm run build

FROM node:24-alpine AS runtime
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3001 \
    HOSTNAME=0.0.0.0
WORKDIR /srv/admin
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=build --chown=nextjs:nodejs /srv/admin/.next/standalone/admin ./
COPY --from=build --chown=nextjs:nodejs /srv/admin/.next/static ./.next/static
USER nextjs
EXPOSE 3001
CMD ["node", "server.js"]
