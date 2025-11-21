FROM ctfd/ctfd:3.8.1

# Switch to root for installations
USER root

# Install additional dependencies
RUN pip install --no-cache-dir \
    requests>=2.31.0 \
    APScheduler>=3.10.0 \
    PyJWT>=2.8.0

# Copy custom plugins
COPY plugins/ /opt/CTFd/CTFd/plugins/

# Set working directory
WORKDIR /opt/CTFd

# Expose port
EXPOSE 8000

# Use default CTFd entrypoint (plugins handle initialization)
# No custom entrypoint needed - initial_setup plugin handles auto-config
