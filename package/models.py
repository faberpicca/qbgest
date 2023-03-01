#from datetime import datetime
from package import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    data = db.Column(db.Date)
    data_decorrenza = db.Column(db.Date)
    data_scadenza = db.Column(db.Date)
    data_decorrenza_stampa = db.Column(db.Date)
    data_scadenza_stampa = db.Column(db.Date)
    anno_stampa = db.Column(db.Integer)
    dal = db.Column(db.Date)
    al = db.Column(db.Date)
    tipo_data = db.Column(db.Text())
    stato = db.Column(db.Text())
    bozze = db.Column(db.Boolean())
    partner_id = db.Column(db.Integer, db.ForeignKey('partner.id'))
    #roles = db.relationship('Role', secondary='user_roles')
    ruolo = db.Column(db.Text())

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# class Role(db.Model):
    # __tablename__ = 'role'
    # id = db.Column(db.Integer(), primary_key=True)
    # name = db.Column(db.String(50), unique=True)

# class UserRoles(db.Model):
    # __tablename__ = 'user_roles'
    # id = db.Column(db.Integer(), primary_key=True)
    # use_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'))
    # rol_id = db.Column(db.Integer(), db.ForeignKey('role.id', ondelete='CASCADE'))

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Impostazioni(db.Model):
    __tablename__ = 'impostazioni'
    id = db.Column(db.Integer, primary_key=True)
    azienda_partner_id = db.Column(db.Integer, db.ForeignKey('partner.id'))
    misc_registro_id = db.Column(db.Integer, db.ForeignKey('registro.id'))
    fatf_registro_id = db.Column(db.Integer, db.ForeignKey('registro.id'))
    notf_registro_id = db.Column(db.Integer, db.ForeignKey('registro.id'))
    fatc_registro_id = db.Column(db.Integer, db.ForeignKey('registro.id'))
    notc_registro_id = db.Column(db.Integer, db.ForeignKey('registro.id'))
    registro_autofattura_rc_id = db.Column(db.Integer, db.ForeignKey('registro.id'))
    registro_riconciliazione_rc_id = db.Column(db.Integer, db.ForeignKey('registro.id'))
    registro_riconciliazione_sp_id = db.Column(db.Integer, db.ForeignKey('registro.id'))
    erario_partner_id = db.Column(db.Integer, db.ForeignKey('partner.id'))
    starting_date = db.Column(db.Date)# da attivare ? Si è l'ultima data di apertura dello stato patrimoniale, da usare nei filtri se non si immette la data di inizio
    imap_server = db.Column(db.Text())
    imap_user = db.Column(db.Text())
    imap_pwd = db.Column(db.Text())
    pec_sdi = db.Column(db.Text())
    smtp_server = db.Column(db.Text())# da attivare
    smtp_user = db.Column(db.Text())# da attivare
    smtp_pwd = db.Column(db.Text())# da attivare
    sequenziale_sdi = db.Column(db.Integer)
    conto_perdite_profitti_id = db.Column(db.Integer, db.ForeignKey('conto.id'))
    conto_utile_id = db.Column(db.Integer, db.ForeignKey('conto.id'))
    conto_chiusura_id = db.Column(db.Integer, db.ForeignKey('conto.id'))
    conto_apertura_id = db.Column(db.Integer, db.ForeignKey('conto.id'))
    conto_lav_autonomo_id = db.Column(db.Integer, db.ForeignKey('conto.id'))
    ultimo_giorno_esercizio = db.Column(db.Text())

class Partner(db.Model):
    __tablename__ = 'partner'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.Text(), index=True)
    indirizzo = db.Column(db.Text())
    citta = db.Column(db.Text())
    comune = db.Column(db.Text())
    provincia = db.Column(db.Text())
    cap = db.Column(db.Text())
    email = db.Column(db.Text())
    fax = db.Column(db.Text())
    telefono = db.Column(db.Text())
    cellulare = db.Column(db.Text())
    iva = db.Column(db.Text())
    cf = db.Column(db.Text())
    pec = db.Column(db.Text())
    rea_codice = db.Column(db.Text())
    rea_capitale = db.Column(db.Numeric)
    rea_stato_liquidatione = db.Column(db.Text())
    rea_tipo_socio = db.Column(db.Text())
    rea_codice_provincia = db.Column(db.Integer)
    rea_ufficio = db.Column(db.Text())
    codice_destinatario = db.Column(db.Text())
    pa = db.Column(db.Boolean())
    lav_autonomo = db.Column(db.Boolean())
    iban = db.Column(db.Text())
    regime_fiscale = db.Column(db.Text())
    registrazione = db.relationship("Registrazione", backref='partner', foreign_keys="[Registrazione.partner_id]", passive_deletes='all')
    registrazione_domiciliatario = db.relationship("Registrazione", backref='domiciliatario', foreign_keys="[Registrazione.domiciliatario_id]", passive_deletes='all')
    movimento = db.relationship('Movimento', backref='partner', lazy='dynamic', passive_deletes='all')
    voce = db.relationship('Voce', backref='partner', lazy='dynamic', passive_deletes='all')
    user = db.relationship('User', backref='partner', lazy='dynamic')
    stampa = db.relationship('Stampa', backref='partner', lazy='dynamic', passive_deletes='all')
    impostazioni_azienda = db.relationship('Impostazioni', backref='azienda', foreign_keys="[Impostazioni.azienda_partner_id]", passive_deletes='all')
    impostazioni_erario = db.relationship("Impostazioni", backref='erario', foreign_keys="[Impostazioni.erario_partner_id]", passive_deletes='all')
    amministratore_id = db.Column(db.Integer, db.ForeignKey('partner.id'))
    amministratore = db.relationship("Partner", remote_side=id, foreign_keys="[Partner.amministratore_id]", single_parent=True, passive_deletes='all')
    letturista_id = db.Column(db.Integer, db.ForeignKey('partner.id'))
    letturista = db.relationship("Partner", remote_side=id, foreign_keys="[Partner.letturista_id]", single_parent=True, passive_deletes='all')

class Imposta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.Text())
    riferimento_normativo = db.Column(db.Text())
    aliquota = db.Column(db.Numeric)
    natura = db.Column(db.Text())
    esigibilita = db.Column(db.Text())
    indetraibile = db.Column(db.Boolean())
    rc = db.Column(db.Boolean())
    no_lipe = db.Column(db.Boolean())
    posizione = db.Column(db.Integer)
    voce = db.relationship('Voce', backref='imposta', lazy='dynamic', passive_deletes='all')#questo impedisce che venga cancellata l'imposta se dei record nella tabella voce puntano a questa
    voce_iva = db.relationship('Voce_iva', backref='imposta', lazy='dynamic', passive_deletes='all')

class Ritenuta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.Text())
    aliquota = db.Column(db.Numeric)
    registro_ritenuta_id = db.Column(db.Integer, db.ForeignKey('registro.id'))
    conto_transito_ritenuta_id = db.Column(db.Integer, db.ForeignKey('conto.id'))
    voce = db.relationship('Voce', backref='ritenuta', lazy='dynamic', passive_deletes='all')
    voce_ritenuta = db.relationship('Voce_ritenuta', backref='ritenuta', lazy='dynamic', passive_deletes='all')

class Pagamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.Text())
    modalita = db.Column(db.Text())
    condizioni = db.Column(db.Text())
    posizione = db.Column(db.Integer)
    registrazione = db.relationship('Registrazione', backref='pagamento', lazy='dynamic', passive_deletes='all')

class Mastro(db.Model):#conto di mastro
    id = db.Column(db.Integer, primary_key=True)
    codice = db.Column(db.Integer, index=True, unique=True)
    nome = db.Column(db.Text())
    tipo = db.Column(db.Text())
    sottomastro = db.relationship('Sottomastro', backref='mastro', lazy='dynamic', passive_deletes='all')

class Sottomastro(db.Model):#sottoconto di mastro
    id = db.Column(db.Integer, primary_key=True)
    codice = db.Column(db.Integer, index=True)
    nome = db.Column(db.Text())
    mastro_id = db.Column(db.Integer, db.ForeignKey('mastro.id'))
    conto = db.relationship('Conto', backref='sottomastro', lazy='dynamic', passive_deletes='all')

class Conto(db.Model):#conto analitico
    id = db.Column(db.Integer, primary_key=True)
    codice = db.Column(db.Integer, index=True)
    nome = db.Column(db.Text())
    descrizione = db.Column(db.Text())
    sottomastro_id = db.Column(db.Integer, db.ForeignKey('sottomastro.id'))
    movimento = db.relationship('Movimento', backref='conto', lazy='dynamic', passive_deletes='all')
    voce = db.relationship('Voce', backref='conto', lazy='dynamic', passive_deletes='all')
    registro = db.relationship('Registro', backref='conto', lazy='dynamic', foreign_keys="[Registro.conto_id]", passive_deletes='all')
    registro_precedente = db.relationship('Registro', backref='conto_precedente', lazy='dynamic', foreign_keys="[Registro.conto_precedente_id]", passive_deletes='all')
    #registro_successivo = db.relationship('Registro', backref='conto_successivo', lazy='dynamic', foreign_keys="[Registro.conto_successivo_id]", passive_deletes='all')
    registro_iva = db.relationship('Registro', backref='conto_iva', lazy='dynamic', foreign_keys="[Registro.conto_iva_id]", passive_deletes='all')
    conto_transito_ritenuta = db.relationship('Ritenuta', backref='conto_transito_ritenuta', lazy='dynamic', passive_deletes='all')
    filtro_conto = db.relationship('Filtro_conto', backref='conto', lazy='dynamic', passive_deletes='all')
    conto_perdite_profitti = db.relationship('Impostazioni', backref='conto_perdite_profitti', foreign_keys="[Impostazioni.conto_perdite_profitti_id]", lazy='dynamic', passive_deletes='all')
    conto_utile = db.relationship('Impostazioni', backref='conto_utile', foreign_keys="[Impostazioni.conto_utile_id]", lazy='dynamic', passive_deletes='all')
    conto_chiusura = db.relationship('Impostazioni', backref='conto_chiusura', foreign_keys="[Impostazioni.conto_chiusura_id]", lazy='dynamic', passive_deletes='all')
    conto_apertura = db.relationship('Impostazioni', backref='conto_apertura', foreign_keys="[Impostazioni.conto_apertura_id]", lazy='dynamic', passive_deletes='all')
    conto_lav_autonomo = db.relationship('Impostazioni', backref='conto_lav_autonomo', foreign_keys="[Impostazioni.conto_lav_autonomo_id]", lazy='dynamic', passive_deletes='all')

class Registro(db.Model):
    __tablename__ = 'registro'
    id = db.Column(db.Integer, primary_key=True)
    codice = db.Column(db.Text(), index=True, unique=True)
    nome = db.Column(db.Text())
    categoria = db.Column(db.Text())
    posizione = db.Column(db.Integer)
    segno = db.Column(db.Integer)
    conto_id = db.Column(db.Integer, db.ForeignKey('conto.id'))
    conto_precedente_id = db.Column(db.Integer, db.ForeignKey('conto.id'))
    #conto_successivo_id = db.Column(db.Integer, db.ForeignKey('conto.id'))
    conto_iva_id = db.Column(db.Integer, db.ForeignKey('conto.id'))
    registro_autofattura_rc = db.relationship("Impostazioni", backref='registro_autofattura_rc', foreign_keys="[Impostazioni.registro_autofattura_rc_id]", passive_deletes='all')
    registro_riconciliazione_rc = db.relationship("Impostazioni", backref='registro_riconciliazione_rc', foreign_keys="[Impostazioni.registro_riconciliazione_rc_id]", passive_deletes='all')
    registro_riconciliazione_sp = db.relationship("Impostazioni", backref='registro_riconciliazione_sp', foreign_keys="[Impostazioni.registro_riconciliazione_sp_id]", passive_deletes='all')
    registro_ritenuta = db.relationship("Ritenuta", backref='registro_ritenuta', lazy='dynamic', passive_deletes='all')
    registrazione = db.relationship('Registrazione', backref='registro', lazy='dynamic', passive_deletes='all')
    voce = db.relationship('Voce', backref='registro', lazy='dynamic', passive_deletes='all')
    filtro_registro = db.relationship('Filtro_registro', backref='registro', lazy='dynamic', cascade = "all, delete, delete-orphan")
    registro_misc = db.relationship("Impostazioni", backref='registro_misc', foreign_keys="[Impostazioni.misc_registro_id]", passive_deletes='all')
    registro_fatf = db.relationship("Impostazioni", backref='registro_fatf', foreign_keys="[Impostazioni.fatf_registro_id]", passive_deletes='all')
    registro_notf = db.relationship("Impostazioni", backref='registro_notf', foreign_keys="[Impostazioni.notf_registro_id]", passive_deletes='all')
    registro_fatc = db.relationship("Impostazioni", backref='registro_fatc', foreign_keys="[Impostazioni.fatc_registro_id]", passive_deletes='all')
    registro_notc = db.relationship("Impostazioni", backref='registro_notc', foreign_keys="[Impostazioni.notc_registro_id]", passive_deletes='all')
    tipo_documento_id = db.Column(db.Integer, db.ForeignKey('tipo_documento.id'))

class Registrazione(db.Model):
    __tablename__ = 'registrazione'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.Text())
    numero = db.Column(db.Integer)
    numero_origine = db.Column(db.Text())
    descrizione = db.Column(db.Text())
    data_contabile = db.Column(db.Date)
    data_decorrenza = db.Column(db.Date)
    data_scadenza = db.Column(db.Date)
    note = db.Column(db.Text())
    importo = db.Column(db.Numeric)
    saldo = db.Column(db.Numeric)
    stato = db.Column(db.Text())
    lav_autonomo = db.Column(db.Boolean())
    letturista = db.Column(db.Boolean())
    registro_id = db.Column(db.Integer, db.ForeignKey('registro.id'))
    partner_id = db.Column(db.Integer, db.ForeignKey('partner.id'))
    domiciliatario_id = db.Column(db.Integer, db.ForeignKey('partner.id'))
    validazione_id = db.Column(db.Integer, db.ForeignKey('validazione.id'))#questo in realta' se esiste e' la registrazione che ha originato questa, il nome migliore sarebbe origine
    pagamento_id = db.Column(db.Integer, db.ForeignKey('pagamento.id'))
    tipo_documento_id = db.Column(db.Integer, db.ForeignKey('tipo_documento.id'))
    movimento = db.relationship('Movimento', backref='registrazione', lazy='dynamic', cascade = "all, delete, delete-orphan")#se viene cancellata la registrazione allora anche tutti i movimenti che puntano a questo vengono cancellati
    voce = db.relationship('Voce', backref='registrazione', lazy='dynamic', foreign_keys="[Voce.registrazione_id]", cascade = "all, delete, delete-orphan")
    voce_iva = db.relationship('Voce_iva', backref='registrazione', lazy='dynamic', cascade = "all, delete, delete-orphan")
    voce_ritenuta = db.relationship('Voce_ritenuta', backref='registrazione', lazy='dynamic', cascade = "all, delete, delete-orphan")
    allegato = db.relationship('Allegato', backref='registrazione', lazy='dynamic', cascade = "all, delete, delete-orphan")
    validazione_backref = db.relationship('Validazione', backref='registrazione', lazy='dynamic', foreign_keys="[Validazione.registrazione_id]", cascade = "all, delete, delete-orphan")
    riconciliazione = db.relationship('Riconciliazione', backref='registrazione', lazy='dynamic', cascade = "all, delete, delete-orphan")
    riconciliazione_voce = db.relationship('Voce', backref='riconciliazione', lazy='dynamic', foreign_keys="[Voce.riconciliazione_id]", cascade = "all, delete, delete-orphan")
    filtro_registrazione = db.relationship('Filtro_registrazione', backref='registrazione', lazy='dynamic', cascade = "all, delete, delete-orphan")
    sdi = db.relationship('Sdi', backref='registrazione', lazy='dynamic')

class Voce_iva(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    imponibile = db.Column(db.Numeric)
    iva = db.Column(db.Numeric)
    registrazione_id = db.Column(db.Integer, db.ForeignKey('registrazione.id'))
    imposta_id = db.Column(db.Integer, db.ForeignKey('imposta.id'))

class Voce_ritenuta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    imponibile = db.Column(db.Numeric)
    ra = db.Column(db.Numeric)
    registrazione_id = db.Column(db.Integer, db.ForeignKey('registrazione.id'))
    ritenuta_id = db.Column(db.Integer, db.ForeignKey('ritenuta.id'))

class Validazione(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    registrazione_id = db.Column(db.Integer, db.ForeignKey('registrazione.id'))
    movimento = db.relationship('Movimento', backref='validazione', lazy='dynamic', cascade = "all, delete, delete-orphan")
    registrazione_backref = db.relationship('Registrazione', backref='validazione', lazy='dynamic', foreign_keys="[Registrazione.validazione_id]", cascade = "all, delete, delete-orphan")
    riconciliazione = db.relationship('Riconciliazione', backref='validazione', lazy='dynamic', cascade = "all, delete, delete-orphan")    

class Riconciliazione(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    registrazione_id = db.Column(db.Integer, db.ForeignKey('registrazione.id'))
    validazione_id = db.Column(db.Integer, db.ForeignKey('validazione.id'))
    movimento_id = db.Column(db.Integer, db.ForeignKey('movimento.id'))

class Movimento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descrizione = db.Column(db.Text())
    data_contabile = db.Column(db.Date)
    importo = db.Column(db.Numeric)
    conto_id = db.Column(db.Integer, db.ForeignKey('conto.id'))
    partner_id = db.Column(db.Integer, db.ForeignKey('partner.id'))
    registrazione_id = db.Column(db.Integer, db.ForeignKey('registrazione.id'))
    validazione_id = db.Column(db.Integer, db.ForeignKey('validazione.id'))
    riconciliazione = db.relationship('Riconciliazione', backref='movimento', lazy='dynamic')# cascade in questo caso non dovrebbe servire, cascade = "all, delete, delete-orphan")    

class Voce(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descrizione = db.Column(db.Text())
    quantita = db.Column(db.Numeric)
    importo = db.Column(db.Numeric)
    esercizio_precedente = db.Column(db.Boolean())
    registrazione_id = db.Column(db.Integer, db.ForeignKey('registrazione.id'))
    conto_id = db.Column(db.Integer, db.ForeignKey('conto.id'))
    imposta_id = db.Column(db.Integer, db.ForeignKey('imposta.id'))
    ritenuta_id = db.Column(db.Integer, db.ForeignKey('ritenuta.id'))
    riconciliazione_id = db.Column(db.Integer, db.ForeignKey('registrazione.id'))
    partner_id = db.Column(db.Integer, db.ForeignKey('partner.id'))
    registro_id = db.Column(db.Integer, db.ForeignKey('registro.id'))# se presente indica una ricevuta verso il partner

class Allegato(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.Text(), index=True)
    binario = db.Column(db.LargeBinary())
    registrazione_id = db.Column(db.Integer, db.ForeignKey('registrazione.id'))
    stampa_id = db.Column(db.Integer, db.ForeignKey('stampa.id'))
    sdi_id = db.Column(db.Integer, db.ForeignKey('sdi.id'))
    pagina_stampa = db.Column(db.Integer)

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime)
    user = db.Column(db.Text())
    datalog = db.Column(db.Text())

class Registro_stampa(db.Model):
    __tablename__ = 'registro_stampa'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.Text())
    categoria = db.Column(db.Text())
    posizione = db.Column(db.Integer)
    filtro_registro = db.relationship('Filtro_registro', backref='registro_stampa', lazy='dynamic', cascade = "all, delete, delete-orphan")
    stampa = db.relationship('Stampa', backref='registro_stampa', lazy='dynamic', passive_deletes='all')

class Filtro_registro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    registro_id = db.Column(db.Integer, db.ForeignKey('registro.id'))
    registro_stampa_id = db.Column(db.Integer, db.ForeignKey('registro_stampa.id'))

class Stampa(db.Model):
    __tablename__ = 'stampa'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.Text())
    data_decorrenza = db.Column(db.Date)
    data_scadenza = db.Column(db.Date)
    anno_stampa = db.Column(db.Integer)
    precedente_pagina_stampa = db.Column(db.Integer)
    ultima_pagina_stampa = db.Column(db.Integer)
    precedente_riga_stampa = db.Column(db.Integer)
    ultima_riga_stampa = db.Column(db.Integer)
    partner_id = db.Column(db.Integer, db.ForeignKey('partner.id'))
    allegato = db.relationship('Allegato', backref='stampa', lazy='dynamic', cascade = "all, delete, delete-orphan")
    registro_stampa_id = db.Column(db.Integer, db.ForeignKey('registro_stampa.id'))
    filtro_conto = db.relationship('Filtro_conto', backref='stampa', lazy='dynamic', cascade = "all, delete, delete-orphan")
    filtro_registrazione = db.relationship('Filtro_registrazione', backref='stampa', lazy='dynamic', cascade = "all, delete, delete-orphan")
    VP7 = db.Column(db.Numeric)
    VP8 = db.Column(db.Numeric)
    VP9 = db.Column(db.Numeric)
    VP10 = db.Column(db.Numeric)
    VP11 = db.Column(db.Numeric)

class Filtro_conto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conto_id = db.Column(db.Integer, db.ForeignKey('conto.id'))
    stampa_id = db.Column(db.Integer, db.ForeignKey('stampa.id'))

class Filtro_registrazione(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    registrazione_id = db.Column(db.Integer, db.ForeignKey('registrazione.id'))
    stampa_id = db.Column(db.Integer, db.ForeignKey('stampa.id'))

class Sdi(db.Model):
    __tablename__ = 'sdi'
    id = db.Column(db.Integer, primary_key=True)
    inbox = db.Column(db.Boolean())
    nome = db.Column(db.Text())
    timestamp = db.Column(db.DateTime)
    fattura = db.Column(db.Boolean())
    sent = db.Column(db.Boolean())
    registrazione_id = db.Column(db.Integer, db.ForeignKey('registrazione.id'))
    allegato = db.relationship('Allegato', backref='sdi', lazy='dynamic', cascade = "all, delete, delete-orphan")

class Filtro_estratto_conto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    originale = db.Column(db.Text())
    sostituto = db.Column(db.Text())

class Tipo_documento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descrizione = db.Column(db.Text())
    codice = db.Column(db.Text())
    posizione = db.Column(db.Integer)
    registrazione = db.relationship('Registrazione', backref='tipo_documento', lazy='dynamic', passive_deletes='all')
    registro = db.relationship('Registro', backref='tipo_documento', lazy='dynamic', passive_deletes='all')
