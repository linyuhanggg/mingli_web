# syntax=docker/dockerfile:1.7
FROM node:24-alpine AS dependencies
WORKDIR /srv/web
COPY web/package.json web/package-lock.json ./
RUN npm ci

FROM dependencies AS build
ARG BACKEND_INTERNAL_URL=http://api:8000
ENV BACKEND_INTERNAL_URL=$BACKEND_INTERNAL_URL \
    NEXT_TELEMETRY_DISABLED=1
COPY web/ ./
RUN npm run build

FROM node:24-alpine AS runtime
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
WORKDIR /srv/web
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=build --chown=nextjs:nodejs /srv/web/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /srv/web/.next/static ./.next/static
COPY --from=build --chown=nextjs:nodejs /srv/web/public ./public
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
