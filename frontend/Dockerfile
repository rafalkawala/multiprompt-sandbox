# Multi-stage build for Angular application

# Stage 1: Build the Angular application
FROM node:18-alpine AS build

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml* ./

# Install dependencies with pnpm
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build argument for configuration (default to production for cloud)
ARG BUILD_CONFIG=production

# Build the application
RUN pnpm run build --configuration=${BUILD_CONFIG}

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copy custom nginx configuration template
COPY nginx.conf /etc/nginx/templates/nginx.conf.template

# Copy built application from build stage
COPY --from=build /app/dist/multiprompt-sandbox /usr/share/nginx/html

# Copy static auth callback HTML for iOS Safari compatibility
COPY src/auth-callback.html /usr/share/nginx/html/auth-callback.html

# Expose port (Cloud Run uses PORT env var)
EXPOSE 8080

# Start nginx with envsubst to substitute PORT
CMD ["/bin/sh", "-c", "envsubst '${PORT}' < /etc/nginx/templates/nginx.conf.template > /etc/nginx/nginx.conf && nginx -g 'daemon off;'"]
