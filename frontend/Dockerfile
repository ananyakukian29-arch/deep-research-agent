# frontend/Dockerfile
FROM node:22-slim

WORKDIR /app

# Copy package files and install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy the rest of the frontend source code
COPY . .

# Expose Vite's default port
EXPOSE 5173

# Force Vite to expose the host so it can be accessed outside the container
CMD ["npm", "run", "dev", "--", "--host"]