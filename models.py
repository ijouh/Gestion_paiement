from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    telephone = db.Column(db.String(20))
    adresse = db.Column(db.String(200))
    type_client = db.Column(db.String(20))  # 'complet' ou 'mensuel'
    montant_total = db.Column(db.Float, nullable=False)

    paiements = db.relationship('Paiement', backref='client', lazy=True)

class Paiement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    date_paiement = db.Column(db.Date, nullable=False)
    montant_paye = db.Column(db.Float, nullable=False)
    reste = db.Column(db.Float)
    statut = db.Column(db.String(20))  # 'payé' ou 'en cours'
