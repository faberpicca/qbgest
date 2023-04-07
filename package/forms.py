from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, TextAreaField, PasswordField, BooleanField, SubmitField, DateField, DecimalField, IntegerField, SelectField, RadioField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Optional, InputRequired
#from app.models import User, Partner, Imposta, Ritenuta, Mastro, Sottomastro, Conto, Registro, Registrazione, Validazione, Movimento, Voce, Log, Pagamento
from package.models import *
#from app.share import *

class FlexibleDecimalField(DecimalField):
    def process_formdata(self, valuelist):
        if valuelist:
            if "," in valuelist[0]:valuelist[0] = valuelist[0].replace(".", "")
            valuelist[0] = valuelist[0].replace(",", ".")
        return super(FlexibleDecimalField, self).process_formdata(valuelist)

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class PasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Salva')

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    ruolo = StringField('Ruolo')
    submit = SubmitField('Salva')

    def validate_ruolo(self, ruolo):
        if ruolo.data !=None and ruolo.data not in ["user", "admin"]:
            raise ValidationError("Ruolo ammesso: user, admin")

def partner_check(form, field):
    partner = Partner.query.filter_by(nome=field.data).first()
    if partner is None:
        raise ValidationError('Questo partner non esiste')

def partner_check_allow_empty(form, field):
    if field!=None and field.data!="":
        partner = Partner.query.filter_by(nome=field.data).first()
        if partner is None:
            raise ValidationError('Questo partner non esiste')

def registro_check(form, field):
    registro = Registro.query.filter_by(nome=field.data).first()
    if registro is None:
        raise ValidationError('Questo registro non esiste')

def conto_check(form, field):
    conto = Conto.query.filter_by(nome=field.data).first()
    if conto is None:
        raise ValidationError('Questo conto non esiste')

class ImpostazioniForm(FlaskForm):
    azienda = StringField('Azienda', [partner_check])
    erario = StringField('Erario', [partner_check])
    registro_misc = StringField('Registro operazioni varie', [registro_check])
    registro_fatf = StringField('Registro fatture fornitori', [registro_check])
    registro_notf = StringField('Registro note di credito fornitori', [registro_check])
    registro_fatc = StringField('Registro fatture clienti', [registro_check])
    registro_notc = StringField('Registro note di credito clienti', [registro_check])
    registro_autofattura_rc = StringField('Registro autofatture reverse charge', [registro_check])
    registro_riconciliazione_rc = StringField('Registro riconciliazione reverse charge', [registro_check])
    registro_riconciliazione_sp = StringField('Registro riconciliazione split payment', [registro_check])
    #starting_date = db.Column(db.Date)# da attivare
    #starting_date = DateField('Data ultima apertura conti',format='%d/%m/%Y',validators=[Optional()])
    starting_date = DateField('Data ultima apertura conti',validators=[Optional()])
    imap_server = StringField('Server IMAP')
    imap_user = StringField('Username IMAP')
    imap_pwd = StringField('Password IMAP')
    smtp_server = StringField('Server SMTP')
    smtp_user = StringField('Username SMTP')
    smtp_pwd = StringField('Password SMTP')
    pec_sdi = StringField('Indirizzo pec del sistema di interscambio')
    sequenziale_sdi = IntegerField('Codice sequenziale SDI')
    conto_perdite_profitti = StringField('Conto perdite e profitti', [conto_check])
    conto_utile = StringField('Conto utile', [conto_check])
    conto_chiusura = StringField('Conto chiusura', [conto_check])
    conto_apertura = StringField('Conto apertura', [conto_check])
    conto_lav_autonomo = StringField('Conto lavoratori autonomi', [conto_check])
    ultimo_giorno_esercizio = StringField('Ultimo giorno di esercizio')
    submit = SubmitField('Salva')

class FatturaForm(FlaskForm):
    descrizione = StringField('Descrizione', validators=[InputRequired()])
    numero_origine = StringField('Numero di origine', filters = [lambda x: x or None])#se non viene compilato il campo restituisce None e non ""
    data_contabile = DateField('Data contabile',validators=[Optional()])
    data_decorrenza = DateField('Data emissione',validators=[Optional()])
    data_scadenza = DateField('Data scadenza',validators=[Optional()])
    note = TextAreaField('Note', render_kw={"rows": 1, "cols": 120})
    partner = StringField('Partner', [partner_check])
    lav_autonomo = BooleanField('Lav. autonomo')
    submit = SubmitField('Salva')

class FatturaForm1(FlaskForm):
    pagamento = StringField('Termini di pagamento')
    letturista = BooleanField('Letturista')
    note = TextAreaField('Causale', render_kw={"rows": 10, "cols": 130})
    submit = SubmitField('Salva')

    def validate_pagamento(self, pagamento):
        if pagamento.data!=None:
            pagamento2 = Pagamento.query.filter_by(nome=pagamento.data).first()
            if pagamento.data!="" and pagamento2 is None:
                raise ValidationError('Questo pagamento non esiste')

class CambiaContoForm(FlaskForm):
    conto = StringField('Conto', [conto_check])
    submit = SubmitField('Salva')

class VoceFatturaForm(FlaskForm):
    descrizione = StringField('Descrizione', validators=[InputRequired()])
    quantita = FlexibleDecimalField('Quantità', validators=[InputRequired()], places=None)
    esercizio_precedente = BooleanField('Esercizio precedente')
    importo = FlexibleDecimalField('Importo', validators=[InputRequired()], places=None)
    registrazione = StringField('Registrazione')
    conto = StringField('Conto', [conto_check])
    imposta = StringField('Imposta')
    ritenuta = StringField('Ritenuta')
    submit = SubmitField('Salva')

    def validate_imposta(self, imposta):
        #print(self.imposta)
        imposta = Imposta.query.filter_by(nome=imposta.data).first()
        if imposta is None:
            raise ValidationError('Questa imposta non esiste')

class VoceRicevutaForm(FlaskForm):
    descrizione = StringField('Descrizione', validators=[InputRequired()])
    importo = FlexibleDecimalField('Importo', validators=[InputRequired()], places=None)
    conto = StringField('Conto', [conto_check])
    submit = SubmitField('Salva')

class IVAForm(FlaskForm):
    descrizione = StringField('Descrizione', validators=[InputRequired()])
    data_contabile = DateField('Data contabile',validators=[Optional()])
    data_decorrenza = DateField('Data inizio',validators=[Optional()])
    data_scadenza = DateField('Data fine',validators=[Optional()])
    note = TextAreaField('Note', render_kw={"rows": 1, "cols": 120})
    partner = StringField('Partner', [partner_check])
    submit = SubmitField('Salva')

class VoceIVAForm(FlaskForm):
    descrizione = StringField('Descrizione', validators=[InputRequired()])
    importo = FlexibleDecimalField('Importo', validators=[InputRequired()], places=None)
    conto = StringField('Conto', [conto_check])
    submit = SubmitField('Salva')

class EditIVAForm(FlaskForm):
    iva = FlexibleDecimalField('IVA', validators=[InputRequired()], places=None)
    submit = SubmitField('Salva')

class CassaForm(FlaskForm):
    descrizione = StringField('Descrizione', validators=[InputRequired()])
    data_contabile = DateField('Data contabile',validators=[Optional()])
    partner = StringField('Partner o domiciliatario', [partner_check_allow_empty])
    importo = FlexibleDecimalField('Importo', validators=[InputRequired()], places=None)
    submit = SubmitField('Salva')

class VoceCassaForm(FlaskForm):
    descrizione = StringField('Descrizione', validators=[InputRequired()])
    conto = StringField('Conto', [conto_check])
    partner = StringField('Partner')
    dare = FlexibleDecimalField('Dare', validators=[InputRequired()], places=None)
    avere = FlexibleDecimalField('Avere', validators=[InputRequired()], places=None)
    submit = SubmitField('Salva')

    def validate_descrizione(self, descrizione):
        if len(descrizione.data.replace(" ",""))==0:
            raise ValidationError('Inserire una descrizione')

class GenericoForm(FlaskForm):
    descrizione = StringField('Descrizione', validators=[InputRequired()])
    data_contabile = DateField('Data contabile',validators=[Optional()])
    partner = StringField('Partner', [partner_check_allow_empty])
    submit = SubmitField('Salva')

class VoceGenericoForm(FlaskForm):
    descrizione = StringField('Descrizione', validators=[InputRequired()])
    conto = StringField('Conto', [conto_check])
    partner = StringField('Partner')
    dare = FlexibleDecimalField('Dare', validators=[InputRequired()], places=None)
    avere = FlexibleDecimalField('Avere', validators=[InputRequired()], places=None)
    submit = SubmitField('Salva')

    def validate_descrizione(self, descrizione):
        if len(descrizione.data.replace(" ",""))==0:
            raise ValidationError('Inserire una descrizione')

class MastroForm(FlaskForm):
    nome = StringField('Descrizione', validators=[InputRequired()])
    tipo = StringField('Tipo')
    categoria = StringField('Categoria')
    codice = IntegerField('Codice')
    submit = SubmitField('Salva')

    def validate_tipo(self, tipo):
        if tipo.data not in ["Attività", "Passività", "Costi", "Ricavi", "Altro"]:
            raise ValidationError("Tipologia ammessa: Attività, Passività, Costi, Ricavi, Altro")

class SottomastroForm(FlaskForm):
    nome = StringField('Descrizione', validators=[InputRequired()])
    codice = IntegerField('Codice')
    mastro = StringField('Conto di mastro')
    submit = SubmitField('Salva')

class ContoForm(FlaskForm):
    descrizione = StringField('Descrizione', validators=[InputRequired()])
    codice = IntegerField('Codice')
    submit = SubmitField('Salva')
    sottomastro = StringField('Sottoconto di mastro')

    def validate_sottomastro(self, sottomastro):
        sottomastro = Sottomastro.query.filter_by(nome=sottomastro.data).first()
        if sottomastro is None:
            raise ValidationError('Questo sottomastro non esiste')

class ImpostaForm(FlaskForm):
    nome = StringField('Nome')
    posizione = IntegerField('Posizione')
    aliquota = FlexibleDecimalField('Aliquota', validators=[InputRequired()], places=None)
    natura = StringField('Natura', filters = [lambda x: x or None])
    esigibilita = StringField('Esigibilità', filters = [lambda x: x or None])
    indetraibile = BooleanField('Indetraibile')
    riferimento_normativo = StringField('Riferimento normativo', filters = [lambda x: x or None])
    rc = BooleanField('Reverse charge')
    no_lipe = BooleanField('Escludi da LIPE')
    submit = SubmitField('Salva')

    def validate_natura(self, natura):
        #print(natura.data)
        if natura.data !=None and natura.data not in ["N1", "N2", "N3", "N4", "N5", "N6", "N6.8", "N7"]:
            raise ValidationError("Natura ammessa: campo vuoto, N1, N2, N3, N4, N5, N6, N6.8, N7")

    def validate_esigibilita(self, esigibilita):
        if esigibilita.data not in ["I", "D", "S"]:
            raise ValidationError("Esigibilità ammessa: I, D, S")

class RitenutaForm(FlaskForm):
    nome = StringField('Nome')
    aliquota = FlexibleDecimalField('Aliquota', validators=[InputRequired()], places=None)
    registro_ritenuta = StringField('Registro ritenuta acconto')
    conto_transito_ritenuta = StringField('Conto transito ritenuta')
    submit = SubmitField('Salva')

class RegistroForm(FlaskForm):
    segno = IntegerField('Segno')
    tipo_documento = StringField('Tipo di documento')
    codice = StringField('Codice')
    nome = StringField('Nome')
    categoria = StringField('Categoria')
    posizione = IntegerField('Posizione')
    conto = StringField('Conto predefinito')
    conto_precedente = StringField('Conto esercizio precedente')
    conto_iva = StringField('Conto IVA')
    submit = SubmitField('Salva')

    def validate_tipo_documento(self, tipo_documento):
        if self.tipo_documento.data != "":
            x = Tipo_documento.query.filter_by(codice=tipo_documento.data).first()
            if x is None:
                raise ValidationError('Questo tipo di documento non esiste')

    def validate_conto(self, conto):
        conto = Conto.query.filter_by(nome=conto.data).first()
        if self.categoria.data in ["Cassa", "Fattura"] and conto is None:
            raise ValidationError('Questo conto non esiste')

    def validate_conto_iva(self, conto_iva):
        if conto_iva.data != "":
            conto = Conto.query.filter_by(nome=conto_iva.data).first()
            if self.categoria.data in ["Fattura", "IVA"] and conto is None:
                raise ValidationError('Questo conto non esiste')

    def validate_categoria(self, categoria):
        if categoria.data not in ["Fattura", "Cassa", "Generico", "Ricevuta", "IVA"]:
            raise ValidationError("Categorie ammesse: Fattura, Cassa, Generico, Ricevuta, IVA")

class FiltroForm(FlaskForm):
    dal = DateField('Dal',validators=[Optional()])
    al = DateField('Al',validators=[Optional()])
    tipo_data = RadioField('', choices=[('data_contabile', 'Data contabile'), ('data_decorrenza', 'Data emissione'), ('data_scadenza', 'Data scadenza')])
    partner = StringField('Partner o domiciliatario', [partner_check_allow_empty])
    stato = RadioField('', choices=[('tutte', 'Tutte'), ('insolute', 'Insolute')])
    bozze = BooleanField('Mostra bozze')
    submit_filtro = SubmitField('Applica filtri')

class ImportForm(FlaskForm):
    file = FileField('Seleziona file',validators=[FileRequired()])  
    submit2 = SubmitField('Importa estratto conto')

class UploadForm(FlaskForm):
    file = FileField('Allega file',validators=[FileRequired()])  
    submit2 = SubmitField('Upload')#ho dovuto mettere un nome diverso per avere due forms nella stessa pagine

class ConfermaForm(FlaskForm):
    data_delibera = DateField('Data contabile')
    submit = SubmitField('Conferma')

class RegistroStampaForm(FlaskForm):
    nome = StringField('Descrizione')
    categoria = StringField('Categoria')
    posizione = IntegerField('Posizione')
    submit = SubmitField('Salva')

    def validate_categoria(self, categoria):
        if categoria.data not in ["Registro IVA", "Liquidazione IVA", "Partitario", "Libro Giornale", "Libro Mastro", "Bilancio Contabile"]:
            raise ValidationError("categorie ammesse: Registro IVA, Liquidazione IVA, Partitario, Libro Giornale, Libro Mastro, Bilancio Contabile")

class StampaForm(FlaskForm):
    nome = StringField('Descrizione', validators=[InputRequired()])
    data_decorrenza = DateField('Data decorrenza',validators=[Optional()])
    data_scadenza = DateField('Data scadenza',validators=[Optional()])
    anno_stampa = IntegerField('Anno di stampa')
    precedente_pagina_stampa = IntegerField('Pagina precedente')
    precedente_riga_stampa = IntegerField('Riga precedente')
    partner = StringField('Partner', [partner_check_allow_empty])
    registrazione = StringField('Registrazione')
    submit = SubmitField('Stampa')

class StampaLiquidazioneIvaForm(FlaskForm):
    anno_stampa = IntegerField('Anno di stampa')
    precedente_pagina_stampa = IntegerField('Pagina precedente')
    precedente_riga_stampa = IntegerField('Riga precedente')
    registrazione = StringField('Liquidazione')
    VP7 = FlexibleDecimalField('VP7', validators=[InputRequired()], places=None)
    VP8 = FlexibleDecimalField('VP8', validators=[InputRequired()], places=None)
    VP9 = FlexibleDecimalField('VP9', validators=[InputRequired()], places=None)
    VP10 = FlexibleDecimalField('VP10', validators=[InputRequired()], places=None)
    VP11 = FlexibleDecimalField('VP11', validators=[InputRequired()], places=None)
    submit = SubmitField('Stampa')

    def validate_registrazione(self, registrazione):
        registrazione = Registrazione.query.filter_by(nome=registrazione.data).first()
        if registrazione is None:
            raise ValidationError('Questa registrazione non esiste')

class AnagraficaForm(FlaskForm):
    search = StringField('Testo da cercare', validators=[DataRequired()])
    submit = SubmitField('Cerca')

class PartnerForm(FlaskForm):
    nome = StringField('Denominazione')
    indirizzo = StringField('Indirizzo', validators=[DataRequired()])
    citta = StringField('Comune', validators=[DataRequired()])
    #comune = StringField('Comune')
    provincia = StringField('Provincia', validators=[DataRequired()])
    cap = StringField('CAP', validators=[DataRequired()])
    cf = StringField('Codice fiscale', filters = [lambda x: x or None])
    iva = StringField('P.IVA', filters = [lambda x: x or None])
    telefono = StringField('Telefono', filters = [lambda x: x or None])
    cellulare = StringField('Cellulare', filters = [lambda x: x or None])
    fax = StringField('Fax', filters = [lambda x: x or None])
    email = StringField('Email', filters = [lambda x: x or None])
    pec = StringField('Pec', filters = [lambda x: x or None])
    codice_destinatario = StringField('Codice destinatario', filters = [lambda x: x or None])
    amministratore = StringField('Amministratore', [partner_check_allow_empty])
    letturista = StringField('Letturista', [partner_check_allow_empty])
    regime_fiscale = StringField('Regime fiscale', filters = [lambda x: x or None])
    rea_ufficio = StringField('Ufficio REA', filters = [lambda x: x or None])
    rea_codice = StringField('Numero REA', filters = [lambda x: x or None])
    rea_stato_liquidatione = StringField('Stato liquidazione', filters = [lambda x: x or None])
    iban = StringField('IBAN', filters = [lambda x: x or None])
    pa = BooleanField('Pubblica amministrazione')
    lav_autonomo = BooleanField('Lavoratore autonomo')
    submit = SubmitField('Salva')

    def validate_iva(self, iva):
        if iva.data!=None and iva.data[:2]!="IT":
            raise ValidationError('Codice IVA non valido')

class FiltroContoForm(FlaskForm):
    conto = StringField('Conto', [conto_check])
    submit = SubmitField('Conferma')

class FiltroRegistroForm(FlaskForm):
    registro = StringField('Registro', [registro_check])
    submit = SubmitField('Conferma')
