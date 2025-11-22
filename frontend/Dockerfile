# Multi-stage build for Angular application

# Stage 1: Build the Angular application
FROM node:18-alpine AS build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build argument for configuration (default to production for cloud)
ARG BUILD_CONFIG=production

# Build the application
RUN npm run build -- --configuration=${BUILD_CONFIG}

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copy custom nginx configuration template
COPY nginx.conf /etc/nginx/templates/nginx.conf.template

# Copy built application from build stage
COPY --from=build /app/dist/multiprompt-sandbox /usr/share/nginx/html

# Expose port (Cloud Run uses PORT env var)
EXPOSE 8080

# Start nginx with envsubst to substitute PORT
CMD ["/bin/sh", "-c", "envsubst '${PORT}' < /etc/nginx/templates/nginx.conf.template > /etc/nginx/nginx.conf && nginx -g 'daemon off;'"]
