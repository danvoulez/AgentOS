# Dockerfile for Vox Service
FROM node:16-alpine

# Create app directory
WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install production dependencies
RUN npm install --production

# Copy application code
COPY . .

# Create uploads directory with proper permissions
RUN mkdir -p uploads && chmod 777 uploads

# Expose the port the app runs on
EXPOSE 3030

# Command to run the application
CMD ["node", "server.js"]
