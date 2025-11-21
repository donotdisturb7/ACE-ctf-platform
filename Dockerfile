FROM ctfd/ctfd:3.7.0

# Install additional dependencies for plugins
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

# Use the default CTFd entrypoint
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "gevent", "--access-logfile", "/var/log/CTFd/access.log", "--error-logfile", "/var/log/CTFd/error.log", "CTFd:create_app()"]
