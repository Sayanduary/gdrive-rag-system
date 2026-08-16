# Build Stage
FROM node:20-alpine AS build

WORKDIR /app

# Copy package management files and install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy application source code and build for production
COPY . .
RUN npm run build

# Production Stage
FROM nginx:alpine

# Copy built web application from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy Nginx SPA configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
