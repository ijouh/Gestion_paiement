from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import date
from sqlalchemy import extract, func
import io
from openpyxl import Workbook

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
    modalite_paiement = db.Column(db.String(20), nullable=False)
    montant_total = db.Column(db.Float, nullable=False)
    paiements = db.relationship('Paiement', backref='client', lazy=True, cascade="all, delete-orphan")

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
    mois = request.args.get('mois', type=int)
    annee = request.args.get('annee', type=int)
    page = request.args.get('page', 1, type=int)
    par_page = 5

    clients = Client.query.all()

    # --- Paiements filtrés ---
    paiements_query = Paiement.query.join(Client)
    if mois:
        paiements_query = paiements_query.filter(extract('month', Paiement.date_paiement) == mois)
    if annee:
        paiements_query = paiements_query.filter(extract('year', Paiement.date_paiement) == annee)
    paiements_query = paiements_query.order_by(Paiement.date_paiement.desc())

    total_paiements = paiements_query.count()
    paiements = paiements_query.offset((page - 1) * par_page).limit(par_page).all()
    total_pages = (total_paiements + par_page - 1) // par_page

    # --- Tableau résumé total par mois (avec filtrage) ---
    paiements_par_mois_query = db.session.query(
        extract('year', Paiement.date_paiement).label('annee'),
        extract('month', Paiement.date_paiement).label('mois'),
        func.sum(Paiement.montant_paye).label('total_mensuel')
    )
    if annee:
        paiements_par_mois_query = paiements_par_mois_query.filter(extract('year', Paiement.date_paiement) == annee)
    if mois:
        paiements_par_mois_query = paiements_par_mois_query.filter(extract('month', Paiement.date_paiement) == mois)

    paiements_par_mois = paiements_par_mois_query.group_by('annee', 'mois').order_by('annee', 'mois').all()

    # --- Mois dispo pour filtres ---
    mois_dispo = db.session.query(
        extract('year', Paiement.date_paiement).label('annee'),
        extract('month', Paiement.date_paiement).label('mois')
    ).distinct().order_by('annee', 'mois').all()

    return render_template(
        'dashboard.html',
        clients=clients,
        paiements=paiements,
        paiements_par_mois=paiements_par_mois,
        mois_dispo=mois_dispo,
        mois=mois,
        annee=annee,
        page=page,
        total_pages=total_pages
    )



@app.route('/ajouter-client', methods=['GET', 'POST'])
def ajouter_client():
    if request.method == 'POST':
        nom = request.form['nom']
        email = request.form['email']
        telephone = request.form.get('telephone')
        adresse = request.form.get('adresse')
        modalite_paiement = request.form['modalite_paiement']
        montant_total = float(request.form['montant_total'])

        if Client.query.filter_by(email=email).first():
            flash("Erreur : un client avec cet email existe déjà.", "danger")
            return redirect(url_for('ajouter_client'))

        client = Client(
            nom=nom,
            email=email,
            telephone=telephone,
            adresse=adresse,
            modalite_paiement=modalite_paiement,
            montant_total=montant_total
        )
        db.session.add(client)
        db.session.commit()
        flash("Client ajouté avec succès.", "success")
        return redirect(url_for('dashboard'))

    return render_template('add_client.html')

@app.route('/modifier-client/<int:id>', methods=['GET', 'POST'])
def modifier_client(id):
    client = Client.query.get_or_404(id)

    if request.method == 'POST':
        email = request.form['email']
        if Client.query.filter(Client.email == email, Client.id != id).first():
            flash("Erreur : un autre client utilise cet email.", "danger")
            return redirect(url_for('modifier_client', id=id))

        client.nom = request.form['nom']
        client.email = email
        client.telephone = request.form.get('telephone')
        client.adresse = request.form.get('adresse')
        client.modalite_paiement = request.form['modalite_paiement']
        client.montant_total = float(request.form['montant_total'])
        db.session.commit()
        flash("Client modifié avec succès.", "success")
        return redirect(url_for('dashboard'))

    return render_template('edit_client.html', client=client)

@app.route('/supprimer-client/<int:id>', methods=['POST'])
def supprimer_client(id):
    client = Client.query.get_or_404(id)
    db.session.delete(client)
    db.session.commit()
    flash("Client supprimé.", "success")
    return redirect(url_for('dashboard'))

@app.route('/ajouter-paiement', methods=['GET', 'POST'])
def ajouter_paiement():
    clients = Client.query.all()
    if request.method == 'POST':
        client_id = int(request.form['client_id'])
        date_paiement = request.form['date_paiement']
        montant_paye = float(request.form['montant_paye'])

        client = Client.query.get(client_id)
        total_paye = sum(p.montant_paye for p in client.paiements)
        reste = client.montant_total - total_paye

        if montant_paye > reste:
            flash(f"Erreur : le montant payé ({montant_paye}€) dépasse le reste à payer ({reste}€).", "danger")
            return redirect(url_for('ajouter_paiement'))

        if client.modalite_paiement == 'complet':
            if montant_paye != reste:
                flash(f"Erreur : paiement complet requis, montant doit être égal à {reste}€.", "danger")
                return redirect(url_for('ajouter_paiement'))

        elif client.modalite_paiement == 'deux_fois':
            nb_paiements = len(client.paiements)
            montant_50 = client.montant_total / 2

            if nb_paiements >= 2:
                flash("Erreur : deux paiements maximum autorisés pour ce client.", "danger")
                return redirect(url_for('ajouter_paiement'))

            if nb_paiements == 0 and montant_paye != montant_50:
                flash(f"Erreur : premier paiement doit être de 50% soit {montant_50}€.", "danger")
                return redirect(url_for('ajouter_paiement'))

            if nb_paiements == 1 and montant_paye != reste:
                flash(f"Erreur : second paiement doit être de {reste}€.", "danger")
                return redirect(url_for('ajouter_paiement'))

        elif client.modalite_paiement == 'flexible':
            nb_paiements = len(client.paiements)
            min_avance = client.montant_total * 0.10

            if nb_paiements == 0 and montant_paye < min_avance:
                flash(f"Erreur : le premier paiement doit être au moins 10% du total, soit {min_avance}€.", "danger")
                return redirect(url_for('ajouter_paiement'))

        if date.fromisoformat(date_paiement) < date.today():
            flash("Erreur : Impossible d’ajouter un paiement dans le passé.", "danger")
            return redirect(url_for('ajouter_paiement'))

        nouveau_reste = reste - montant_paye
        statut = 'payé' if nouveau_reste <= 0 else 'en cours'

        paiement = Paiement(
            client_id=client_id,
            date_paiement=date.fromisoformat(date_paiement),
            montant_paye=montant_paye,
            reste=max(nouveau_reste, 0),
            statut=statut
        )
        db.session.add(paiement)
        db.session.commit()
        flash("Paiement ajouté avec succès.", "success")
        return redirect(url_for('dashboard'))

    today = date.today().isoformat()
    return render_template('add_payment.html', clients=clients, today=today)

@app.route('/modifier-paiement/<int:id>', methods=['GET', 'POST'])
def modifier_paiement(id):
    paiement = Paiement.query.get_or_404(id)
    clients = Client.query.all()

    if request.method == 'POST':
        client_id = int(request.form['client_id'])
        date_paiement = request.form['date_paiement']
        montant_paye = float(request.form['montant_paye'])

        client = Client.query.get(client_id)
        total_paye_sans_courant = sum(p.montant_paye for p in client.paiements if p.id != id)
        reste = client.montant_total - total_paye_sans_courant

        if montant_paye > reste:
            flash(f"Erreur : le montant payé ({montant_paye}€) dépasse le reste à payer ({reste}€).", "danger")
            return redirect(url_for('modifier_paiement', id=id))

        if client.modalite_paiement == 'complet':
            if montant_paye != reste:
                flash(f"Erreur : paiement complet requis, montant doit être égal à {reste}€.", "danger")
                return redirect(url_for('modifier_paiement', id=id))

        elif client.modalite_paiement == 'deux_fois':
            nb_paiements = len(client.paiements)
            montant_50 = client.montant_total / 2

            if nb_paiements > 2:
                flash("Erreur : deux paiements maximum autorisés pour ce client.", "danger")
                return redirect(url_for('modifier_paiement', id=id))

            paiements_tries = sorted(client.paiements, key=lambda x: x.date_paiement)
            premier_paiement = paiements_tries[0] if paiements_tries else None
            deuxieme_paiement = paiements_tries[1] if len(paiements_tries) > 1 else None

            if paiement.id == premier_paiement.id and montant_paye != montant_50:
                flash(f"Erreur : premier paiement doit être de 50% soit {montant_50}€.", "danger")
                return redirect(url_for('modifier_paiement', id=id))

            if paiement.id == deuxieme_paiement.id and montant_paye != reste:
                flash(f"Erreur : second paiement doit être de {reste}€.", "danger")
                return redirect(url_for('modifier_paiement', id=id))

        elif client.modalite_paiement == 'flexible':
            paiements_tries = sorted(client.paiements, key=lambda x: x.date_paiement)
            min_avance = client.montant_total * 0.10
            # On vérifie si c'est le premier paiement (par date) qu'on modifie
            if paiement.id == paiements_tries[0].id and montant_paye < min_avance:
                flash(f"Erreur : le premier paiement doit être au moins 10% du total, soit {min_avance}€.", "danger")
                return redirect(url_for('modifier_paiement', id=id))

        if date.fromisoformat(date_paiement) < date.today():
            flash("Erreur : Impossible d’ajouter un paiement dans le passé.", "danger")
            return redirect(url_for('modifier_paiement', id=id))

        # Mise à jour
        paiement.client_id = client_id
        paiement.date_paiement = date.fromisoformat(date_paiement)
        paiement.montant_paye = montant_paye

        nouveau_reste = reste - montant_paye
        paiement.reste = max(nouveau_reste, 0)
        paiement.statut = 'payé' if nouveau_reste <= 0 else 'en cours'

        db.session.commit()
        flash("Paiement modifié avec succès.", "success")
        return redirect(url_for('dashboard'))

    return render_template('edit_payment.html', paiement=paiement, clients=clients)

@app.route('/supprimer-paiement/<int:id>', methods=['POST'])
def supprimer_paiement(id):
    paiement = Paiement.query.get_or_404(id)
    db.session.delete(paiement)
    db.session.commit()
    flash("Paiement supprimé.", "success")
    return redirect(url_for('dashboard'))

@app.route('/api/paiements')
def api_paiements():
    paiements = Paiement.query.all()
    events = []
    for p in paiements:
        events.append({
            'title': f"{p.client.nom} payé: {p.montant_paye}€, reste: {p.reste}€",
            'start': p.date_paiement.strftime('%Y-%m-%d'),
            'color': 'green' if p.statut == 'payé' else 'orange',
        })
    return jsonify(events)

@app.route('/calendar')
def calendar_view():
    return render_template('calendar.html')

@app.route('/export-clients-excel')
def export_clients_excel():
    wb = Workbook()

    # Onglet Clients
    ws_clients = wb.active
    ws_clients.title = "Clients"

    headers_clients = [
        'ID', 'Nom', 'Email', 'Téléphone', 'Adresse',
        'Modalité paiement', 'Montant total (€)', 'Montant payé (€)', 'Reste (€)'
    ]
    ws_clients.append(headers_clients)

    clients = Client.query.all()
    for c in clients:
        total_paye = sum(p.montant_paye for p in c.paiements)
        reste = c.montant_total - total_paye

        ws_clients.append([
            c.id,
            c.nom,
            c.email or '',
            c.telephone or '',
            c.adresse or '',
            c.modalite_paiement,
            round(c.montant_total, 2),
            round(total_paye, 2),
            round(reste, 2),
        ])

    # Onglet Paiements
    ws_payments = wb.create_sheet(title="Paiements")

    headers_payments = ['ID paiement', 'ID client', 'Nom client', 'Date paiement', 'Montant payé (€)', 'Reste (€)', 'Statut']
    ws_payments.append(headers_payments)

    paiements = Paiement.query.order_by(Paiement.client_id, Paiement.date_paiement).all()
    for p in paiements:
        ws_payments.append([
            p.id,
            p.client_id,
            p.client.nom,
            p.date_paiement.strftime('%Y-%m-%d'),
            round(p.montant_paye, 2),
            round(p.reste, 2),
            p.statut,
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="rapport_paiements_clients.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


if __name__ == '__main__':
    app.run(debug=True)
