# AgentDesk AI frontend (Next.js 15)
FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE 3000

# Dev server is fine for a portfolio demo; build args/env come from docker-compose.
CMD ["npm", "run", "dev"]
