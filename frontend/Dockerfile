# 1. 빌드 단계
FROM node:18 AS build

# 작업 디렉토리
WORKDIR /app

# 1️ frontend의 package.json / package-lock.json만 복사
COPY frontend/package*.json ./

# 2️ 의존성 설치
RUN npm install

# 3️ frontend 소스 전체 복사
COPY frontend/ ./

# 4️ CRA 빌드 (build 폴더 생성)
RUN npm run build

# 2. 배포 단계 (nginx)
FROM nginx:alpine

# 5️ 빌드 결과물을 nginx 기본 html 경로로 복사
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
