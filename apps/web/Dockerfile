FROM node:22-alpine

WORKDIR /app

COPY package.json ./package.json
COPY tsconfig.base.json ./tsconfig.base.json
COPY packages ./packages
COPY apps/web ./apps/web

RUN npm install

EXPOSE 3000

CMD ["npm", "run", "dev", "--workspace", "@agent/web", "--", "--hostname", "0.0.0.0", "--port", "3000"]
