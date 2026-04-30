# 阶段 1：构建
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# 阶段 2：输出静态文件
FROM alpine:3.21
COPY --from=build /app/dist /dist
# 由 docker-compose 挂载到 nginx
CMD ["cp", "-r", "/dist/.", "/usr/share/nginx/html/"]
