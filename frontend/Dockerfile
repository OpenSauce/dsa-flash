FROM node:22-alpine AS builder
WORKDIR /usr/src/app

COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile

COPY . .
RUN yarn build

FROM node:22-alpine
WORKDIR /usr/src/app

COPY --from=builder /usr/src/app/.output ./.output
COPY --from=builder /usr/src/app/package.json ./package.json

EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
