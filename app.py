from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import date

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'secret'

db = SQLAlchemy(app)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    telephone = db.Column(db.String(20))
    adresse = db.Column(db.String(200))
    type_client = db.Column(db.String(20), nullable=False)
    montant_total = db.Column(db.Float, nullable=False)
    paiements = db.relationship('Paiement', backref='client', lazy=True)

class Paiement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    date_paiement = db.Column(db.Date, nullable=False)
    montant_paye = db.Column(db.Float, nullable=False)
    reste = db.Column(db.Float, nullable=False)
    statut = db.Column(db.String(20), nullable=False)

with app.app_context():
    db.create_all()

@app.route('/')
def dashboard():
    clients = Client.query.all()
    return render_template('dashboard.html', clients=clients)

@app.route('/ajouter-client', methods=['GET', 'POST'])
def ajouter_client():
    if request.method == 'POST':
        nom = request.form['nom']
        email = request.form['email']
        telephone = request.form['telephone']
        adresse = request.form['adresse']
        type_client = request.form['type_client']
        montant_total = float(request.form['montant_total'])

        # Vérifie si l'email est déjà utilisé
        if Client.query.filter_by(email=email).first():
            return "Erreur : un client avec cet email existe déjà.", 400

        client = Client(
            nom=nom,
            email=email,
            telephone=telephone,
            adresse=adresse,
            type_client=type_client,
            montant_total=montant_total
        )
        db.session.add(client)
        db.session.commit()
        return redirect(url_for('dashboard'))

    return render_template('add_client.html')

@app.route('/ajouter-paiement', methods=['GET', 'POST'])
def ajouter_paiement():
    clients = Client.query.all()
    if request.method == 'POST':
        client_id = int(request.form['client_id'])
        date_paiement = request.form['date_paiement']
        montant_paye = float(request.form['montant_paye'])

        # Validation côté serveur : ne pas autoriser une date passée
        if date.fromisoformat(date_paiement) < date.today():
            return "Erreur : Impossible d’ajouter un paiement dans le passé.", 400

        client = Client.query.get(client_id)
        total_paye = sum(p.montant_paye for p in client.paiements)
        reste = client.montant_total - (total_paye + montant_paye)
        statut = 'payé' if reste <= 0 else 'en cours'

        paiement = Paiement(
            client_id=client_id,
            date_paiement=date.fromisoformat(date_paiement),
            montant_paye=montant_paye,
            reste=max(reste, 0),
            statut=statut
        )
        db.session.add(paiement)
        db.session.commit()
        return redirect(url_for('dashboard'))

    today = date.today().isoformat()
    return render_template('add_payment.html', clients=clients, today=today)

@app.route('/api/paiements')
def api_paiements():
    paiements = Paiement.query.all()
    events = []
    for p in paiements:
        events.append({
            'title': f"{p.client.nom} payé: {p.montant_paye}€, reste: {p.reste}€",
            'start': p.date_paiement.strftime('%Y-%m-%d'),
            'color': 'green' if p.statut == 'payé' else 'orange' if p.statut == 'en cours' else 'red',
        })
    return jsonify(events)

@app.route('/calendar')
def calendar_view():
    return render_template('calendar.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
