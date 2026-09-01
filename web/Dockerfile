FROM node:22-alpine AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
COPY --from=dependencies /app/node_modules ./node_modules
COPY . ./
RUN npm run build

FROM node:22-alpine AS runtime
ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0
WORKDIR /app
RUN addgroup --system --gid 10001 harvestmind \
    && adduser --system --uid 10001 --ingroup harvestmind harvestmind
COPY --from=builder --chown=harvestmind:harvestmind /app/.next/standalone ./
COPY --from=builder --chown=harvestmind:harvestmind /app/.next/static ./.next/static
COPY --from=builder --chown=harvestmind:harvestmind /app/public ./public
USER harvestmind
EXPOSE 3000
CMD ["node", "server.js"]
