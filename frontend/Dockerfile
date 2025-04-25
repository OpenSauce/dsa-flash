FROM node:18-alpine AS builder
WORKDIR /usr/src/app

COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile

COPY . .
RUN yarn build

# Production stage
FROM node:18-alpine
WORKDIR /usr/src/app

COPY --from=builder /usr/src/app ./

EXPOSE 3000
CMD ["yarn", "start"]
