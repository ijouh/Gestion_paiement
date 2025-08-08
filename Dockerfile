# Utilise une image Python officielle avec une version récente
FROM python:3.11-slim

# Installer les dépendances système nécessaires pour pandas et psycopg2
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Créer et définir le répertoire de travail
WORKDIR /app

# Copier les fichiers requirements et installer les dépendances Python
COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copier tout le contenu du projet dans le conteneur
COPY . .

# Expose le port utilisé par Flask (modifie si besoin)
EXPOSE 5000

# Commande pour lancer l’application Flask (à adapter si nécessaire)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
