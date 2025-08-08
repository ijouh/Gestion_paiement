from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SubmitField, SelectField, DateField
from wtforms.validators import DataRequired

class ClientForm(FlaskForm):
    nom = StringField('Nom du client', validators=[DataRequired()])
    modalite_paiement = SelectField('Modalité de paiement', choices=[
        ('complet', 'Paiement complet'),
        ('moitie', '50% + 50%'),
        ('flexible', 'Paiement flexible')
    ], validators=[DataRequired()])
    submit = SubmitField('Ajouter')

class PaiementForm(FlaskForm):
    montant = FloatField('Montant', validators=[DataRequired()])
    date_paiement = DateField('Date de paiement', validators=[DataRequired()])
    client_id = SelectField('Client', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Ajouter')
