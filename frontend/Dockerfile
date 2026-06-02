# AgentDesk AI frontend (Next.js 15) — implemented in Phase 7
FROM node:20-slim

WORKDIR /app

COPY package.json ./
RUN if [ -f package.json ]; then npm install; fi

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
