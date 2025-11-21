FROM python:3.11-slim

WORKDIR /app

# Installer Flask
RUN pip install --no-cache-dir flask

# Copier l'application
COPY app.py .

# Exposer le port
EXPOSE 5000

# Lancer l'application
CMD ["python", "app.py"]
