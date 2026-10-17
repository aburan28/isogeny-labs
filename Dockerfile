FROM node:24-bookworm-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends python3 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG CONTACT_API_URL=/api/inquiries
ENV CONTACT_API_URL=$CONTACT_API_URL
RUN npm run build

FROM node:24-bookworm-slim
ENV NODE_ENV=production
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY --from=build /app/_site ./_site
COPY server ./server
USER node
EXPOSE 3000
CMD ["node", "server/index.mjs"]
