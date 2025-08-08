# Utiliser une image Python officielle avec une version récente
FROM python:3.11-slim

# Installer les dépendances système nécessaires pour pandas, psycopg2, et compilation
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /app

# Copier le fichier requirements dans le conteneur
COPY requirements.txt .

# Mettre à jour pip et installer les dépendances Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copier le reste des fichiers de l'application
COPY . .

# Exposer le port utilisé par Flask (adapter si besoin)
EXPOSE 5000

# Commande pour lancer l’application Flask avec Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
