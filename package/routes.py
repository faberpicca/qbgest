from lxml import etree
from lxml import objectify
import base64
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from flask import render_template, flash, redirect, url_for, request, send_file, current_app
from flask_login import login_user, logout_user, current_user, login_required
#from flask_user import roles_required, UserManager
from werkzeug.urls import url_parse
from package import app, db
from package.forms import *
from package.models import *
from sqlalchemy import Integer, cast, func, and_, or_
from natsort import natsort_keygen
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.utils import simpleSplit
import copy
import locale
from sqlalchemy.orm.session import make_transient
import os
import io
from decimal import *
import time
import imaplib
import email
from email.header import decode_header
import base64
import xml.etree.ElementTree as ET
from subprocess import call
from flask_mail import Message
#from package import mail
from flask_mail import Mail

from functools import wraps

#user_manager = UserManager(app, db, User)

#footer='CENTRALE TERMICA FOSSOLO SOC. COOPERATIVA - VIA MISA 1 - 40139 BOLOGNA - P.IVA 00324170372 - CF 00324170372'

here = os.path.dirname(__file__)

locale.setlocale(locale.LC_ALL, 'it_IT.utf8')

key1 = natsort_keygen(key=lambda x: x.nome.lower())

LOCK=[False]

L=['0','1','2','3','4','5','6','7','8','9','A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z','a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z']


#from app.common import *
#from app.impostazioni import *
#from app.fattura import *
#from app.ricevuta import *
#from app.cassa import *
#from app.generico import *
#from app.iva import *
#from app.stampa import *
#from app.partner import *
#from app.sdi import *

#def chunkstring(string, length):
#    return (string[0+i:length+i] for i in range(0, len(string), length))

def chunkstring(string,length):
    words=string.split()
    records=[]
    row=words[0]
    for w in words[1:]:
        if len(row+" "+w)<=length:row+=" "+w
        else:
            records.append(row)
            row=w
    if row!="":records.append(row)
    return records

def requires_roles(*roles):
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if current_user.ruolo not in roles:
                # Redirect the user to an unauthorized notice!
                flash('Non hai i privilegi per accedere a questa pagina !')
                return redirect(url_for('index'))
                #return "You are not authorized to access this page"
            return f(*args, **kwargs)
        return wrapped
    return wrapper

# def requires_access_level(access_level):
    # def decorator(f):
        # @wraps(f)
        # def decorated_function(*args, **kwargs):
            # if not session.get('email'):
                # return redirect(url_for('login'))

            # user = User.find_by_email(session['email'])
            # elif not user.allowed(access_level):
                # return redirect(url_for('index', message="You do not have access to that page. Sorry!"))
            # return f(*args, **kwargs)
        # return decorated_function
    # return decorator

# M A I N #########################################################################
@app.route('/')
@app.route('/index')
@login_required
def index():
    return render_template('index.html', title='Home')
    #return redirect(url_for('immobili'))

@app.route('/wait')
def wait():
    #l=request.args.get('link')
    return render_template ("wait.html", link="test")

@app.route('/test')
def test():
    #a=request.args.get('prova')
    print("Test")
    time.sleep(3)
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        user.data=date.today()
        unlock()
        db.session.commit()
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
@login_required
@requires_roles('admin')
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("L'utente e' stato aggiunto")
        return redirect(url_for('index'))
    return render_template('register.html', title='Register', form=form)

@app.route('/modifica_data', methods=['GET', 'POST'])
@login_required
def modifica_data():
    form = ConfermaForm()
    if form.validate_on_submit():
        current_user.data = form.data_delibera.data
        db.session.commit()
        flash('La data è stata modificata !')
        return redirect(url_for('registri'))
    form.data_delibera.data = current_user.data
    return render_template('data.html', testo="Impostare una nuova data ", form=form)

@app.route('/chiusura_apertura', methods=['GET', 'POST'])
@login_required
@requires_roles('admin')
def chiusura_apertura():#genera le scritture contabili di chiusura e riapertura anno fiscale
    impostazioni=Impostazioni.query.get(1)
    anno=current_user.data.year
    filter_al=datetime.strptime(impostazioni.ultimo_giorno_esercizio+"/"+str(anno-1),"%d/%m/%Y").date()
    filter_dal=filter_al+relativedelta(days=1)-relativedelta(years=1)
    form = ConfermaForm()
    if form.validate_on_submit():
        #filter_dal = current_user.dal
        #filter_al = current_user.al
        registrazione=Registrazione(registro=impostazioni.registro_misc,data_contabile=filter_al, descrizione="Chiusura conto economico")
        db.session.add(registrazione)
        utile=0
        conti = Conto.query.join(Sottomastro).join(Mastro).filter(Mastro.tipo=="Costi").order_by(Sottomastro.codice).order_by(Conto.codice).all()
        for c in conti:
            filtro="filter(Movimento.conto==c)."
            if filter_dal!=None:filtro+="filter(Movimento.data_contabile>=filter_dal)."
            if filter_al!=None:filtro+="filter(Movimento.data_contabile<=filter_al)."
            totale=(eval("db.session.query(func.sum(Movimento.importo))."+filtro+"scalar()") or 0)
            utile+=totale
            if totale!=0:
                voce=Voce(registrazione=registrazione, conto=c, importo=-totale, descrizione="Chiusura conto economico")
                db.session.add(voce)
        conti = Conto.query.join(Sottomastro).join(Mastro).filter(Mastro.tipo=="Ricavi").order_by(Sottomastro.codice).order_by(Conto.codice).all()
        for c in conti:
            filtro="filter(Movimento.conto==c)."
            if filter_dal!=None:filtro+="filter(Movimento.data_contabile>=filter_dal)."
            if filter_al!=None:filtro+="filter(Movimento.data_contabile<=filter_al)."
            totale=(eval("db.session.query(func.sum(Movimento.importo))."+filtro+"scalar()") or 0)
            utile+=totale
            if totale!=0:
                voce=Voce(registrazione=registrazione, conto=c, importo=-totale, descrizione="Chiusura conto economico")
                db.session.add(voce)
        voce=Voce(registrazione=registrazione, conto=impostazioni.conto_perdite_profitti, importo=utile, descrizione="Chiusura conto economico")
        db.session.add(voce)
        db.session.commit()
        reg_generico(registrazione)

        registrazione=Registrazione(registro=impostazioni.registro_misc,data_contabile=filter_al, descrizione="Utile esercizio")
        db.session.add(registrazione)
        voce=Voce(registrazione=registrazione, conto=impostazioni.conto_perdite_profitti, importo=-utile, descrizione="Utile esercizio")
        db.session.add(voce)
        voce=Voce(registrazione=registrazione, conto=impostazioni.conto_utile, importo=utile, descrizione="Utile esercizio")
        db.session.add(voce)
        db.session.commit()
        reg_generico(registrazione)

        chiusura_passivita=Registrazione(registro=impostazioni.registro_misc,data_contabile=filter_al, descrizione="Chiusura stato patrimoniale - Passività")
        db.session.add(chiusura_passivita)
        chiusura_attivita=Registrazione(registro=impostazioni.registro_misc,data_contabile=filter_al, descrizione="Chiusura stato patrimoniale - Attività")
        db.session.add(chiusura_attivita)
        apertura_passivita=Registrazione(registro=impostazioni.registro_misc,data_contabile=filter_al+relativedelta(days=1), descrizione="Apertura stato patrimoniale - Passività")
        db.session.add(apertura_passivita)
        apertura_attivita=Registrazione(registro=impostazioni.registro_misc,data_contabile=filter_al+relativedelta(days=1), descrizione="Apertura stato patrimoniale - Attività")
        db.session.add(apertura_attivita)
        conti = Conto.query.join(Sottomastro).join(Mastro).filter(Mastro.tipo=="Passività").order_by(Sottomastro.codice).order_by(Conto.codice).all()
        passivita=0
        for c in conti:
            filtro="filter(Movimento.conto==c)."
            if filter_dal!=None:filtro+="filter(Movimento.data_contabile>=filter_dal)."
            if filter_al!=None:filtro+="filter(Movimento.data_contabile<=filter_al)."
            totale=(eval("db.session.query(func.sum(Movimento.importo))."+filtro+"scalar()") or 0)
            passivita+=totale
            if totale!=0:
                voce=Voce(registrazione=chiusura_passivita, conto=c, importo=-totale, descrizione="Chiusura stato patrimoniale - Passività")
                db.session.add(voce)
                voce=Voce(registrazione=apertura_passivita, conto=c, importo=totale, descrizione="Apertura stato patrimoniale - Passività")
                db.session.add(voce)
        voce=Voce(registrazione=chiusura_passivita, conto=impostazioni.conto_chiusura, importo=passivita, descrizione="Passività")
        voce=Voce(registrazione=apertura_passivita, conto=impostazioni.conto_apertura, importo=-passivita, descrizione="Passività")
        conti = Conto.query.join(Sottomastro).join(Mastro).filter(Mastro.tipo=="Attività").order_by(Sottomastro.codice).order_by(Conto.codice).all()
        attivita=0
        for c in conti:
            filtro="filter(Movimento.conto==c)."
            if filter_dal!=None:filtro+="filter(Movimento.data_contabile>=filter_dal)."
            if filter_al!=None:filtro+="filter(Movimento.data_contabile<=filter_al)."
            totale=(eval("db.session.query(func.sum(Movimento.importo))."+filtro+"scalar()") or 0)
            attivita+=totale
            if totale!=0:
                voce=Voce(registrazione=chiusura_attivita, conto=c, importo=-totale, descrizione="Chiusura stato patrimoniale - Attività ")
                db.session.add(voce)
                voce=Voce(registrazione=apertura_attivita, conto=c, importo=totale, descrizione="Apertura stato patrimoniale - Attività")
                db.session.add(voce)
        voce=Voce(registrazione=chiusura_attivita, conto=impostazioni.conto_chiusura, importo=attivita, descrizione="Attività")
        voce=Voce(registrazione=apertura_attivita, conto=impostazioni.conto_apertura, importo=-attivita, descrizione="Attività")
        reg_generico(chiusura_attivita)
        reg_generico(chiusura_passivita)
        reg_generico(apertura_attivita)
        reg_generico(apertura_passivita)
        impostazioni.starting_date=filter_al+relativedelta(days=1)
        db.session.commit()

        return redirect(url_for('registrazioni', id=impostazioni.registro_misc.id))
    form.data_delibera.data = current_user.data
    return render_template('conferma.html', testo="Generare le scritture per la chiusura e la riapertura dei conti per il periodo dal "+filter_dal.strftime("%d/%m/%Y")+" al "+filter_al.strftime("%d/%m/%Y")+" ?", form=form)

@app.route('/conti')
@login_required
def conti():#mostra il saldo di tutti i conti
    impostazioni=Impostazioni.query.get(1)
    conti = Conto.query.join(Sottomastro).join(Mastro).order_by(Mastro.codice).order_by(Sottomastro.codice).order_by(Conto.codice).all()
    saldo=[]
    for c in conti:
        filtro="filter(Movimento.conto==c)."
        filtro+="filter(Movimento.data_contabile>=impostazioni.starting_date)."
        saldo.append(eval("db.session.query(func.sum(Movimento.importo))."+filtro+"scalar()") or 0)
    return render_template('conti.html', conti=conti, saldo=saldo, inizio=impostazioni.starting_date)

@app.route('/movimenti/<id>', methods=['GET', 'POST'])
@login_required
def movimenti(id):#mostra i movimenti sul singolo conto
    impostazioni=Impostazioni.query.get(1)
    conto=Conto.query.get(id)
    filtro_form=FiltroForm()
    partners = Partner.query.order_by(Partner.nome).with_entities(Partner.nome).all()
    if filtro_form.validate_on_submit():
        current_user.dal=filtro_form.dal.data
        current_user.al=filtro_form.al.data
        current_user.bozze=filtro_form.bozze.data
        current_user.partner=Partner.query.filter_by(nome=filtro_form.partner.data).first()
        datalog="Modificato filtro: dal["+format_date(current_user.dal)+"] al["+format_date(current_user.al)+"] tipo["+str(current_user.tipo_data)+"] stato["+str(current_user.stato)+"] bozze["+str(current_user.bozze)+"] partner["+nome(current_user.partner)+"]"
        log = Log(datalog=datalog, user=current_user.username, timestamp = func.now())
        db.session.add(log)
        db.session.commit()
    if filtro_form.is_submitted() and not filtro_form.validate():pass
    else:
        filtro_form.dal.data=current_user.dal
        filtro_form.al.data=current_user.al
        filtro_form.tipo_data.data=current_user.tipo_data
        filtro_form.stato.data=current_user.stato
        filtro_form.bozze.data=current_user.bozze
        if current_user.partner != None: filtro_form.partner.data=current_user.partner.nome
    filtro="filter(Movimento.conto==conto)."
    filter_partner = current_user.partner
    filter_dal = current_user.dal
    filter_al = current_user.al
    if filter_partner!=None:filtro+="filter(Movimento.partner==filter_partner)."
    if filter_dal!=None:filtro+="filter(Movimento.data_contabile>=filter_dal)."
    if filter_al!=None:filtro+="filter(Movimento.data_contabile<=filter_al)."
    movimenti= eval("Movimento.query."+filtro+"order_by(Movimento.data_contabile).order_by(Movimento.id).all()")
    dare = eval("db.session.query(func.sum(Movimento.importo))."+filtro+"filter(Movimento.importo>0).scalar()") or 0
    avere = eval("db.session.query(func.sum(Movimento.importo))."+filtro+"filter(Movimento.importo<0).scalar()") or 0
    avere=-avere
    return render_template('movimenti.html', conto=conto, movimenti=movimenti, dare=dare, avere=avere, filtro_form=filtro_form, partners=partners)

@app.route('/registri')
@login_required
def registri():#mostra il totale ed il saldo di tutti i registri
    impostazioni=Impostazioni.query.get(1)
    registri = Registro.query.order_by(Registro.posizione).all()
    totale=[]
    saldo=[]
    for r in registri:
        if r.categoria=="Fattura" or r.categoria=="Ricevuta" or r.categoria=="IVA":
            filtro="filter(Registrazione.registro==r)."
            filtro+="filter(Registrazione.numero!=None)."
            filtro+="filter(Registrazione.data_contabile>=impostazioni.starting_date)."
            tot=eval("db.session.query(func.sum(Registrazione.importo))."+filtro+"scalar()") or 0
            sal=eval("db.session.query(func.sum(Registrazione.saldo))."+filtro+"scalar()") or 0
            totale.append(r.segno*tot)
            saldo.append(r.segno*sal)
        else:
            tot=eval("db.session.query(func.sum(Registrazione.importo)).filter(Registrazione.registro==r).filter(Registrazione.numero!=None).scalar()") or 0
            totale_bozze= eval("db.session.query(func.sum(Registrazione.importo)).filter(Registrazione.registro==r).filter(Registrazione.numero==None).scalar()") or 0
            totale.append(tot+totale_bozze)
            saldo.append(totale_bozze)
    return render_template('registri.html', registri=registri, totale=totale, saldo=saldo, inizio=impostazioni.starting_date)

@app.route('/duplica_registrazione/<id>')
@login_required
def duplica_registrazione(id):#duplica una registrazione
    nuovaregistrazione=Registrazione.query.get(id)
    db.session.expunge(nuovaregistrazione)
    make_transient(nuovaregistrazione)
    nuovaregistrazione.id = None
    nuovaregistrazione.nome = None
    nuovaregistrazione.numero = None
    nuovaregistrazione.validazione = None
    nuovaregistrazione.stato = None
    nuovaregistrazione.saldo = 0
    db.session.add(nuovaregistrazione)
    registrazione=Registrazione.query.get(id)
    voci=Voce.query.filter_by(registrazione=registrazione).order_by(Voce.id)
    for v in voci:
        nuovavoce=v
        db.session.expunge(nuovavoce)
        make_transient(nuovavoce)
        nuovavoce.id = None
        nuovavoce.registrazione = nuovaregistrazione
        db.session.add(nuovavoce)
    voci_iva=Voce_iva.query.filter_by(registrazione=registrazione).order_by(Voce_iva.id)
    for v in voci_iva:
        nuovavoce=v
        db.session.expunge(nuovavoce)
        make_transient(nuovavoce)
        nuovavoce.id = None
        nuovavoce.registrazione = nuovaregistrazione
        db.session.add(nuovavoce)
    voci_ritenuta=Voce_ritenuta.query.filter_by(registrazione=registrazione).order_by(Voce_ritenuta.id)
    for v in voci_ritenuta:
        nuovavoce=v
        db.session.expunge(nuovavoce)
        make_transient(nuovavoce)
        nuovavoce.id = None
        nuovavoce.registrazione = nuovaregistrazione
        db.session.add(nuovavoce)
    db.session.commit()
    #id=Registrazione.query.get(id).registro.id
    #return redirect(url_for('registrazioni', id=id))
    return redirect(url_for('registrazione', id=nuovaregistrazione.id))

@app.route('/aggiungi_registrazione/<id>')
@login_required
def aggiungi_registrazione(id):#aggiunge una registrazione
    registro=Registro.query.get(id)
    registrazione=Registrazione(registro=registro, importo=0, saldo=0, data_contabile=current_user.data)
    if registro.categoria=="Fattura":
        registrazione.data_decorrenza=current_user.data_decorrenza
        registrazione.data_scadenza=current_user.data_scadenza
        registrazione.tipo_documento=registrazione.registro.tipo_documento
    db.session.add(registrazione)
    db.session.commit()
    #return redirect(url_for('registrazioni', id=id))
    return redirect(url_for('registrazione', id=registrazione.id))

@app.route('/rimuovi_registrazione/<id>', methods=['GET', 'POST'])
@login_required
def rimuovi_registrazione(id):#rimuove una registrazione
    registrazione=Registrazione.query.get(id)
    form = ConfermaForm()
    if form.validate_on_submit():
        id=registrazione.registro.id
        db.session.delete(registrazione)
        db.session.commit()
        return redirect(url_for('registrazioni', id=id))
    form.data_delibera.data = current_user.data
    testo=registrazione.descrizione
    if testo==None:testo="None"
    return render_template('conferma.html', testo="Rimozione della registrazione "+testo, form=form)

@app.route('/annulla_registrazione/<id>')
@login_required
def annulla_registrazione(id):#annulla una registrazione e annulla (o elimina, dipende dai casi) tutte le registrazioni che dipendono da questa
    registrazione=Registrazione.query.get(id)
    RDA=[registrazione]
    TRDA=None
    reg_saldo=[]
    while RDA != TRDA:#cerca tutte le registrazioni coinvolte nell'annullamento della prima e quelle per quale occore ricalcolare il saldo
        TRDA=RDA[:]
        for registrazione in TRDA:
            riconciliazioni=Riconciliazione.query.filter_by(registrazione=registrazione).all()
            for r in riconciliazioni:
                reg=r.validazione.registrazione
                if reg not in RDA: RDA.append(reg)
            registrazioni=Registrazione.query.filter_by(validazione=registrazione.validazione_backref.first()).all()
            for reg in registrazioni:
                if reg not in RDA: RDA.append(reg)
            riconciliazioni=Riconciliazione.query.filter_by(validazione=registrazione.validazione_backref.first()).all()
            for r in riconciliazioni:
                if r.registrazione not in reg_saldo: reg_saldo.append(r.registrazione)
    #print("Registrazioni da annullare")
    #for reg in RDA:
    #    print(reg.nome)
    text=""
    for reg in RDA:#ho trovato le registrazioni da annullare, quindi le annullo
        if reg != None:
            text+=" "+reg.nome
            if reg.partner!=None:partner_nome=reg.partner.nome
            else:partner_nome=""
            datalog="Annullata registrazione ["+reg.nome+"] importo["+str(reg.importo)+"] partner["+partner_nome+"] data contabile["+format_date(reg.data_contabile)+"] data registrazione["+format_date(reg.data_decorrenza)+"] data scadenza["+format_date(reg.data_scadenza)+"]"
            log = Log(datalog=datalog, user=current_user.username, timestamp = func.now())
            db.session.add(log)
            reg.numero=None
            reg.nome=None
            validazione=reg.validazione_backref.first()
            if validazione != None: db.session.delete(validazione)
            #db.session.delete(validazione)
    #print("Registrazioni dove ricalcolare il saldo")
    #for r in reg_saldo:
    #    print(r.nome)
    db.session.commit()
    saldo(reg_saldo)
    flash("Sono state annullate le registrazioni "+text)
    return redirect(url_for('registrazione', id=id))

@app.route('/registrazioni/<id>', methods=['GET', 'POST'])
@login_required
def registrazioni(id):#mostra le registrazioni appartenenti ad un registro
    impostazioni=Impostazioni.query.get(1)
    if id=="0":
        registrazioni = Registrazione.query.all()
        return render_template('registrazioni.html', registrazioni=registrazioni)
    registro=Registro.query.get(id)
    partners = Partner.query.order_by(Partner.nome).with_entities(Partner.nome).all()
    categoria=registro.categoria
    filtro_form=FiltroForm()
    import_form = ImportForm()
    if categoria=="Fattura" or categoria=="Ricevuta" or categoria=="IVA":
        if filtro_form.validate_on_submit():
            current_user.dal=filtro_form.dal.data
            current_user.al=filtro_form.al.data
            current_user.tipo_data=filtro_form.tipo_data.data
            current_user.stato=filtro_form.stato.data
            current_user.bozze=filtro_form.bozze.data
            current_user.partner=Partner.query.filter_by(nome=filtro_form.partner.data).first()
            datalog="Modificato filtro: dal["+format_date(current_user.dal)+"] al["+format_date(current_user.al)+"] tipo["+str(current_user.tipo_data)+"] stato["+str(current_user.stato)+"] bozze["+str(current_user.bozze)+"] partner["+nome(current_user.partner)+"]"
            log = Log(datalog=datalog, user=current_user.username, timestamp = func.now())
            db.session.add(log)
            db.session.commit()
        if filtro_form.is_submitted() and not filtro_form.validate():pass
        else:
            filtro_form.dal.data=current_user.dal
            filtro_form.al.data=current_user.al
            filtro_form.tipo_data.data=current_user.tipo_data
            filtro_form.stato.data=current_user.stato
            filtro_form.bozze.data=current_user.bozze
            if current_user.partner != None: filtro_form.partner.data=current_user.partner.nome
        filtro="filter(Registrazione.registro==registro)."
        filter_partner = current_user.partner
        filter_dal = current_user.dal
        #if filter_dal==None:filter_dal=impostazioni.starting_date
        filter_al = current_user.al
        #if filter_partner!=None:filtro+="filter_by(partner=filter_partner)."
        if filter_partner!=None:filtro+="filter(or_(Registrazione.partner==filter_partner, Registrazione.domiciliatario==filter_partner))."
        if current_user.stato=="insolute":filtro+="filter(Registrazione.saldo!=0)."
        if filter_dal!=None:filtro+="filter(Registrazione."+current_user.tipo_data+">=filter_dal)."
        if filter_al!=None:filtro+="filter(Registrazione."+current_user.tipo_data+"<=filter_al)."
        registr= eval("Registrazione.query."+filtro+"filter(Registrazione.numero!=None).order_by(Registrazione.nome.desc()).all()")
        bozze= eval("Registrazione.query."+filtro+"filter(Registrazione.numero==None).order_by(Registrazione.id.desc()).all()")
        totale = eval("db.session.query(func.sum(Registrazione.importo))."+filtro+"filter(Registrazione.numero!=None).scalar()") or 0
        totale_bozze = eval("db.session.query(func.sum(Registrazione.importo))."+filtro+"filter(Registrazione.numero==None).scalar()") or 0
        saldo = eval("db.session.query(func.sum(Registrazione.saldo))."+filtro+"filter(Registrazione.numero!=None).scalar()") or 0
        saldo_bozze = eval("db.session.query(func.sum(Registrazione.saldo))."+filtro+"filter(Registrazione.numero==None).scalar()") or 0
        if not current_user.bozze:
            totale_bozze=0
            saldo_bozze=0
            bozze=[]
        totale=totale+totale_bozze
        saldo=saldo+saldo_bozze
        registrazioni=bozze+registr
        return render_template('fatture.html', registrazioni=registrazioni, registro=registro, filtro_form=filtro_form, partners=partners, totale=totale, saldo=saldo)
    if categoria=="Cassa":
        if import_form.submit2.data and import_form.validate():
            filtro=Filtro_estratto_conto.query.all()
            filename=os.path.join(here, 'estratto.txt')
            import_form.file.data.save(filename)
            text=[]
            in_file=open(filename,"r")
            while True:
                line=in_file.readline()
                if len(line)<2: break
                text.append(line)
            in_file.close()
            data,descrizione,importo=[],[],[]
            for r in text:
                if r[0]=="D": data.append(datetime.strptime(r[1:-1],"%m/%d/%Y").date())
                if r[0]=="M":
                    while "  " in r: r=r.replace("  ", " ")
                    #for f in filtro: print(f.originale, f.sostituto)
                    for f in filtro: r=r.replace(f.originale, f.sostituto)
                    while "  " in r: r=r.replace("  ", " ")
                    descrizione.append(r[1:-1])
                if r[0]=="T": importo.append(dec(r[1:-1].replace(",","")))
            for i in range(len(data)):
                registrazione=Registrazione(registro=registro, importo=importo[i], data_contabile=data[i], descrizione=descrizione[i])
                db.session.add(registrazione)
                voce=Voce(registrazione=registrazione, descrizione=descrizione[i], conto=registrazione.registro.conto, importo=importo[i])
                db.session.add(voce)
            datalog="Importato estratto conto nel registro ["+registro.nome+"]"
            log = Log(datalog=datalog, user=current_user.username, timestamp = func.now())
            db.session.add(log)
            db.session.commit()
            return redirect(url_for('registrazioni', id=id))
        if filtro_form.submit_filtro.data and filtro_form.validate():
            current_user.dal=filtro_form.dal.data
            current_user.al=filtro_form.al.data
            current_user.bozze=filtro_form.bozze.data
            current_user.partner=Partner.query.filter_by(nome=filtro_form.partner.data).first()
            datalog="Modificato filtro: dal["+format_date(current_user.dal)+"] al["+format_date(current_user.al)+"] tipo["+str(current_user.tipo_data)+"] stato["+str(current_user.stato)+"] bozze["+str(current_user.bozze)+"] partner["+nome(current_user.partner)+"]"
            log = Log(datalog=datalog, user=current_user.username, timestamp = func.now())
            db.session.add(log)
            db.session.commit()
        if filtro_form.is_submitted() and not filtro_form.validate():pass
        else:
            filtro_form.dal.data=current_user.dal
            filtro_form.al.data=current_user.al
            filtro_form.tipo_data.data=current_user.tipo_data
            filtro_form.stato.data=current_user.stato
            filtro_form.bozze.data=current_user.bozze
            if current_user.partner != None: filtro_form.partner.data=current_user.partner.nome
        filter_partner = current_user.partner
        filter_dal = current_user.dal
        #if filter_dal==None:filter_dal=impostazioni.starting_date
        filter_al = current_user.al
        if filter_dal!=None:filtro_dal="filter(Registrazione.data_contabile>=filter_dal)."
        else:filtro_dal=""
        if filter_al!=None:filtro_al="filter(Registrazione.data_contabile<=filter_al)."
        else:filtro_al=""
        filtro="filter(Registrazione.registro==registro)."
        if filter_partner!=None:filtro+="filter(Registrazione.partner==filter_partner)."
        bozze= eval("Registrazione.query."+filtro+filtro_al+"filter(Registrazione.numero==None).order_by(Registrazione.data_contabile).order_by(Registrazione.id).all()")
        registr= eval("Registrazione.query."+filtro+filtro_dal+filtro_al+"filter(Registrazione.numero!=None).order_by(Registrazione.data_contabile.desc()).order_by(Registrazione.nome.desc()).all()")
        #totale = eval("db.session.query(func.sum(Registrazione.importo))."+filtro+filtro_dal+filtro_al+"filter(Registrazione.numero!=None).scalar()") or 0
        totale = eval("db.session.query(func.sum(Registrazione.importo))."+filtro+filtro_al+"filter(Registrazione.numero!=None).scalar()") or 0
        totale_bozze = eval("db.session.query(func.sum(Registrazione.importo))."+filtro+filtro_al+"filter(Registrazione.numero==None).scalar()") or 0

        saldo_iniziale=0
        if filter_dal!=None:
            # anno=filter_dal.year#calcola il saldo iniziale nei conti tipo cassa
            # fine_esercizio_anno=datetime.strptime(impostazioni.ultimo_giorno_esercizio+"/"+str(anno),"%d/%m/%Y").date()
            # if filter_dal > fine_esercizio_anno:inizio_esercizio=fine_esercizio_anno+relativedelta(days=1)
            # else:inizio_esercizio=fine_esercizio_anno-relativedelta(years=1)+relativedelta(days=1)
            # if inizio_esercizio>impostazioni.starting_date:inizio_esercizio=impostazioni.starting_date
            # #inizio_esercizio=impostazioni.starting_date#pezza messa per correggere al volo, da sistemare
            # saldo_iniziale=eval("db.session.query(func.sum(Registrazione.importo))."+filtro+"filter(Registrazione.data_contabile>=inizio_esercizio).filter(Registrazione.data_contabile<filter_dal).scalar()") or 0
            saldo_iniziale=eval("db.session.query(func.sum(Registrazione.importo))."+filtro+"filter(Registrazione.data_contabile<filter_dal).scalar()") or 0

        if not current_user.bozze:
            totale_bozze=0
            bozze=[]
        totale=totale+totale_bozze
        registrazioni=bozze+registr
        return render_template('casse.html', registrazioni=registrazioni, registro=registro, filtro_form=filtro_form, import_form = import_form, partners=partners, totale=totale, saldo_iniziale=saldo_iniziale)
    if categoria=="Generico":
        if filtro_form.submit_filtro.data and filtro_form.validate():
            current_user.dal=filtro_form.dal.data
            current_user.al=filtro_form.al.data
            current_user.bozze=filtro_form.bozze.data
            current_user.partner=Partner.query.filter_by(nome=filtro_form.partner.data).first()
            datalog="Modificato filtro: dal["+format_date(current_user.dal)+"] al["+format_date(current_user.al)+"] tipo["+str(current_user.tipo_data)+"] stato["+str(current_user.stato)+"] bozze["+str(current_user.bozze)+"] partner["+nome(current_user.partner)+"]"
            log = Log(datalog=datalog, user=current_user.username, timestamp = func.now())
            db.session.add(log)
            db.session.commit()
        if filtro_form.is_submitted() and not filtro_form.validate():pass
        else:
            filtro_form.dal.data=current_user.dal
            filtro_form.al.data=current_user.al
            filtro_form.tipo_data.data=current_user.tipo_data
            filtro_form.stato.data=current_user.stato
            filtro_form.bozze.data=current_user.bozze
            if current_user.partner != None: filtro_form.partner.data=current_user.partner.nome
        filtro="filter_by(registro=registro)."
        filter_partner = current_user.partner
        filter_dal = current_user.dal
        #if filter_dal==None:filter_dal=impostazioni.starting_date
        filter_al = current_user.al
        if filter_partner!=None:filtro+="filter_by(partner=filter_partner)."
        if filter_dal!=None:filtro+="filter(Registrazione.data_contabile>=filter_dal)."
        if filter_al!=None:filtro+="filter(Registrazione.data_contabile<=filter_al)."
        registr= eval("Registrazione.query."+filtro+"filter(Registrazione.numero!=None).order_by(Registrazione.data_contabile.desc()).order_by(Registrazione.nome.desc()).all()")
        bozze= eval("Registrazione.query."+filtro+"filter(Registrazione.numero==None).order_by(Registrazione.data_contabile).order_by(Registrazione.id).all()")
        if not current_user.bozze:
            bozze=[]
        registrazioni=bozze+registr
        return render_template('generici.html', registrazioni=registrazioni, registro=registro, filtro_form=filtro_form, partners=partners)

@app.route('/registrazione/<id>')
@login_required
def registrazione(id):#mostra una registrazione (view or edit)
    registrazione=Registrazione.query.get(id)
    categoria=registrazione.registro.categoria
    if categoria=="Fattura": return redirect(url_for('fattura', id=id))
    if categoria=="Cassa": return redirect(url_for('cassa', id=id))
    if categoria=="Generico": return redirect(url_for('generico', id=id))
    if categoria=="Ricevuta": return redirect(url_for('ricevuta', id=id))
    if categoria=="IVA": return redirect(url_for('iva', id=id))

@app.route('/rimuovi_allegato/<id>', methods=['GET', 'POST'])
@login_required
def rimuovi_allegato(id):#rimuove un allegato da una registrazione
    allegato=Allegato.query.get(id)
    form = ConfermaForm()
    if form.validate_on_submit():
        id=allegato.registrazione.id
        if allegato.registrazione.validazione_backref.first() == None:
            db.session.delete(allegato)
            db.session.commit()
        return redirect(url_for('registrazione', id=id))
    testo=allegato.nome
    if testo==None:testo="None"
    return render_template('conferma.html', testo="Rimozione dell'allegato "+testo, form=form)

@app.route('/rimuovi_allegato_stampa/<id>', methods=['GET', 'POST'])
@login_required
def rimuovi_allegato_stampa(id):#rimuove un allegato da una stampa
    allegato=Allegato.query.get(id)
    form = ConfermaForm()
    if form.validate_on_submit():
        id=allegato.stampa.id
        db.session.delete(allegato)
        db.session.commit()
        return redirect(url_for('stampa', id=id))
    testo=allegato.nome
    if testo==None:testo="None"
    return render_template('conferma.html', testo="Rimozione dell'allegato "+testo, form=form)

@app.route('/rimuovi_voce/<id>', methods=['GET', 'POST'])
@login_required
def rimuovi_voce(id):#rimuove una voce da una registrazione
    voce=Voce.query.get(id)
    form = ConfermaForm()
    if form.validate_on_submit():
        if voce.registrazione.validazione_backref.first() == None:
            registrazione=voce.registrazione
            db.session.delete(voce)
            db.session.commit()
            if registrazione.registro.categoria=="Fattura":calcola_iva_ritenute(registrazione)
        return redirect(url_for('registrazione', id=registrazione.id))
    form.data_delibera.data = current_user.data
    testo=voce.descrizione
    if testo==None:testo="None"
    return render_template('conferma.html', testo="Rimozione della voce "+testo, form=form)

@app.route('/aggiungi_voce/<id>')
@login_required
def aggiungi_voce(id):#aggiunge una voce ad una registrazione
    registrazione=Registrazione.query.get(id)
    categoria=registrazione.registro.categoria
    importo=dec(0.0)
    if categoria=="Generico" or categoria=="Cassa":
        voci = Voce.query.filter(Voce.registrazione==registrazione).all()
        for v in voci:
            importo-=dec(v.importo)
    voce=Voce(registrazione=registrazione, importo=importo, quantita=1)
    db.session.add(voce)
    db.session.commit()
    if categoria=="Fattura":return redirect(url_for('voce_fattura', id=voce.id))
    if categoria=="Ricevuta":return redirect(url_for('voce_ricevuta', id=voce.id))
    if categoria=="Cassa":return redirect(url_for('voce_cassa', id=voce.id))
    if categoria=="Generico":return redirect(url_for('voce_generico', id=voce.id))
    if categoria=="IVA":return redirect(url_for('voce_iva', id=voce.id))

@app.route('/aggiungi_riconciliazione/<id>', methods=['GET', 'POST'])
@login_required
def aggiungi_riconciliazione(id):# nella registrazione di tipo cassa o generico aggiunge le voci per riconciliare con altre registrazioni
    impostazioni=Impostazioni.query.get(1)
    riconciliazione_id = request.args.get('riconciliazione_id')
    riconciliazione=Registrazione.query.get(riconciliazione_id)
    registrazione=Registrazione.query.get(id)

    #controlla se la riconciliazione inserita fa riferimento ad una fattura con ritenuta e in caso inserisce la ritenuta
    ritenuta=[]
    for v in riconciliazione.voce:
        if v.ritenuta!= None and v.ritenuta not in ritenuta: ritenuta.append(v.ritenuta)
    imponibile=[0]*len(ritenuta)
    ra=[0]*len(ritenuta)
    for v in riconciliazione.voce:
        if v.ritenuta != None: imponibile[ritenuta.index(v.ritenuta)]+=dec(v.importo*v.quantita)
    for i in range(len(ritenuta)):
        ra=dec(-imponibile[i]*ritenuta[i].aliquota/100)
        descrizione=ritenuta[i].nome+" "+riconciliazione.nome+" N. "+riconciliazione.numero_origine+" "+riconciliazione.partner.nome
        voce=Voce(registrazione=registrazione, descrizione=descrizione, conto=ritenuta[i].conto_transito_ritenuta, importo=ra)
        db.session.add(voce)
    if riconciliazione.lav_autonomo: conto=impostazioni.conto_lav_autonomo
    else: conto=riconciliazione.registro.conto
    voce=Voce(registrazione=registrazione, descrizione=riconciliazione.descrizione, conto=conto, partner=riconciliazione.partner, importo=-riconciliazione.saldo, riconciliazione=riconciliazione)
    db.session.add(voce)
    db.session.commit()
    return redirect(url_for('registrazione', id=id))

@app.route('/download_file/<id>')
@login_required
def download_file(id):#offre il file in download
    file=Allegato.query.get(id)
    #print(file.nome)
    return send_file(io.BytesIO(file.binario),as_attachment=True,attachment_filename=file.nome)#,mimetype='application/pdf')
    
@app.route('/anagrafica', methods=['GET', 'POST'])
@login_required
def anagrafica():
    form = AnagraficaForm()#mostra l'anagrafica
    partners = Partner.query.order_by(Partner.nome).with_entities(Partner.nome, Partner.id).all()
    if form.validate_on_submit():
        partners = Partner.query.filter(Partner.nome.ilike('%%'+form.search.data+'%%')).order_by(Partner.nome).all()
    return render_template('anagrafica.html', partners=partners, form=form)
# M A I N #########################################################################



# P A R T N E R #########################################################################
@app.route('/partner/<id>', methods=['GET', 'POST'])
@login_required
def partner(id):#visualizza il partner
    impostazioni=Impostazioni.query.get(1)
    partner=Partner.query.get(id)
    form = PartnerForm()
    filtro_form=FiltroForm()
    print(filtro_form.submit_filtro.data)
    if filtro_form.submit_filtro.data and filtro_form.validate():
        current_user.dal=filtro_form.dal.data
        current_user.al=filtro_form.al.data
        current_user.tipo_data=filtro_form.tipo_data.data
        current_user.stato=filtro_form.stato.data
        datalog="Modificato filtro: dal["+format_date(current_user.dal)+"] al["+format_date(current_user.al)+"] tipo["+str(current_user.tipo_data)+"] stato["+str(current_user.stato)+"] bozze["+str(current_user.bozze)+"] partner["+nome(current_user.partner)+"]"
        log = Log(datalog=datalog, user=current_user.username, timestamp = func.now())
        db.session.add(log)
        db.session.commit()
    if filtro_form.is_submitted() and not filtro_form.validate():pass
    else:
        filtro_form.dal.data=current_user.dal
        filtro_form.al.data=current_user.al
        filtro_form.tipo_data.data=current_user.tipo_data
        filtro_form.stato.data=current_user.stato
    filtro="filter(Registrazione.partner==partner)."
    filter_dal = current_user.dal
    filter_al = current_user.al
    if current_user.stato=="insolute":filtro+="filter(Registrazione.saldo!=0)."
    if filter_dal!=None:filtro+="filter(Registrazione."+current_user.tipo_data+">=filter_dal)."
    if filter_al!=None:filtro+="filter(Registrazione."+current_user.tipo_data+"<=filter_al)."
    registrazioni,totale,saldo=[],0,0
    for registro in Registro.query.filter(or_(Registro.categoria=="Fattura", Registro.categoria=="Ricevuta")).order_by(Registro.posizione).all():
        filtro+="filter(Registrazione.registro==registro)."
        registrazioni += eval("Registrazione.query."+filtro+"filter(Registrazione.numero!=None).order_by(Registrazione.nome.desc()).order_by(Registrazione.id).all()")
        totale += eval("db.session.query(func.sum(Registrazione.importo))."+filtro+"filter(Registrazione.numero!=None).scalar()") or 0
        saldo += eval("db.session.query(func.sum(Registrazione.saldo))."+filtro+"filter(Registrazione.numero!=None).scalar()") or 0
    se=[]
    return render_template('partner.html', partner=partner, form=form, filtro_form=filtro_form, registrazioni=registrazioni, totale=totale, saldo=saldo)

@app.route('/aggiungi_partner')
@login_required
def aggiungi_partner():#aggiunge un partner
    partner=Partner()
    db.session.add(partner)
    db.session.commit()
    partner.nome="Nuovo "+str(partner.id)
    datalog="Aggiunto il patner id "+str(partner.id)
    log = Log(datalog=datalog, user=current_user.username, timestamp = func.now())
    db.session.add(log)
    db.session.commit()
    return redirect(url_for('partner', id=partner.id))

@app.route('/rimuovi_partner/<id>', methods=['GET', 'POST'])
@login_required
def rimuovi_partner(id):#rimuove il partenr
    partner=Partner.query.get(id)
    form = ConfermaForm()
    if form.validate_on_submit():
        nome=partner.nome
        db.session.delete(partner)
        db.session.commit()
        flash("Il partner "+nome+" è stato rimosso !")
        return redirect(url_for('anagrafica'))
    return render_template('conferma.html', testo="Rimozione del partner "+partner.nome, form=form)

@app.route('/edit_partner/<id>', methods=['GET', 'POST'])
@login_required
def edit_partner(id):#modifica il partner
    partner=Partner.query.get(id)
    partners = Partner.query.all()
    form = PartnerForm()
    if form.submit.data and form.validate():
    #if form.validate_on_submit():
        partner.nome = form.nome.data
        partner.cf = form.cf.data
        partner.iva = form.iva.data
        partner.indirizzo = form.indirizzo.data
        partner.cap = form.cap.data
        partner.citta = form.citta.data
        partner.provincia = form.provincia.data
        partner.telefono = form.telefono.data
        partner.cellulare = form.cellulare.data
        partner.fax = form.fax.data
        partner.email = form.email.data
        partner.pec = form.pec.data
        partner.codice_destinatario = form.codice_destinatario.data
        partner.amministratore=Partner.query.filter_by(nome=form.amministratore.data).first()
        partner.letturista=Partner.query.filter_by(nome=form.letturista.data).first()
        partner.regime_fiscale = form.regime_fiscale.data
        partner.rea_ufficio = form.rea_ufficio.data
        partner.rea_codice = form.rea_codice.data
        partner.rea_stato_liquidatione = form.rea_stato_liquidatione.data
        partner.pa = form.pa.data
        partner.lav_autonomo = form.lav_autonomo.data
        partner.iban = form.iban.data
        db.session.commit()
        flash('I dati sono stati salvati !')
        return redirect(url_for('partner', id=partner.id))
    if form.is_submitted() and not form.validate():pass
    else:
        form.nome.data=partner.nome
        form.cf.data=partner.cf
        form.iva.data=partner.iva
        form.indirizzo.data = partner.indirizzo
        form.cap.data = partner.cap
        form.citta.data = partner.citta
        form.provincia.data = partner.provincia
        form.telefono.data = partner.telefono
        form.cellulare.data = partner.cellulare
        form.fax.data = partner.fax
        form.email.data = partner.email
        form.pec.data = partner.pec
        form.codice_destinatario.data = partner.codice_destinatario
        if partner.amministratore != None: form.amministratore.data=partner.amministratore.nome
        if partner.letturista != None: form.letturista.data=partner.letturista.nome
        form.regime_fiscale.data = partner.regime_fiscale
        form.rea_ufficio.data = partner.rea_ufficio
        form.rea_codice.data = partner.rea_codice
        form.rea_stato_liquidatione.data = partner.rea_stato_liquidatione
        form.pa.data = partner.pa
        form.lav_autonomo.data = partner.lav_autonomo
        form.iban.data = partner.iban
    #domicilio=partner.domicilio
    return render_template('edit_partner.html', form=form, partner=partner, partners=partners)
# P A R T N E R #########################################################################



# S T A M P A #########################################################################
@app.route('/registri_stampe')
@login_required
def registri_stampe():
    registri = Registro_stampa.query.order_by(Registro_stampa.posizione).all()
    return render_template('registri_stampe.html', registri=registri)

@app.route('/aggiungi_stampa/<id>')
@login_required
def aggiungi_stampa(id):
    registro=Registro_stampa.query.get(id)
    stampa=Stampa(registro_stampa=registro)
    stampa.data_decorrenza=current_user.data_decorrenza_stampa
    stampa.data_scadenza=current_user.data_scadenza_stampa
    stampa.anno_stampa=current_user.anno_stampa
    stampa.vp7,stampa.vp8,stampa.vp9,stampa.vp10,stampa.vp11=0,0,0,0,0
    db.session.add(stampa)
    db.session.commit()
    #return redirect(url_for('stampe', id=id))
    return redirect(url_for('stampa', id=stampa.id))

@app.route('/rimuovi_stampa/<id>', methods=['GET', 'POST'])
@login_required
def rimuovi_stampa(id):
    stampa=Stampa.query.get(id)
    form = ConfermaForm()
    if form.validate_on_submit():
        id=stampa.registro_stampa.id
        db.session.delete(stampa)
        db.session.commit()
        return redirect(url_for('stampe', id=id))
    return render_template('conferma.html', testo="Rimozione della stampa", form=form)

@app.route('/aggiungi_filtro_conto/<id>')
@login_required
def aggiungi_filtro_conto(id):
    stampa=Stampa.query.get(id)
    filtro_conto=Filtro_conto(stampa=stampa)
    db.session.add(filtro_conto)
    db.session.commit()
    return redirect(url_for('filtro_conto', id=filtro_conto.id))

@app.route('/filtro_conto/<id>', methods=['GET', 'POST'])
@login_required
def filtro_conto(id):
    conti = Conto.query.all()
    form = FiltroContoForm()
    filtro = Filtro_conto.query.get(id)
    if form.validate_on_submit():
        filtro.conto=Conto.query.filter_by(nome=form.conto.data).first()
        db.session.commit()
        flash('I dati sono stati salvati !')
        return redirect(url_for('stampa', id=filtro.stampa.id))
    if form.is_submitted() and not form.validate():pass
    else:
        if filtro.conto != None: form.conto.data=filtro.conto.nome
    return render_template('filtro_conto.html', form=form, conti=conti)

@app.route('/rimuovi_filtro_conto/<id>')
@login_required
def rimuovi_filtro_conto(id):
    filtro=Filtro_conto.query.get(id)
    id=filtro.stampa.id
    db.session.delete(filtro)
    db.session.commit()
    return redirect(url_for('stampa', id=id))

@app.route('/stampe/<id>')
@login_required
def stampe(id):
    registro=Registro_stampa.query.get(id)
    categoria=registro.categoria
    if registro.categoria=="Libro Mastro" or registro.categoria=="Partitario":stampe=Stampa.query.filter_by(registro_stampa=registro).order_by(Stampa.nome).all()
    else:stampe=Stampa.query.filter_by(registro_stampa=registro).order_by(Stampa.data_decorrenza).all()
    if registro.categoria=="Bilancio Contabile" or registro.categoria=="Libro Mastro" or registro.categoria=="Partitario":show=False
    else:show=True
    return render_template('stampe.html', stampe=stampe, registro=registro, show=show)

@app.route('/stampa/<id>')
@login_required
def stampa(id):
    stampa=Stampa.query.get(id)
    categoria=stampa.registro_stampa.categoria
    if categoria=="Registro IVA": return redirect(url_for('stampa_registro_iva', id=id))
    if categoria=="Liquidazione IVA": return redirect(url_for('stampa_liquidazione_iva', id=id))
    if categoria=="Partitario": return redirect(url_for('stampa_partitario', id=id))
    if categoria=="Libro Giornale": return redirect(url_for('stampa_libro_giornale', id=id))
    if categoria=="Libro Mastro": return redirect(url_for('stampa_libro_mastro', id=id))
    if categoria=="Bilancio Contabile": return redirect(url_for('stampa_bilancio_contabile', id=id))

@app.route('/stampa_liquidazione_iva/<id>', methods=['GET', 'POST'])
@login_required
def stampa_liquidazione_iva(id):
    stampa=Stampa.query.get(id)
    allegati=stampa.allegato.order_by(Allegato.id).all()
    form = StampaLiquidazioneIvaForm()
    if form.submit.data and form.validate():
        stampa.anno_stampa=form.anno_stampa.data
        stampa.precedente_pagina_stampa=form.precedente_pagina_stampa.data
        registrazione=Registrazione.query.filter_by(nome=form.registrazione.data).first()
        for f in Filtro_registrazione.query.filter(Filtro_registrazione.stampa==stampa):
            db.session.delete(f)
        filtro=Filtro_registrazione(stampa=stampa, registrazione=registrazione)
        db.session.add(filtro)
        stampa.data_decorrenza=registrazione.data_decorrenza
        stampa.data_scadenza=registrazione.data_scadenza
        stampa.nome=registrazione.descrizione
        stampa.VP7=Decimal(form.VP7.data).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        stampa.VP8=Decimal(form.VP8.data).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        stampa.VP9=Decimal(form.VP9.data).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        stampa.VP10=Decimal(form.VP10.data).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        stampa.VP11=Decimal(form.VP11.data).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        db.session.commit()
        return redirect(url_for('genera_stampa_liquidazione_iva', id=id))
        #flash('I dati sono stati salvati !')
    if form.is_submitted() and not form.validate():pass
    else:
        filtro=stampa.filtro_registrazione.first()
        if filtro!=None:form.registrazione.data=filtro.registrazione.nome
        form.anno_stampa.data=stampa.anno_stampa
        form.precedente_pagina_stampa.data=stampa.precedente_pagina_stampa
        form.VP7.data=stampa.VP7
        form.VP8.data=stampa.VP8
        form.VP9.data=stampa.VP9
        form.VP10.data=stampa.VP10
        form.VP11.data=stampa.VP11
    registro_liq_iva=stampa.registro_stampa.filtro_registro.first().registro
    #registrazioni=Registrazione.query.filter(Registrazione.numero!=None).filter(Registrazione.registro==registro_liq_iva).all()
    registrazioni=Registrazione.query.outerjoin(Filtro_registrazione).filter(Registrazione.registro_id==15).filter(Filtro_registrazione.stampa_id==None).all()
    print(allegati)
    return render_template('stampa_liquidazione_iva.html', form=form, stampa=stampa, allegati=allegati, registrazioni=registrazioni)

@app.route('/stampa_registro_iva/<id>', methods=['GET', 'POST'])
@login_required
def stampa_registro_iva(id):
    stampa=Stampa.query.get(id)
    allegati=stampa.allegato.order_by(Allegato.id).all()
    form = StampaForm()
    if form.submit.data and form.validate():
        stampa.nome=form.nome.data
        stampa.data_decorrenza=form.data_decorrenza.data
        stampa.data_scadenza=form.data_scadenza.data
        stampa.anno_stampa=form.anno_stampa.data
        stampa.precedente_pagina_stampa=form.precedente_pagina_stampa.data
        current_user.data_decorrenza_stampa=stampa.data_decorrenza
        current_user.data_scadenza_stampa=stampa.data_scadenza
        current_user.anno_stampa=stampa.anno_stampa
        db.session.commit()
        return redirect(url_for('genera_stampa_registro_iva', id=id))
        #flash('I dati sono stati salvati !')
    if form.is_submitted() and not form.validate():pass
    else:
        form.nome.data=stampa.nome
        form.data_decorrenza.data=stampa.data_decorrenza
        form.data_scadenza.data=stampa.data_scadenza
        form.anno_stampa.data=stampa.anno_stampa
        form.precedente_pagina_stampa.data=stampa.precedente_pagina_stampa
    return render_template('stampa_registro_iva.html', form=form, stampa=stampa, allegati=allegati)

@app.route('/stampa_partitario/<id>', methods=['GET', 'POST'])
@login_required
def stampa_partitario(id):
    stampa=Stampa.query.get(id)
    allegati=stampa.allegato.order_by(Allegato.id).all()
    filtro_conto=stampa.filtro_conto.all()
    form = StampaForm()
    partners = Partner.query.order_by(Partner.nome).with_entities(Partner.nome).all()
    if form.submit.data and form.validate():
        stampa.nome=form.nome.data
        stampa.data_decorrenza=form.data_decorrenza.data
        stampa.data_scadenza=form.data_scadenza.data
        stampa.partner=Partner.query.filter_by(nome=form.partner.data).first()
        current_user.data_decorrenza_stampa=stampa.data_decorrenza
        current_user.data_scadenza_stampa=stampa.data_scadenza
        db.session.commit()
        return redirect(url_for('genera_stampa_partitario', id=id))
        #flash('I dati sono stati salvati !')
    if form.is_submitted() and not form.validate():pass
    else:
        form.nome.data=stampa.nome
        form.data_decorrenza.data=stampa.data_decorrenza
        form.data_scadenza.data=stampa.data_scadenza
        if stampa.partner != None: form.partner.data=stampa.partner.nome
    #conti=[]
    return render_template('stampa_partitario.html', form=form, stampa=stampa, allegati=allegati, partners=partners)

@app.route('/stampa_libro_giornale/<id>', methods=['GET', 'POST'])
@login_required
def stampa_libro_giornale(id):
    stampa=Stampa.query.get(id)
    allegati=stampa.allegato.order_by(Allegato.id).all()
    form = StampaForm()
    if form.submit.data and form.validate():
        stampa.nome=form.nome.data
        stampa.data_decorrenza=form.data_decorrenza.data
        stampa.data_scadenza=form.data_scadenza.data
        stampa.anno_stampa=form.anno_stampa.data
        stampa.precedente_pagina_stampa=form.precedente_pagina_stampa.data
        stampa.precedente_riga_stampa=form.precedente_riga_stampa.data
        current_user.data_decorrenza_stampa=stampa.data_decorrenza
        current_user.data_scadenza_stampa=stampa.data_scadenza
        current_user.anno_stampa=stampa.anno_stampa
        db.session.commit()
        return redirect(url_for('genera_stampa_libro_giornale', id=id))
        #flash('I dati sono stati salvati !')
    if form.is_submitted() and not form.validate():pass
    else:
        form.nome.data=stampa.nome
        form.data_decorrenza.data=stampa.data_decorrenza
        form.data_scadenza.data=stampa.data_scadenza
        form.anno_stampa.data=stampa.anno_stampa
        form.precedente_pagina_stampa.data=stampa.precedente_pagina_stampa
        form.precedente_riga_stampa.data=stampa.precedente_riga_stampa
    return render_template('stampa_libro_giornale.html', form=form, stampa=stampa, allegati=allegati)

@app.route('/stampa_libro_mastro/<id>', methods=['GET', 'POST'])
@login_required
def stampa_libro_mastro(id):
    stampa=Stampa.query.get(id)
    allegati=stampa.allegato.order_by(Allegato.id).all()
    filtro_conto=stampa.filtro_conto.all()
    form = StampaForm()
    partners = Partner.query.order_by(Partner.nome).with_entities(Partner.nome).all()
    conti = Conto.query.with_entities(Conto.nome).all()
    if form.submit.data and form.validate():
        stampa.nome=form.nome.data
        stampa.data_decorrenza=form.data_decorrenza.data
        stampa.data_scadenza=form.data_scadenza.data
        stampa.partner=Partner.query.filter_by(nome=form.partner.data).first()
        current_user.data_decorrenza_stampa=stampa.data_decorrenza
        current_user.data_scadenza_stampa=stampa.data_scadenza
        current_user.anno_stampa=stampa.anno_stampa
        db.session.commit()
        filtro_conto=stampa.filtro_conto.all()
        return redirect(url_for('genera_stampa_libro_mastro', id=id))
        #flash('I dati sono stati salvati !')
    if form.is_submitted() and not form.validate():pass
    else:
        form.nome.data=stampa.nome
        form.data_decorrenza.data=stampa.data_decorrenza
        form.data_scadenza.data=stampa.data_scadenza
        if stampa.partner != None: form.partner.data=stampa.partner.nome
    #conti=[]
    return render_template('stampa_libro_mastro.html', form=form, stampa=stampa, allegati=allegati, partners=partners, conti=conti, filtro_conto=filtro_conto)

@app.route('/stampa_bilancio_contabile/<id>', methods=['GET', 'POST'])
@login_required
def stampa_bilancio_contabile(id):
    stampa=Stampa.query.get(id)
    allegati=stampa.allegato.order_by(Allegato.id).all()
    filtro_conto=stampa.filtro_conto.all()
    form = StampaForm()
    if form.submit.data and form.validate():
        stampa.nome=form.nome.data
        stampa.data_decorrenza=form.data_decorrenza.data
        stampa.data_scadenza=form.data_scadenza.data
        current_user.data_decorrenza_stampa=stampa.data_decorrenza
        current_user.data_scadenza_stampa=stampa.data_scadenza
        db.session.commit()
        return redirect(url_for('genera_stampa_bilancio_contabile', id=id))
        #flash('I dati sono stati salvati !')
    if form.is_submitted() and not form.validate():pass
    else:
        form.nome.data=stampa.nome
        form.data_decorrenza.data=stampa.data_decorrenza
        form.data_scadenza.data=stampa.data_scadenza
    #conti=[]
    return render_template('stampa_bilancio_contabile.html', form=form, stampa=stampa, allegati=allegati)

@app.route('/genera_stampa_liquidazione_iva/<id>')
@login_required
def genera_stampa_liquidazione_iva(id):
    return render_template('wait.html', id=id, link="genera_stampa_liquidazione_iva_")

@app.route('/genera_stampa_liquidazione_iva_/<id>')
@login_required
def genera_stampa_liquidazione_iva_(id):
    stampa=Stampa.query.get(id)
    filename=os.path.join(here, 'stampa.pdf')
    for a in stampa.allegato:
        if a.nome=="LIQUIDAZIONE IVA.pdf":
            db.session.delete(a)
    pagina=Stampa_liquidazione_iva(stampa)
    with open(filename, 'rb') as bites:
        data=io.BytesIO(bites.read())
    allegato=Allegato(stampa=stampa, nome="LIQUIDAZIONE IVA.pdf", binario=data.read(), pagina_stampa=0)
    db.session.add(allegato)
    db.session.commit()
    flash('La liquidazione iva è stata generata !')
    return redirect(url_for('stampa', id=id))

@app.route('/genera_stampa_registro_iva/<id>')
@login_required
def genera_stampa_registro_iva(id):
    return render_template('wait.html', id=id, link="genera_stampa_registro_iva_")

@app.route('/genera_stampa_registro_iva_/<id>')
@login_required
def genera_stampa_registro_iva_(id):
    stampa=Stampa.query.get(id)
    filename=os.path.join(here, 'stampa.pdf')
    for a in stampa.allegato:
        if a.nome=="REGISTRO IVA.pdf":
            db.session.delete(a)
    if Stampa_registro_iva(stampa):
        with open(filename, 'rb') as bites:
            data=io.BytesIO(bites.read())
        allegato=Allegato(stampa=stampa, nome="REGISTRO IVA.pdf", binario=data.read(), pagina_stampa=0)
        db.session.add(allegato)
        flash('Il registro iva è stato generato !')
    else:
        flash('Non ci sono registrazioni nel periodo selezionato !')
    db.session.commit()
    return redirect(url_for('stampa', id=id))

@app.route('/genera_stampa_partitario/<id>')
@login_required
def genera_stampa_partitario(id):
    return render_template('wait.html', id=id, link="genera_stampa_partitario_")

@app.route('/genera_stampa_partitario_/<id>')
@login_required
def genera_stampa_partitario_(id):
    stampa=Stampa.query.get(id)
    filename=os.path.join(here, 'stampa.pdf')
    for a in stampa.allegato:
        if a.nome=="PARTITARIO.pdf" or a.nome=="PARTITARIO INSOLUTI.pdf":
            db.session.delete(a)
    if stampa.partner!=None:
        pagina=Stampa_partitario_singolo(stampa)
        with open(filename, 'rb') as bites:
            data=io.BytesIO(bites.read())
        allegato=Allegato(stampa=stampa, nome="PARTITARIO.pdf", binario=data.read(), pagina_stampa=0)
        db.session.add(allegato)
    else:
        Stampa_partitario(stampa)
        with open(filename, 'rb') as bites:
            data=io.BytesIO(bites.read())
        allegato=Allegato(stampa=stampa, nome="PARTITARIO.pdf", binario=data.read(), pagina_stampa=0)
        db.session.add(allegato)
        Stampa_partitario_insoluti(stampa)
        with open(filename, 'rb') as bites:
            data=io.BytesIO(bites.read())
        allegato=Allegato(stampa=stampa, nome="PARTITARIO INSOLUTI.pdf", binario=data.read(), pagina_stampa=0)
        db.session.add(allegato)
    db.session.commit()
    flash('Il partitario è stato generato !')
    return redirect(url_for('stampa', id=id))

@app.route('/genera_stampa_libro_mastro/<id>')
@login_required
def genera_stampa_libro_mastro(id):
    return render_template('wait.html', id=id, link="genera_stampa_libro_mastro_")

@app.route('/genera_stampa_libro_mastro_/<id>')
@login_required
def genera_stampa_libro_mastro_(id):
    stampa=Stampa.query.get(id)
    dal=stampa.data_decorrenza
    al=stampa.data_scadenza
    fconti=stampa.filtro_conto.all()
    conti=[]
    for f in fconti:conti.append(f.conto)
    partner=stampa.partner
    filename=os.path.join(here, 'stampa.pdf')
    for a in stampa.allegato:
        if a.nome=="LIBRO MASTRO.pdf" or a.nome=="LIBRO MASTRO LANDSCAPE.pdf":
            db.session.delete(a)
    pagina=Stampa_libro_mastro(partner,dal,al,conti,filename)
    with open(filename, 'rb') as bites:
        data=io.BytesIO(bites.read())
    allegato=Allegato(stampa=stampa, nome="LIBRO MASTRO.pdf", binario=data.read(), pagina_stampa=0)
    db.session.add(allegato)
    db.session.commit()
    flash('Il libro mastro è stato generato !')
    return redirect(url_for('stampa', id=id))

@app.route('/genera_stampa_libro_giornale/<id>')
@login_required
def genera_stampa_libro_giornale(id):
    return render_template('wait.html', id=id, link="genera_stampa_libro_giornale_")

@app.route('/genera_stampa_libro_giornale_/<id>')
@login_required
def genera_stampa_libro_giornale_(id):
    stampa=Stampa.query.get(id)
    filename=os.path.join(here, 'stampa.pdf')
    for a in stampa.allegato:
        if a.nome=="LIBRO GIORNALE.pdf" or a.nome=="LIBRO GIORNALE LANDSCAPE.pdf" or a.nome=="REGISTRO.pdf":
            db.session.delete(a)
    if stampa.registro_stampa.filtro_registro.all() == []:
        pagina=Stampa_libro_giornale(stampa)
        with open(filename, 'rb') as bites:
            data=io.BytesIO(bites.read())
        allegato=Allegato(stampa=stampa, nome="LIBRO GIORNALE.pdf", binario=data.read(), pagina_stampa=0)
        db.session.add(allegato)
#        pagina=Stampa_libro_giornale_landscape(stampa)
#        with open(filename, 'rb') as bites:
#            data=io.BytesIO(bites.read())
#        allegato=Allegato(stampa=stampa, nome="LIBRO GIORNALE LANDSCAPE.pdf", binario=data.read(), pagina_stampa=0)
#        db.session.add(allegato)
    else:
        fregistri=stampa.registro_stampa.filtro_registro.all()
        registri=[]
        for f in fregistri:registri.append(f.registro)
        dal=stampa.data_decorrenza
        al=stampa.data_scadenza
        page=stampa.precedente_pagina_stampa+1
        year=stampa.anno_stampa
        pagina=Stampa_registri(partner,dal,al,registri,filename,page,year)
        with open(filename, 'rb') as bites:
            data=io.BytesIO(bites.read())
        allegato=Allegato(stampa=stampa, nome="REGISTRO.pdf", binario=data.read(), pagina_stampa=0)
        db.session.add(allegato)
#        pagina=Stampa_registri_landscape(stampa)
#        with open(filename, 'rb') as bites:
#            data=io.BytesIO(bites.read())
#        allegato=Allegato(stampa=stampa, nome="LIBRO GIORNALE LANDSCAPE.pdf", binario=data.read(), pagina_stampa=0)
#        db.session.add(allegato)
    db.session.commit()
    flash('Il libro giornale è stato generato !')
    return redirect(url_for('stampa', id=id))

@app.route('/genera_stampa_bilancio_contabile/<id>')
@login_required
def genera_stampa_bilancio_contabile(id):
    return render_template('wait.html', id=id, link="genera_stampa_bilancio_contabile_")

@app.route('/genera_stampa_bilancio_contabile_/<id>')
@login_required
def genera_stampa_bilancio_contabile_(id):
    stampa=Stampa.query.get(id)
    filename=os.path.join(here, 'stampa.pdf')
    for a in stampa.allegato:
        if a.nome=="BILANCIO CONTABILE.pdf":
            db.session.delete(a)
    pagina=Stampa_bilancio_contabile(stampa)
    with open(filename, 'rb') as bites:
        data=io.BytesIO(bites.read())
    allegato=Allegato(stampa=stampa, nome="BILANCIO CONTABILE.pdf", binario=data.read(), pagina_stampa=0)
    db.session.add(allegato)
    db.session.commit()
    flash('Il bilancio contabile è stato generato !')
    return redirect(url_for('stampa', id=id))

def Stampa_liquidazione_iva(stampa):
    #registro=stampa.registro_stampa.registro
    registro=stampa.registro_stampa.filtro_registro.first().registro
    registrazione=stampa.filtro_registrazione.first().registrazione
    registri_fatture, conto_iva, imposta, imponibile, iva, IVA=calcola_IVA(registrazione)
    VP2,VP3,VP4,VP5=calcola_LIPE(registrazione)
    tab=[[40,"l"],[170,"l"],[320,"r"],[390,"r"],[400,"l"],[150,"r"]]
    des=["Descrizione","Tipo","Imponibile","Imposta"]
    filename=os.path.join(here, 'stampa.pdf')
    header='LIBRO IVA VENDITE - LIQUIDAZIONE IVA - '+stampa.nome
    azienda=Impostazioni.query.get(1).azienda
    footer=azienda.nome+" - "+azienda.indirizzo+" - "+azienda.cap+" "+azienda.citta+" - P.IVA "+azienda.iva+" - CF "+azienda.cf
    #header+=" stampato il "+datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    can=document2(filename, pagesize=A4, page=stampa.precedente_pagina_stampa+1, year=stampa.anno_stampa, tab=tab, des=des, header=header, footer=footer)
    for c in range(len(conto_iva)):
        for j in range(len(imposta)):
            if imponibile[j][c]!=0:
                if conto_iva[c].sottomastro.mastro.tipo=="Attività":segno=-1
                else:segno=1
                can.newline()
                can.write(0,imposta[j].nome)
                can.write(1,conto_iva[c].descrizione)
                can.write(2,valuta(segno*imponibile[j][c]))
                can.write(3,valuta(segno*iva[j][c]))
                if imposta[j].indetraibile: can.write(4,"Indetraibile")
                if imposta[j].esigibilita=="S": can.write(4,"Split payment")
    totale=0
    can.newline()
    for c in range(len(conto_iva)):
        if conto_iva[c].sottomastro.mastro.tipo=="Attività":segno=-1
        else:segno=1
        can.newline()
        can.write(0,"TOTALE "+conto_iva[c].descrizione)
        can.write(3,valuta(IVA[c]*segno))
        totale+=IVA[c]
    can.newline()
    can.writebold(0,"TOTALE IVA DOVUTA")
    can.writebold(3,valuta(totale))
    can.newline()
    voci=registrazione.voce.order_by(Voce.id).all()
    for v in voci:
        if v.conto not in conto_iva:
            can.newline()
            can.write(0,v.descrizione)
            can.write(3,valuta(v.importo))
            totale+=v.importo
    can.newline()
    can.newline()
    can.writebold(0,"TOTALE LIQUIDAZIONE IVA")
    can.writebold(3,valuta(totale))
    can.newline()
    can.newline()
    can.newline()
    can.writebold(0,"COMUNICAZIONE LIQUIDAZIONI PERIODICHE IVA")
    can.writebold(2,"DEBITI")
    can.writebold(3,"CREDITI")
    can.newline()
    can.newline()
    can.write(0,"VP2 Totale operazioni attive")
    can.write(2,valuta(VP2))
    can.newline()
    can.write(0,"VP3 Totale operazioni passive")
    can.write(3,valuta(VP3))
    can.newline()
    can.write(0,"VP4 IVA esigibile")
    can.write(2,valuta(VP4))
    can.newline()
    can.write(0,"VP5 IVA detratta")
    can.write(3,valuta(VP5))
    can.newline()
    can.write(0,"VP6 IVA dovuta / IVA a debito")
    if VP4-VP5>=0:
        can.write(2,valuta(VP4-VP5))
    else:
        can.write(3,valuta(VP5-VP4))
    can.newline()
    can.write(0,"VP7 Debito per. prec. non sup. 25,82 euro")
    can.write(2,valuta(stampa.VP7))
    can.newline()
    can.write(0,"VP8 Credito periodo precedente")
    can.write(3,valuta(stampa.VP8))
    can.newline()
    can.write(0,"VP9 Credito anno precedente")
    can.write(3,valuta(stampa.VP9))
    can.newline()
    can.write(0,"VP10 Versamenti auto UE")
    can.write(3,valuta(stampa.VP10))
    can.newline()
    can.write(0,"VP11 Crediti d’imposta")
    can.write(3,valuta(stampa.VP11))
    can.newline()
    can.write(0,"VP14 IVA da versare / IVA a credito")
    saldo=VP5-VP4-stampa.VP7+stampa.VP8+stampa.VP9+stampa.VP10+stampa.VP11#-VP12+VP13
    if saldo>=0:
        can.write(3,valuta(saldo))
    else:
        can.write(2,valuta(-saldo))
    stampa.ultima_pagina_stampa=can.page
    can.save()

def Stampa_registro_iva(stampa):
    tab=[[40,"l"],[82,"l"],[124,"l"],[185,"l"],[380,"r"],[430,"r"],[475,"r"],[480,"l"]]
    des=["Data reg","Data doc","Numero","Partner","Totale","Imponibile","Imposta","Descrizione"]
    filename=os.path.join(here, 'stampa.pdf')
    #registro=stampa.registro_stampa.registro
    registri=stampa.registro_stampa.filtro_registro.all()
    #header='REGISTRO IVA '+registro.nome+" - "+stampa.nome+" - "+registro.conto_iva.descrizione
    header=stampa.registro_stampa.nome+" - "+stampa.nome
    azienda=Impostazioni.query.get(1).azienda
    footer=azienda.nome+" - "+azienda.indirizzo+" - "+azienda.cap+" "+azienda.citta+" - P.IVA "+azienda.iva+" - CF "+azienda.cf
    #header+=" stampato il "+datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    can=document2(filename, pagesize=A4, page=stampa.precedente_pagina_stampa+1, year=stampa.anno_stampa, tab=tab, des=des, header=header, footer=footer)
    imposta=Imposta.query.order_by(Imposta.posizione).all()
    IMPONIBILE=[0]*len(imposta)
    IVA=[0]*len(imposta)

    filtro="filter(or_("
    for i in range(len(registri)):
        filtro+="Registrazione.registro==registri["+str(i)+"].registro,"
    filtro=filtro[:-1]
    filtro+="))."


    #filtro="filter_by(registro=registro)."
    if stampa.data_decorrenza!=None:filtro+="filter(Registrazione.data_contabile>=stampa.data_decorrenza)."
    if stampa.data_scadenza!=None:filtro+="filter(Registrazione.data_contabile<=stampa.data_scadenza)."

    registrazioni=eval("Registrazione.query.filter(Registrazione.numero!=None)."+filtro+"order_by(Registrazione.data_contabile).order_by(Registrazione.nome).all()")
    #registrazioni=Registrazione.query.filter_by(registro=registro).filter(Registrazione.numero!=None).filter(and_(Registrazione.data_contabile >= stampa.data_decorrenza, Registrazione.data_contabile <= stampa.data_scadenza)).order_by(Registrazione.numero).all()
    if len(registrazioni)>0:
        for r in registrazioni:
            segno2=1
            if registri[0].registro.conto.sottomastro.mastro.tipo=="Passività": segno2=-1

            voci=r.voce_iva.order_by(Voce_iva.id).all()
            tot_imponibile=0
            tot_imposta=0
            imponibile=[0]*len(imposta)
            iva=[0]*len(imposta)
            for v in voci:
                imponibile[imposta.index(v.imposta)]+=v.imponibile*r.registro.segno
                iva[imposta.index(v.imposta)]+=v.iva*r.registro.segno
            for j in range(len(imposta)):
                tot_imponibile+=imponibile[j]
                tot_imposta+=iva[j]
            totale=tot_imponibile+tot_imposta

            first=True
            for j in range(len(imposta)):
                if imponibile[j]!=0:
                    can.newline()
                    if first:
                        first=False
                        can.write(0,r.data_contabile.strftime("%d/%m/%y"))
                        can.write(1,r.data_decorrenza.strftime("%d/%m/%y"))
                        can.write(2,r.nome)
                        #can.write(3,r.partner.nome[:28])
                        if r.validazione == None:can.write(3,r.partner.nome[:28])#per stampa partner fatture RC
                        else:can.write(3,r.validazione.registrazione.partner.nome[:28])
                        can.write(4,valuta(totale*segno2))
                    can.write(5,valuta(imponibile[j]*segno2))
                    can.write(6,valuta(iva[j]*segno2))
                    can.write(7,imposta[j].nome)
            for j in range(len(imponibile)):
                IMPONIBILE[j]+=imponibile[j]
                IVA[j]+=iva[j]
        can.newline()
        can.newline()
        can.writebold(4,"TOTALI")
        can.newline()
        tot_imponibile,tot_imposta=0,0
        for j in range(len(imponibile)):
            if IMPONIBILE[j]!=0:# print(IMPONIBILE[j],IVA[j])
                can.newline()
                can.writebold(4,valuta(IMPONIBILE[j]*segno2))
                can.writebold(6,valuta(IVA[j]*segno2))
                can.writebold(7,imposta[j].nome[:20])
                tot_imponibile+=IMPONIBILE[j]*segno2
                tot_imposta+=IVA[j]*segno2
        can.newline()
        can.newline()
        can.writebold(4,valuta(tot_imponibile))
        can.writebold(6,valuta(tot_imposta))
        stampa.ultima_pagina_stampa=can.page
        can.save()
        return True
    else:
        return False

def Stampa_libro_giornale(stampa):
    tab=[[40,"l"],[75,"l"],[120,"l"],[260,"l"],[490,"r"],[550,"r"],[460,"r"],[500,"r"]]
    des=["Riga","Data","Registro/Conto","Partner/Descrizione","N.Doc/Dare","Data/Avere","",""]
    filename=os.path.join(here, 'stampa.pdf')
    header='LIBRO GIORNALE'
    azienda=Impostazioni.query.get(1).azienda
    footer=azienda.nome+" - "+azienda.indirizzo+" - "+azienda.cap+" "+azienda.citta+" - P.IVA "+azienda.iva+" - CF "+azienda.cf
    #header+=" stampato il "+datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    x=False
    can=document2(filename, pagesize=A4, page=stampa.precedente_pagina_stampa+1, year=stampa.anno_stampa, tab=tab, des=des, header=header, footer=footer)
    riga=stampa.precedente_riga_stampa+1
    for day in daterange(stampa.data_decorrenza,stampa.data_scadenza):
        tdare,tavere=0,0
        registrazioni=Registrazione.query.join(Registro).filter(Registrazione.numero!=None).filter(Registrazione.data_contabile == day).order_by(Registrazione.numero).all()
        if len(registrazioni)>0:
            if x:can.newline()
            x=True
        for r in registrazioni:
            can.newline()
            n_origine,n_partner="",""
            if r.numero_origine!=None:n_origine=r.numero_origine
            if r.partner!=None:n_partner=r.partner.nome
            can.writebold(4,n_origine)
            can.writebold(3,n_partner[:47-len(n_origine)])
            can.writebold(0,r.nome)
            can.writebold(2,r.registro.nome)
            data_decorrenza=r.data_decorrenza
            if data_decorrenza!=None:can.writebold(5,data_decorrenza.strftime("%d/%m/%y"))
            for m in r.movimento:
                can.newline()
                can.write(0,str(riga).zfill(6))
                riga+=1
                can.write(1,m.data_contabile.strftime("%d/%m/%y"))
                can.write(2,m.conto.nome[:28])
                can.write(3,str(m.descrizione)[:36])
                dare,avere=0,0
                if m.importo>=0:dare=m.importo
                else:avere=-m.importo
                tdare+=dare
                tavere+=avere
                can.write(4,valuta(dare))
                can.write(5,valuta(avere))
        if len(registrazioni)>0:
            can.newline()
            can.writebold(3,"TOTALE DEL GIORNO "+day.strftime("%d/%m/%Y"))
            can.writebold(4,valuta(tdare))
            can.writebold(5,valuta(tavere))
            #can.newline()
    can.save()
    stampa.ultima_pagina_stampa=can.page
    stampa.ultima_riga_stampa=riga-1
    return can.page

def Stampa_libro_giornale_landscape(stampa):#stampa libro giornale in orizzontale, non lo uso più
    tab=[[40,"l"],[90,"l"],[140,"l"],[320,"l"],[510,"l"],[738,"r"],[800,"r"]]
    des=["Riga","Data","Registro/Conto","Descrizione","Partner","N.Doc/Dare","Data/Avere"]
    filename=os.path.join(here, 'stampa.pdf')
    header='LIBRO GIORNALE'
    azienda=Impostazioni.query.get(1).azienda
    footer=azienda.nome+" - "+azienda.indirizzo+" - "+azienda.cap+" "+azienda.citta+" - P.IVA "+azienda.iva+" - CF "+azienda.cf
    #header+=" stampato il "+datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    can=document3(filename, pagesize=landscape(A4), page=stampa.precedente_pagina_stampa+1, year=stampa.anno_stampa, tab=tab, des=des, header=header, footer=footer)
    riga=stampa.precedente_riga_stampa+1
    for day in daterange(stampa.data_decorrenza,stampa.data_scadenza):
        tdare,tavere=0,0
        registrazioni=Registrazione.query.join(Registro).filter(Registrazione.numero!=None).filter(Registrazione.data_contabile == day).order_by(Registrazione.numero).all()
        for r in registrazioni:
            can.newline()
            n_origine,n_partner="",""
            if r.numero_origine!=None:n_origine=r.numero_origine
            if r.partner!=None:n_partner=r.partner.nome
            can.writebold(3,r.descrizione[:37])
            can.writebold(5,n_origine)
            can.writebold(4,n_partner[:37])
            can.writebold(0,r.nome)
            can.writebold(2,r.registro.nome)
            data_decorrenza=r.data_decorrenza
            if data_decorrenza!=None:can.writebold(6,data_decorrenza.strftime("%d/%m/%y"))
            for m in r.movimento:
                can.newline()
                can.write(0,str(riga).zfill(6))
                riga+=1
                can.write(1,m.data_contabile.strftime("%d/%m/%y"))
                can.write(2,m.conto.nome[:35])
                can.write(3,str(m.descrizione)[:37])
                if m.partner!=None:can.write(4,m.partner.nome[:37])
                dare,avere=0,0
                if m.importo>=0:dare=m.importo
                else:avere=-m.importo
                tdare+=dare
                tavere+=avere
                can.write(5,valuta(dare))
                can.write(6,valuta(avere))
        if len(registrazioni)>0:
            can.newline()
            can.writebold(3,"TOTALE DEL GIORNO "+day.strftime("%d/%m/%Y"))
            can.writebold(5,valuta(tdare))
            can.writebold(6,valuta(tavere))
            can.newline()
    can.save()
    stampa.ultima_pagina_stampa=can.page
    stampa.ultima_riga_stampa=riga-1
    return can.page

def Stampa_registri_portrait(partner,dal,al,registri,filename,page,year):
    tab=[[40,"l"],[105,"l"],[260,"l"],[490,"r"],[550,"r"]]
    des=["Reg./Data","N. Doc/Conto/Descr.","Partner/Descrizione","N.Doc/Dare","Data/Avere",]
    header='REGISTRO'
    for reg in registri:header+=" "+reg.nome
    azienda=Impostazioni.query.get(1).azienda
    footer=azienda.nome+" - "+azienda.indirizzo+" - "+azienda.cap+" "+azienda.citta+" - P.IVA "+azienda.iva+" - CF "+azienda.cf
    if dal!=None:header+=" dal "+dal.strftime("%d/%m/%y")
    if al!=None:header+=" al "+al.strftime("%d/%m/%y")
    header+=" stampato il "+datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    can=document2(filename, pagesize=A4, page=page, year=year, tab=tab, des=des, header=header, footer=footer)
    filtro=""
    if dal!=None:filtro+="filter(Registrazione.data_contabile>=dal)."
    if al!=None:filtro+="filter(Registrazione.data_contabile<=al)."
    for reg in registri:
        tdare,tavere=0,0
        registrazioni= eval("Registrazione.query.filter(Registrazione.numero!=None).filter(Registrazione.registro==reg)."+filtro+"order_by(Registrazione.data_contabile).order_by(Registrazione.nome).all()")
        for r in registrazioni:
            can.newline()
            n_origine,n_partner="",""
            if r.numero_origine!=None:n_origine=r.numero_origine
            if r.partner!=None:n_partner=r.partner.nome
            can.writebold(3,n_origine)
            can.writebold(2,n_partner[:47-len(n_origine)])
            if r.partner!=None:can.writebold(1,r.descrizione[:30])
            else:can.writebold(1,r.descrizione[:69])
            can.writebold(0,r.nome)
            data_decorrenza=r.data_decorrenza
            if data_decorrenza!=None:can.writebold(4,data_decorrenza.strftime("%d/%m/%y"))
            for m in r.movimento:
                can.newline()
                can.write(0,m.data_contabile.strftime("%d/%m/%y"))
                can.write(1,m.conto.nome[:30])
                can.write(2,str(m.descrizione)[:36])
                dare,avere=0,0
                if m.importo>=0:dare=m.importo
                else:avere=-m.importo
                tdare+=dare
                tavere+=avere
                can.write(3,valuta(dare))
                can.write(4,valuta(avere))
        if len(registrazioni)>0:
            can.newline()
            can.newline()
            can.writebold(2,"TOTALE")
            can.writebold(3,valuta(tdare))
            can.writebold(4,valuta(tavere))
            can.newline()
    can.save()
    stampa.ultima_pagina_stampa=can.page
    return can.page

@app.route('/stampa_registro/<id>')
@login_required
def stampa_registro(id):
    impostazioni=Impostazioni.query.get(1)
    registri=[Registro.query.get(id)]
    partner=None
    dal=impostazioni.starting_date
    al=None
    filename=os.path.join(here, 'stampa.pdf')
    Stampa_registri(partner,dal,al,registri,filename,1,"")
    return send_file(filename,as_attachment=True,attachment_filename=registri[0].nome+".pdf")

def Stampa_registri(partner,dal,al,registri,filename,page,year):
    tab=[[40,"l"],[110,"l"],[260,"l"],[460,"l"],[738,"r"],[800,"r"]]
    des=["Reg./Data","Conto","Descrizione","Partner","N.Doc/Dare","Data/Avere"]
    header='REGISTRO'
    for reg in registri:header+=" "+reg.nome
    azienda=Impostazioni.query.get(1).azienda
    footer=azienda.nome+" - "+azienda.indirizzo+" - "+azienda.cap+" "+azienda.citta+" - P.IVA "+azienda.iva+" - CF "+azienda.cf
    if dal!=None:header+=" dal "+dal.strftime("%d/%m/%y")
    if al!=None:header+=" al "+al.strftime("%d/%m/%y")
    header+=" stampato il "+datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    can=document3(filename, pagesize=landscape(A4), page=page, year=year, tab=tab, des=des, header=header, footer=footer)
    filtro=""
    if dal!=None:filtro+="filter(Registrazione.data_contabile>=dal)."
    if al!=None:filtro+="filter(Registrazione.data_contabile<=al)."
    for reg in registri:
        tdare,tavere=0,0
        registrazioni= eval("Registrazione.query.filter(Registrazione.numero!=None).filter(Registrazione.registro==reg)."+filtro+"order_by(Registrazione.data_contabile).order_by(Registrazione.nome).all()")
        for r in registrazioni:
            can.newline()
            n_origine,n_partner="",""
            if r.numero_origine!=None:n_origine=r.numero_origine
            if r.partner!=None:n_partner=r.partner.nome
            can.writebold(4,n_origine)
            can.writebold(3,n_partner[:55-len(n_origine)])
            if r.partner!=None:can.writebold(2,r.descrizione[:40])
            else:can.writebold(2,r.descrizione[:80])
            can.writebold(0,r.nome)
            data_decorrenza=r.data_decorrenza
            if data_decorrenza!=None:can.writebold(5,data_decorrenza.strftime("%d/%m/%y"))
            for m in r.movimento:
                can.newline()
                can.write(0,m.data_contabile.strftime("%d/%m/%y"))
                can.write(1,m.conto.nome[:29])
                if m.partner!=None:
                    can.write(2,str(m.descrizione)[:40])
                    can.write(3,m.partner.nome[:40])
                else:can.write(2,str(m.descrizione)[:80])
                dare,avere=0,0
                if m.importo>=0:dare=m.importo
                else:avere=-m.importo
                tdare+=dare
                tavere+=avere
                can.write(4,valuta(dare))
                can.write(5,valuta(avere))
        if len(registrazioni)>0:
            can.newline()
            can.newline()
            can.writebold(2,"TOTALE")
            can.writebold(4,valuta(tdare))
            can.writebold(5,valuta(tavere))
            can.newline()
    can.save()
    stampa.ultima_pagina_stampa=can.page
    return can.page

def Stampa_libro_mastro_portrait(stampa):#stampa in verticale, non lo uso più
    tab=[[40,"l"],[82,"l"],[124,"l"],[185,"l"],[190,"l"],[426,"r"],[488,"r"],[550,"r"]]
    des=["Data reg","Data doc","Numero","","Descrizione","Dare","Avere","Saldo"]
    filename=os.path.join(here, 'stampa.pdf')
    header='LIBRO MASTRO'
    azienda=Impostazioni.query.get(1).azienda
    footer=azienda.nome+" - "+azienda.indirizzo+" - "+azienda.cap+" "+azienda.citta+" - P.IVA "+azienda.iva+" - CF "+azienda.cf
    if stampa.data_decorrenza!=None:header+=" dal "+stampa.data_decorrenza.strftime("%d/%m/%y")
    if stampa.data_scadenza!=None:header+=" al "+stampa.data_scadenza.strftime("%d/%m/%y")
    fconti=stampa.filtro_conto.all()
    conti=[]
    for f in fconti:
        header+=" "+f.conto.nome
        conti.append(f.conto)
    if stampa.partner!=None:header+=" "+stampa.partner.nome[:30]
    header+=" stampato il "+datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    can=document2(filename, pagesize=A4, page=1, year="", tab=tab, des=des, header=header, footer=footer)
    if len(conti)==0:conti = Conto.query.join(Sottomastro).join(Mastro).order_by(Mastro.codice).order_by(Sottomastro.codice).order_by(Conto.codice).all()
    #registri_fatture=Registro.query.filter(Registro.categoria=="Fattura").order_by(Registro.posizione).all()
    for conto in conti:
        filtro="filter(Movimento.conto==conto)."
        if stampa.partner!=None:filtro+="filter(Movimento.partner==stampa.partner)."
        saldo=0
        if stampa.data_decorrenza!=None:
            saldo=eval("db.session.query(func.sum(Movimento.importo))."+filtro+"filter(Movimento.data_contabile<stampa.data_decorrenza).scalar()") or 0
            filtro+="filter(Movimento.data_contabile>=stampa.data_decorrenza)."
        if stampa.data_scadenza!=None:filtro+="filter(Movimento.data_contabile<=stampa.data_scadenza)."
        movimenti= eval("Movimento.query."+filtro+"order_by(Movimento.data_contabile).order_by(Movimento.id).all()")
        if len(movimenti)>0:
            can.newline()
            can.writebold(0,conto.nome)
            #can.write(5,"Saldo iniziale")
            can.write(7,valuta(saldo))
            for m in movimenti:
                can.newline()
                can.write(0,m.data_contabile.strftime("%d/%m/%y"))
                if m.registrazione.data_decorrenza!=None:can.write(1,m.registrazione.data_decorrenza.strftime("%d/%m/%y"))
                can.write(2,m.registrazione.nome)
                #if m.registrazione.numero_origine!=None:can.write(3,m.registrazione.numero_origine)
                #if m.registrazione.registro in registri_fatture:
                #    can.write(4,m.registrazione.registro.nome)
                #else:
                #    can.write(4,m.descrizione[:32])

#                if m.partner!=None:
#                    l=37-min(len(m.partner.nome),20)
#                    can.write(4,m.partner.nome[:20]+" "+m.descrizione[:l])
#                else:can.write(4,m.descrizione[:38])

                can.write(4,m.descrizione[:38])
                if m.importo<0:can.write(6,valuta(-1*m.importo))
                else:can.write(5,valuta(m.importo))
                saldo+=m.importo
                can.write(7,valuta(saldo))
                if m.partner!=None:
                    can.newline()
                    can.write(4,m.partner.nome[:38])
            can.newline()
    can.save()
    stampa.ultima_pagina_stampa=can.page
    return can.page

def Stampa_libro_mastro(partner,dal,al,conti,filename):
    impostazioni=Impostazioni.query.get(1)
    tab=[[40,"l"],[90,"l"],[140,"l"],[210,"l"],[420,"l"],[676,"r"],[738,"r"],[800,"r"]]
    des=["Data reg","Data doc","Numero","Descrizione","Partner","Dare","Avere","Saldo"]
    header='LIBRO MASTRO'
    azienda=impostazioni.azienda
    footer=azienda.nome+" - "+azienda.indirizzo+" - "+azienda.cap+" "+azienda.citta+" - P.IVA "+azienda.iva+" - CF "+azienda.cf
    if dal!=None:header+=" dal "+dal.strftime("%d/%m/%y")
    if al!=None:header+=" al "+al.strftime("%d/%m/%y")
    for c in conti:header+=" "+c.nome
    if partner!=None:header+=" "+partner.nome[:30]
    header+=" stampato il "+datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    can=document3(filename, pagesize=landscape(A4), page=1, year="", tab=tab, des=des, header=header, footer=footer)
    if len(conti)==0:conti = Conto.query.join(Sottomastro).join(Mastro).order_by(Mastro.codice).order_by(Sottomastro.codice).order_by(Conto.codice).all()
    x=False
    for conto in conti:
        filtro="filter(Movimento.conto==conto)."
        if partner!=None:filtro+="filter(Movimento.partner==partner)."
        saldo=0
        if dal!=None:
            anno=dal.year#calcola il saldo iniziale
            fine_esercizio_anno=datetime.strptime(impostazioni.ultimo_giorno_esercizio+"/"+str(anno),"%d/%m/%Y").date()
            if dal > fine_esercizio_anno:inizio_esercizio=fine_esercizio_anno+relativedelta(days=1)
            else:inizio_esercizio=fine_esercizio_anno-relativedelta(years=1)+relativedelta(days=1)
            if inizio_esercizio>impostazioni.starting_date:inizio_esercizio=impostazioni.starting_date
            #inizio_esercizio=impostazioni.starting_date##messa questa come pezza, da finire di sistemare
            saldo=eval("db.session.query(func.sum(Movimento.importo))."+filtro+"filter(Movimento.data_contabile>=inizio_esercizio).filter(Movimento.data_contabile<dal).scalar()") or 0
            filtro+="filter(Movimento.data_contabile>=dal)."
        if al!=None:filtro+="filter(Movimento.data_contabile<=al)."
        movimenti= eval("Movimento.query."+filtro+"order_by(Movimento.data_contabile).order_by(Movimento.id).all()")
        if len(movimenti)>0:
            if x:can.newline()
            x=True
            can.newline()
            can.writebold(0,conto.nome)
            can.write(7,valuta(saldo))
            for m in movimenti:
                can.newline()
                can.write(0,m.data_contabile.strftime("%d/%m/%y"))
                if m.registrazione.data_decorrenza!=None:can.write(1,m.registrazione.data_decorrenza.strftime("%d/%m/%y"))
                if m.partner!=None:
                    can.write(4,m.partner.nome[:40])
                    can.write(3,m.descrizione[:40])
                else:can.write(3,m.descrizione[:80])
                can.write(2,m.registrazione.nome)
                if m.importo<0:can.write(6,valuta(-1*m.importo))
                else:can.write(5,valuta(m.importo))
                saldo+=m.importo
                can.write(7,valuta(saldo))
            #can.newline()
    can.save()
    stampa.ultima_pagina_stampa=can.page
    return can.page

@app.route('/stampa_mastrino/<id>')
@login_required
def stampa_mastrino(id):
    impostazioni=Impostazioni.query.get(1)
    partner=None
    dal=impostazioni.starting_date
    al=None
    conti=[Conto.query.get(id)]
    filename=os.path.join(here, 'stampa.pdf')
    Stampa_libro_mastro(partner,dal,al,conti,filename)
    return send_file(filename,as_attachment=True,attachment_filename=conti[0].nome+".pdf")

@app.route('/stampa_mastrino_filtrato/<id>')
@login_required
def stampa_mastrino_filtrato(id):
    impostazioni=Impostazioni.query.get(1)
    partner=current_user.partner
    dal = current_user.dal
    #if dal==None:dal=impostazioni.starting_date
    al = current_user.al
    conti=[Conto.query.get(id)]
    filename=os.path.join(here, 'stampa.pdf')
    Stampa_libro_mastro(partner,dal,al,conti,filename)
    return send_file(filename,as_attachment=True,attachment_filename=conti[0].nome+".pdf")

def Stampa_partitario_singolo(stampa):
    tab=[[40,"l"],[330,"l"],[380,"l"],[485,"r"],[550,"r"],[105,"l"],[280,"l"]]
    des=["Numero doc.","Data doc.","Data scad.","Importo","Saldo","Descrizione","Data cont."]
    filename=os.path.join(here, 'stampa.pdf')
    #header='LIBRO MASTRO'
    header=stampa.registro_stampa.nome
    azienda=Impostazioni.query.get(1).azienda
    footer=azienda.nome+" - "+azienda.indirizzo+" - "+azienda.cap+" "+azienda.citta+" - P.IVA "+azienda.iva+" - CF "+azienda.cf
    if stampa.data_decorrenza!=None:header+=" dal "+stampa.data_decorrenza.strftime("%d/%m/%y")
    if stampa.data_scadenza!=None:data_scadenza=stampa.data_scadenza
    else:data_scadenza=current_user.data
    header+=" al "+data_scadenza.strftime("%d/%m/%y")
    header+=" "+stampa.partner.nome[:30]
    header+=" stampato il "+datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    can=document2(filename, pagesize=A4, page=1, year="", tab=tab, des=des, header=header, footer=footer)
    registri=stampa.registro_stampa.filtro_registro.all()
    filtro="filter(Registrazione.partner==stampa.partner)."
    #filtro+="filter(Registrazione.saldo!=0)."
    filtro+="filter(or_("
    for i in range(len(registri)):
        filtro+="Registrazione.registro==registri["+str(i)+"].registro,"
    filtro=filtro[:-1]
    filtro+="))."
    if stampa.data_decorrenza!=None:filtro+="filter(Registrazione.data_contabile>=stampa.data_decorrenza)."
    filtro+="filter(Registrazione.data_contabile<=data_scadenza)."
    filtro+="filter(Registrazione.numero!=None)."
    registrazioni,totale,saldo=[],0,0
    segno=1
    if registri[0].registro.conto.sottomastro.mastro.tipo=="Passività": segno=segno*-1
    registrazioni = eval("Registrazione.query."+filtro+"order_by(Registrazione.data_contabile).order_by(Registrazione.numero).all()")
    #totale = (eval("db.session.query(func.sum(Registrazione.importo))."+filtro+"scalar()") or 0)*segno
    #saldo = (eval("db.session.query(func.sum(Registrazione.saldo))."+filtro+"scalar()") or 0)*segno
    totale=0
    for r in registrazioni:
        saldo=r.importo*segno
        can.newline()
        can.write(0,r.nome)
        can.write(1,r.data_decorrenza.strftime("%d/%m/%y"))
        can.write(6,r.data_contabile.strftime("%d/%m/%y"))
        can.write(2,r.data_scadenza.strftime("%d/%m/%y"))
        can.write(3,valuta(r.importo*segno))
        #can.write(5,r.descrizione[:35])

        lines=chunkstring(r.descrizione, 35)
        for i in range(len(lines)):
            if i!=0:can.newline()
            can.write(5,lines[i])

        #can.write(4,valuta(r.saldo*segno))
        validazione=r.validazione_backref.first()
        riconciliazioni=r.riconciliazione.filter(Riconciliazione.validazione!=validazione).order_by(Riconciliazione.id).all()
        for ric in riconciliazioni:
            if ric.movimento.data_contabile<=data_scadenza:saldo+=ric.movimento.importo*segno
        can.write(4,valuta(saldo))
        totale+=saldo
        for ric in riconciliazioni:
            if ric.movimento.data_contabile<=data_scadenza:
                can.newline()
                #can.write(5,ric.validazione.registrazione.descrizione[:38])
                can.write(0,ric.validazione.registrazione.nome)
                can.write(6,ric.movimento.data_contabile.strftime("%d/%m/%y"))
                can.write(3,valuta(ric.movimento.importo*segno))
        can.newline()
    can.newline()
    can.newline()
    can.writebold(0,"Totale")
    #can.write(3,valuta(totale))
    can.writebold(4,valuta(totale))
    can.save()
    stampa.ultima_pagina_stampa=can.page
    return can.page

def Stampa_partitario_insoluti(stampa):
    tab=[[40,"l"],[250,"r"],[325,"r"],[400,"r"],[475,"r"],[550,"r"]]
    filename=os.path.join(here, 'stampa.pdf')
    header=stampa.registro_stampa.nome+" INSOLUTI"
    #if stampa.data_decorrenza!=None:header+=" dal "+stampa.data_decorrenza.strftime("%d/%m/%y")
    if stampa.data_scadenza!=None:data_scadenza=stampa.data_scadenza
    else:data_scadenza=current_user.data
    header+=" al "+data_scadenza.strftime("%d/%m/%y")
    header+=" stampato il "+datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    azienda=Impostazioni.query.get(1).azienda
    footer=azienda.nome+" - "+azienda.indirizzo+" - "+azienda.cap+" "+azienda.citta+" - P.IVA "+azienda.iva+" - CF "+azienda.cf
    des=["Partner",(data_scadenza+relativedelta(months=-4)).strftime("%d/%m/%y"),(data_scadenza+relativedelta(months=-3)).strftime("%d/%m/%y"),(data_scadenza+relativedelta(months=-2)).strftime("%d/%m/%y"),(data_scadenza+relativedelta(months=-1)).strftime("%d/%m/%y"),data_scadenza.strftime("%d/%m/%y")]
    can=document2(filename, pagesize=A4, page=1, year="", tab=tab, des=des, header=header, footer=footer)
    registri=stampa.registro_stampa.filtro_registro.all()
    partners = Partner.query.order_by(Partner.nome).all()
    totale=[0,0,0,0,0]
    segno=1
    if registri[0].registro.conto.sottomastro.mastro.tipo=="Passività": segno=segno*-1
    filtro="filter(Registrazione.partner==partner)."
    filtro+="filter(Registrazione.saldo!=0)."
    filtro+="filter(or_("
    for i in range(len(registri)):
        filtro+="Registrazione.registro==registri["+str(i)+"].registro,"
    filtro=filtro[:-1]
    filtro+="))."
    #if stampa.data_decorrenza!=None:filtro+="filter(Registrazione.data_decorrenza>=stampa.data_decorrenza)."
    for partner in partners:
        saldo=[0,0,0,0,0]
        for i in range(len(totale)):
            filtro_al="filter(Registrazione.data_scadenza<(data_scadenza+relativedelta(months=-i)))."
            saldo[i] = (eval("db.session.query(func.sum(Registrazione.saldo))."+filtro+filtro_al+"scalar()") or 0)*segno
            #totale[i]+=saldo[i]
        if saldo[0]!=0:
            can.newline()
            can.write(0,partner.nome[:33])
            can.write(1,valuta(saldo[4]))
            can.write(2,valuta(saldo[3]))
            can.write(3,valuta(saldo[2]))
            can.write(4,valuta(saldo[1]))
            can.write(5,valuta(saldo[0]))
            for i in range(len(totale)):totale[i]+=saldo[i]
    can.newline()
    can.newline()
    can.writebold(0,"Totale")
    can.write(1,valuta(totale[4]))
    can.write(2,valuta(totale[3]))
    can.write(3,valuta(totale[2]))
    can.write(4,valuta(totale[1]))
    can.writebold(5,valuta(totale[0]))
    can.save()
    stampa.ultima_pagina_stampa=can.page
    return can.page

def Stampa_partitario_insoluti_2(stampa):#calcola gli insoluti alla data indicata, ignorando se sono stati saldati dopo
    tab=[[40,"l"],[250,"r"],[325,"r"],[400,"r"],[475,"r"],[550,"r"]]
    filename=os.path.join(here, 'stampa.pdf')
    header=stampa.registro_stampa.nome
    #if stampa.data_decorrenza!=None:header+=" dal "+stampa.data_decorrenza.strftime("%d/%m/%y")
    if stampa.data_scadenza!=None:data_scadenza=stampa.data_scadenza
    else:data_scadenza=current_user.data
    header+=" al "+data_scadenza.strftime("%d/%m/%y")
    header+=" stampato il "+datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    azienda=Impostazioni.query.get(1).azienda
    footer=azienda.nome+" - "+azienda.indirizzo+" - "+azienda.cap+" "+azienda.citta+" - P.IVA "+azienda.iva+" - CF "+azienda.cf
    des=["Partner",(data_scadenza+relativedelta(months=-4)).strftime("%d/%m/%y"),(data_scadenza+relativedelta(months=-3)).strftime("%d/%m/%y"),(data_scadenza+relativedelta(months=-2)).strftime("%d/%m/%y"),(data_scadenza+relativedelta(months=-1)).strftime("%d/%m/%y"),data_scadenza.strftime("%d/%m/%y")]
    can=document2(filename, pagesize=A4, page=1, year="", tab=tab, des=des, header=header, footer=footer)
    registri=stampa.registro_stampa.filtro_registro.all()
    partners = Partner.query.order_by(Partner.nome).all()
    totale=[0,0,0,0,0]
    segno=1
    if registri[0].registro.conto.sottomastro.mastro.tipo=="Passività": segno=segno*-1
    filtro="filter(Registrazione.partner==partner)."
    filtro+="filter(or_("
    for i in range(len(registri)):
        filtro+="Registrazione.registro==registri["+str(i)+"].registro,"
    filtro=filtro[:-1]
    filtro+="))."
    filtro+="filter(Registrazione.data_contabile<=DATA)."
    #if stampa.data_decorrenza!=None:filtro+="filter(Registrazione.data_decorrenza>=stampa.data_decorrenza)."
    for partner in partners:
        saldo=[0,0,0,0,0]
        for i in range(len(totale)):
            DATA=data_scadenza+relativedelta(months=-i)
            registrazioni = eval("Registrazione.query."+filtro+"all()")
            for r in registrazioni:
                riconciliazioni=r.riconciliazione.all()
                for ric in riconciliazioni:
                        if ric.movimento.data_contabile<=DATA:
                            saldo[i]+=ric.movimento.importo*segno
        if saldo[0]!=0:
            can.newline()
            can.write(0,partner.nome[:33])
            can.write(1,valuta(saldo[4]))
            can.write(2,valuta(saldo[3]))
            can.write(3,valuta(saldo[2]))
            can.write(4,valuta(saldo[1]))
            can.write(5,valuta(saldo[0]))
            for i in range(len(totale)):totale[i]+=saldo[i]
    can.newline()
    can.newline()
    can.writebold(0,"Totale")
    can.write(1,valuta(totale[4]))
    can.write(2,valuta(totale[3]))
    can.write(3,valuta(totale[2]))
    can.write(4,valuta(totale[1]))
    can.writebold(5,valuta(totale[0]))
    can.save()
    stampa.ultima_pagina_stampa=can.page
    return can.page

def Stampa_partitario(stampa):
    tab=[[40,"l"],[550,"r"]]
    filename=os.path.join(here, 'stampa.pdf')
    header=stampa.registro_stampa.nome
    #if stampa.data_decorrenza!=None:header+=" dal "+stampa.data_decorrenza.strftime("%d/%m/%y")
    if stampa.data_scadenza!=None:data_scadenza=stampa.data_scadenza
    else:data_scadenza=current_user.data
    header+=" al "+data_scadenza.strftime("%d/%m/%y")
    header+=" stampato il "+datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    azienda=Impostazioni.query.get(1).azienda
    footer=azienda.nome+" - "+azienda.indirizzo+" - "+azienda.cap+" "+azienda.citta+" - P.IVA "+azienda.iva+" - CF "+azienda.cf
    des=["Partner","Importo"]
    can=document2(filename, pagesize=A4, page=1, year="", tab=tab, des=des, header=header, footer=footer)
    registri=stampa.registro_stampa.filtro_registro.all()
    partners = Partner.query.order_by(Partner.nome).all()
    totale=[0,0,0,0,0]
    segno=1
    if registri[0].registro.conto.sottomastro.mastro.tipo=="Passività": segno=segno*-1
    filtro="filter(Registrazione.partner==partner)."
    filtro+="filter(or_("
    for i in range(len(registri)):
        filtro+="Registrazione.registro==registri["+str(i)+"].registro,"
    filtro=filtro[:-1]
    filtro+="))."
    filtro+="filter(Registrazione.data_contabile<=data_scadenza)."
    #if stampa.data_decorrenza!=None:filtro+="filter(Registrazione.data_decorrenza>=stampa.data_decorrenza)."
    totale=0
    for partner in partners:
        saldo=0
        registrazioni = eval("Registrazione.query."+filtro+"all()")
        for r in registrazioni:
            riconciliazioni=r.riconciliazione.all()
            for ric in riconciliazioni:
                    if ric.movimento.data_contabile<=data_scadenza:
                        saldo+=ric.movimento.importo*segno
        if saldo!=0:
            can.newline()
            can.write(0,partner.nome[:80])
            can.write(1,valuta(saldo))
            totale+=saldo
    can.newline()
    can.newline()
    can.write(0,"Totale")
    can.write(1,valuta(totale))
    can.save()
    stampa.ultima_pagina_stampa=can.page
    return can.page

def Stampa_bilancio_contabile(stampa):
    tab=[[40,"l"],[300,"r"]]
    des=["Descrizione","Importo"]
    filename=os.path.join(here, 'stampa.pdf')
    header='BILANCIO CONTABILE'
    if stampa.data_decorrenza!=None:header+=" dal "+stampa.data_decorrenza.strftime("%d/%m/%y")
    if stampa.data_scadenza!=None:header+=" al "+stampa.data_scadenza.strftime("%d/%m/%y")
    header+=" stampato il "+datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    azienda=Impostazioni.query.get(1).azienda
    footer=azienda.nome+" - "+azienda.indirizzo+" - "+azienda.cap+" "+azienda.citta+" - P.IVA "+azienda.iva+" - CF "+azienda.cf
    can=document2(filename, pagesize=A4, page=1, year="", tab=tab, des=des, header=header, footer=footer)
    if stampa.data_decorrenza!=None:filtro="filter(Movimento.data_contabile>=stampa.data_decorrenza)."
    if stampa.data_scadenza!=None:filtro+="filter(Movimento.data_contabile<=stampa.data_scadenza)."
    attivita, passivita, costi, ricavi = 0,0,0,0
    for m in Mastro.query.order_by(Mastro.codice).all():
        if m.tipo=="Passività" or m.tipo=="Ricavi":segno=-1
        else:segno=1
        saldo=segno*(eval("db.session.query(func.sum(Movimento.importo)).join(Conto).join(Sottomastro)."+filtro+"filter(Sottomastro.mastro==m).scalar()") or 0)
        if m.tipo=="Attività":attivita=saldo
        if m.tipo=="Passività":passivita=saldo
        if m.tipo=="Costi":costi=saldo
        if m.tipo=="Ricavi":ricavi=saldo
        if saldo!=0:
            can.newline()
            can.writebold(0,m.nome)
            can.writebold(1,valuta(saldo))
            can.newline()
            for s in Sottomastro.query.filter(Sottomastro.mastro==m).order_by(Sottomastro.codice).all():
                saldo=segno*(eval("db.session.query(func.sum(Movimento.importo)).join(Conto)."+filtro+"filter(Conto.sottomastro==s).scalar()") or 0)
                if saldo!=0:
                    can.newline()
                    can.writebold(0,s.nome)
                    can.writebold(1,valuta(saldo))
                    for c in Conto.query.filter(Conto.sottomastro==s).order_by(Conto.codice).all():
                        saldo=segno*(eval("db.session.query(func.sum(Movimento.importo))."+filtro+"filter(Movimento.conto==c).scalar()") or 0)
                        if saldo!=0:
                            can.newline()
                            can.write(0,c.nome)
                            can.write(1,valuta(saldo))
            can.newline()
    can.newline()
    can.writebold(0,"ATTIVITÀ")
    can.writebold(1,valuta(attivita))
    can.newline()
    can.writebold(0,"PASSIVITÀ")
    can.writebold(1,valuta(passivita))
    can.newline()
    can.writebold(0,"PATRIMONIO NETTO")
    can.writebold(1,valuta(attivita-passivita))
    can.newline()
    can.newline()
    can.writebold(0,"COSTI")
    can.writebold(1,valuta(costi))
    can.newline()
    can.writebold(0,"RICAVI")
    can.writebold(1,valuta(ricavi))
    can.newline()
    can.writebold(0,"UTILE DI ESERCIZIO")
    can.writebold(1,valuta(ricavi-costi))

    can.save()
    stampa.ultima_pagina_stampa=can.page
    return can.page

def calcola_LIPE(registrazione):
    impostazioni=Impostazioni.query.get(1)
    fatf=Registrazione.query.filter_by(registro=impostazioni.registro_fatf).filter(and_(Registrazione.data_contabile >= registrazione.data_decorrenza, Registrazione.data_contabile <= registrazione.data_scadenza)).filter(Registrazione.numero!=None).all()
    notf=Registrazione.query.filter_by(registro=impostazioni.registro_notf).filter(and_(Registrazione.data_contabile >= registrazione.data_decorrenza, Registrazione.data_contabile <= registrazione.data_scadenza)).filter(Registrazione.numero!=None).all()
    VP2,VP3,VP4,VP5=0,0,0,0
    for r in fatf:
        for voce in r.voce_iva:
            #if voce.imposta.natura!="N1" and voce.imposta.natura!="N2":#Zanotti ha detto il 15/04/2021 che non vanno solo N1 e N2
            if not voce.imposta.no_lipe:
                VP3+=voce.imponibile
                if not voce.imposta.indetraibile and voce.imposta.esigibilita!="S":VP5+=voce.iva#esclude l'iva indetraibile e lo split payment dal totale iva
                if voce.imposta.natura!=None and voce.imposta.natura[:2]=="N6":VP4+=voce.iva#se è RC va anche nell'iva vendite
    for r in notf:
        for voce in r.voce_iva:
            #if voce.imposta.natura!="N1" and voce.imposta.natura!="N2":
            if not voce.imposta.no_lipe:
                VP3-=voce.imponibile
                if not voce.imposta.indetraibile and voce.imposta.esigibilita!="S":VP5-=voce.iva#esclude l'iva indetraibile e lo split payment dal totale iva
                if voce.imposta.natura!=None and voce.imposta.natura[:2]=="N6":VP4-=voce.iva#se è RC va anche nell'iva vendite
    fatc=Registrazione.query.filter_by(registro=impostazioni.registro_fatc).filter(and_(Registrazione.data_contabile >= registrazione.data_decorrenza, Registrazione.data_contabile <= registrazione.data_scadenza)).filter(Registrazione.numero!=None).all()
    notc=Registrazione.query.filter_by(registro=impostazioni.registro_notc).filter(and_(Registrazione.data_contabile >= registrazione.data_decorrenza, Registrazione.data_contabile <= registrazione.data_scadenza)).filter(Registrazione.numero!=None).all()
    for r in fatc:
        for voce in r.voce_iva:
            #if voce.imposta.natura!="N1" and voce.imposta.natura!="N2":
            if not voce.imposta.no_lipe:
                VP2+=voce.imponibile
                if not voce.imposta.indetraibile and voce.imposta.esigibilita!="S":VP4+=voce.iva#esclude l'iva indetraibile e lo split payment dal totale iva
    for r in notc:
        for voce in r.voce_iva:
            #if voce.imposta.natura!="N1" and voce.imposta.natura!="N2":
            if not voce.imposta.no_lipe:
                VP2-=voce.imponibile
                if not voce.imposta.indetraibile and voce.imposta.esigibilita!="S":VP4-=voce.iva#esclude l'iva indetraibile e lo split payment dal totale iva
    return VP2,VP3,VP4,VP5
# S T A M P A #########################################################################



# I V A #########################################################################
@app.route('/iva/<id>', methods=['GET', 'POST'])
@login_required
def iva(id):# visualizza o modifica la liquidazione IVA
    partners = Partner.query.order_by(Partner.nome).with_entities(Partner.nome).all()
    registrazione=Registrazione.query.get(id)
    allegati=registrazione.allegato.order_by(Allegato.id).all()
    voci=registrazione.voce.order_by(Voce.id).all()
    totale=0
    for v in voci:
        totale+=v.importo
    if registrazione.validazione_backref.first() == None:
        registrazione.importo=totale*registrazione.registro.segno
        db.session.commit()
        form = IVAForm()
        upload_form = UploadForm()
        if upload_form.submit2.data and upload_form.validate():
            allegato=Allegato(registrazione=registrazione, nome=upload_form.file.data.filename, binario=upload_form.file.data.read())
            db.session.add(allegato)
            db.session.commit()
            return redirect(url_for('iva', id=id))
        if form.submit.data and form.validate():
            registrazione.descrizione=form.descrizione.data
            registrazione.data_contabile=form.data_contabile.data
            registrazione.data_decorrenza=form.data_decorrenza.data
            registrazione.data_scadenza=form.data_scadenza.data
            current_user.data_decorrenza=form.data_decorrenza.data
            current_user.data_scadenza=form.data_scadenza.data
            registrazione.note=form.note.data
            registrazione.partner=Partner.query.filter_by(nome=form.partner.data).first()
            registri_fatture, conto_iva, imposta, imponibile, iva, IVA=calcola_IVA(registrazione)

            for c in conto_iva:#rimuovo le voci della registrazione eventualmente già presenti
                vo=registrazione.voce.filter_by(conto=c).all()
                for v in vo:db.session.delete(v)

            for c in range(len(conto_iva)):
                for i in range(len(imposta)):
                    if iva[i][c]!=0 and (not imposta[i].indetraibile) and imposta[i].esigibilita!="S":
                        voce=Voce(registrazione=registrazione, conto=conto_iva[c], importo=-registrazione.registro.segno*iva[i][c], descrizione=imposta[i].nome)
                        db.session.add(voce)
            db.session.commit()

            flash('I dati sono stati salvati !')
        if form.is_submitted() and not form.validate():pass
        else:
            form.descrizione.data=registrazione.descrizione
            form.data_contabile.data=registrazione.data_contabile
            form.data_decorrenza.data=registrazione.data_decorrenza
            form.data_scadenza.data=registrazione.data_scadenza
            form.note.data=registrazione.note
            if registrazione.partner != None: form.partner.data=registrazione.partner.nome
        allegati=registrazione.allegato.order_by(Allegato.id).all()
        voci=registrazione.voce.order_by(Voce.id).all()
        riconciliazioni=[]
        for v in voci:
            if v.riconciliazione != None: riconciliazioni.append(v.riconciliazione)
        registrazioni=Registrazione.query.filter_by(partner=registrazione.partner).filter(Registrazione.validazione_backref != None).filter(Registrazione.saldo != 0).order_by(Registrazione.data_contabile).all()
        for r in riconciliazioni: 
            try:registrazioni.remove(r)
            except:pass
        return render_template('edit_iva.html', registrazione=registrazione, form=form, upload_form=upload_form, partners=partners, registrazioni=registrazioni, voci=voci, allegati=allegati)
    else:
        validazione=registrazione.validazione_backref.first()
        movimenti = Movimento.query.filter_by(registrazione=registrazione).order_by(Movimento.id).all()
        dare,avere = 0,0
        for m in movimenti:
            if m.importo > 0: dare=dare+m.importo
            else: avere=avere-m.importo
        riconciliazioni=Riconciliazione.query.filter_by(registrazione=registrazione).filter(Riconciliazione.validazione!=validazione).order_by(Riconciliazione.id).all()
        return render_template('iva.html', registrazione=registrazione, partners=partners, voci=voci, totale=totale, movimenti=movimenti, dare=dare, avere=avere, riconciliazioni=riconciliazioni, Validazione=Validazione, allegati=allegati)

@app.route('/voce_iva/<id>', methods=['GET', 'POST'])
@login_required
def voce_iva(id):#modifica la voce della liquidazione IVA
    conti = Conto.query.all()
    voce = Voce.query.get(id)
    form = VoceIVAForm()
    if voce.registrazione.validazione_backref.first() == None:
        if form.validate_on_submit():
            voce.descrizione=form.descrizione.data
            voce.conto=Conto.query.filter_by(nome=form.conto.data).first()
            voce.importo=form.importo.data
            db.session.commit()
            flash('I dati sono stati salvati !')
            return redirect(url_for('registrazione', id=voce.registrazione.id))
        if form.is_submitted() and not form.validate():pass
        else:
            form.descrizione.data=voce.descrizione
            if voce.conto!=None:form.conto.data=voce.conto.nome
            form.importo.data=voce.importo
    return render_template('voce_iva.html', voce=voce, form=form, conti=conti)

@app.route('/registra_iva/<id>', methods=['GET', 'POST'])
@login_required
def registra_iva(id):#registra la registrazione liquidazione IVA
    registrazione=Registrazione.query.get(id)
    if registrazione.validazione_backref.first() == None:
        reg_iva(registrazione)
    return redirect(url_for('iva', id=id))

@app.route('/aggiungi_riconciliazione_iva/<id>', methods=['GET', 'POST'])
@login_required
def aggiungi_riconciliazione_iva(id):#aggiunge riconciliazione IVA
    riconciliazione_id = request.args.get('riconciliazione_id')
    riconciliazione=Registrazione.query.get(riconciliazione_id)
    registrazione=Registrazione.query.get(id)
    voce=Voce(registrazione=registrazione, descrizione=riconciliazione.descrizione, conto=riconciliazione.registro.conto, partner=riconciliazione.partner, importo=riconciliazione.saldo*registrazione.registro.segno, riconciliazione=riconciliazione, quantita=1)
    db.session.add(voce)
    db.session.commit()
    return redirect(url_for('registrazione', id=id))

def reg_iva(registrazione):#registra la registrazione IVA
    validazione=Validazione(registrazione=registrazione)
    db.session.add(validazione)
    anno=registrazione.data_contabile.year
    dal=datetime.strptime("01/01/"+str(anno),"%d/%m/%Y").date()
    al=datetime.strptime("31/12/"+str(anno),"%d/%m/%Y").date()
    i=1
    while Registrazione.query.filter_by(registro=registrazione.registro).filter(and_(Registrazione.data_contabile >= dal, Registrazione.data_contabile <= al)).filter_by(numero=i).first()!=None:
        i=i+1
    registrazione.numero=i
    registrazione.nome=registrazione.registro.codice+"/"+str(anno)[2:]+"/"+ str(i).zfill(4)
    reg_saldo=[]

    voci=registrazione.voce.order_by(Voce.id).all()
    totale=0
    for v in voci:
        totale+=v.importo
    registrazione.importo=totale*registrazione.registro.segno

    movimento=Movimento(descrizione=registrazione.descrizione, data_contabile=registrazione.data_contabile, importo=totale*registrazione.registro.segno, conto=registrazione.registro.conto_iva, partner=registrazione.partner, registrazione=registrazione, validazione=validazione)
    db.session.add(movimento)
    riconciliazione=Riconciliazione(validazione=validazione, registrazione=registrazione, movimento=movimento)
    db.session.add(riconciliazione)

    for v in voci:
        movimento=Movimento(descrizione=v.descrizione, data_contabile=registrazione.data_contabile, importo=-v.importo*registrazione.registro.segno, conto=v.conto, partner=v.partner, registrazione=registrazione, validazione=validazione)
        db.session.add(movimento)
        if v.riconciliazione != None:
            riconciliazione=Riconciliazione(validazione=validazione, registrazione=v.riconciliazione, movimento=movimento)
            db.session.add(riconciliazione)
            reg_saldo.append(v.riconciliazione)

    if registrazione.partner!=None:partner_nome=registrazione.partner.nome
    else:partner_nome=""
    datalog="Validata registrazione ["+registrazione.nome+"] importo["+str(registrazione.importo)+"] partner["+partner_nome+"] data contabile["+format_date(registrazione.data_contabile)+"] data registrazione["+format_date(registrazione.data_decorrenza)+"] data scadenza["+format_date(registrazione.data_scadenza)+"]"
    log = Log(datalog=datalog, user=current_user.username, timestamp = func.now())
    db.session.add(log)
    db.session.commit()
    reg_saldo.append(registrazione)
    saldo(reg_saldo)
# I V A #########################################################################



# G E N E R I C O #########################################################################
@app.route('/generico/<id>', methods=['GET', 'POST'])
@login_required
def generico(id):#visualizza o modifica la registrazione generica
    partners = Partner.query.order_by(Partner.nome).with_entities(Partner.nome).all()
    registrazione=Registrazione.query.get(id)
    allegati=registrazione.allegato.order_by(Allegato.id).all()
    registrazioni_generate=Registrazione.query.filter_by(validazione=registrazione.validazione_backref.first()).all()
    dare=0
    avere=0
    validazione=registrazione.validazione_backref.first()
    if validazione == None:
        form = GenericoForm()
        upload_form = UploadForm()
        if upload_form.submit2.data and upload_form.validate():
            allegato=Allegato(registrazione=registrazione, nome=upload_form.file.data.filename, binario=upload_form.file.data.read())
            db.session.add(allegato)
            db.session.commit()
            return redirect(url_for('generico', id=id))
        if form.submit.data and form.validate():
            registrazione.descrizione=form.descrizione.data
            registrazione.data_contabile=form.data_contabile.data
            registrazione.partner=Partner.query.filter_by(nome=form.partner.data).first()
            db.session.commit()
            flash('I dati sono stati salvati !')
        if form.is_submitted() and not form.validate():pass
        else:
            form.descrizione.data=registrazione.descrizione
            form.data_contabile.data=registrazione.data_contabile
            if registrazione.partner != None: form.partner.data=registrazione.partner.nome
        voci = Voce.query.join(Conto).join(Sottomastro).join(Mastro).filter(Voce.registrazione==registrazione).order_by(Mastro.codice).order_by(Sottomastro.codice).order_by(Conto.codice).order_by(Voce.id).all()
        voci = voci + registrazione.voce.filter(Voce.conto==None).order_by(Voce.id).all()
        for v in voci:
            if v.importo > 0: dare=dare+v.importo
            else: avere=avere-v.importo
        riconciliazioni=[]
        for v in voci:
            if v.riconciliazione != None: riconciliazioni.append(v.riconciliazione)
        registrazioni=Registrazione.query.filter_by(partner=registrazione.partner).filter(Registrazione.validazione_backref != None).filter(Registrazione.saldo != 0).order_by(Registrazione.data_contabile).order_by(Registrazione.numero).all()
        for r in riconciliazioni: 
            try:registrazioni.remove(r)
            except:pass
        return render_template('edit_generico.html', registrazione=registrazione, form=form, upload_form=upload_form, partners=partners, voci=voci, registrazioni=registrazioni, dare=dare, avere=avere, allegati=allegati)
    else:
        movimenti = Movimento.query.join(Conto).join(Sottomastro).join(Mastro).filter(Movimento.registrazione==registrazione).order_by(Mastro.codice).order_by(Sottomastro.codice).order_by(Conto.codice).order_by(Movimento.id).all()
        dare,avere = 0,0
        riconciliazioni=[]
        for m in movimenti:
            if m.importo > 0: dare=dare+m.importo
            else: avere=avere-m.importo
            riconciliazioni.append(Riconciliazione.query.filter_by(validazione=validazione).filter_by(movimento=m).first())
        return render_template('generico.html', registrazione=registrazione, movimenti=movimenti, dare=dare, avere=avere, riconciliazioni=riconciliazioni, registrazioni_generate=registrazioni_generate, allegati=allegati)

@app.route('/voce_generico/<id>', methods=['GET', 'POST'])
@login_required
def voce_generico(id):#modifica la voce della registrazione generica
    partners = Partner.query.order_by(Partner.nome).with_entities(Partner.nome).all()
    conti = Conto.query.with_entities(Conto.nome).all()
    imposte = Imposta.query.all()
    voce = Voce.query.get(id)
    form = VoceGenericoForm()
    if form.validate_on_submit():
        voce.descrizione=form.descrizione.data
        voce.conto=Conto.query.filter_by(nome=form.conto.data).first()
        #voce.importo=form.dare.data-form.avere.data
        voce.importo=Decimal(form.dare.data-form.avere.data).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        voce.partner=Partner.query.filter_by(nome=form.partner.data).first()
        db.session.commit()
        flash('I dati sono stati salvati !')
        return redirect(url_for('registrazione', id=voce.registrazione.id))
    if form.is_submitted() and not form.validate():pass
    else:
        form.descrizione.data=voce.descrizione
        if voce.partner != None: form.partner.data=voce.partner.nome
        if voce.conto!=None:form.conto.data=voce.conto.nome
        if voce.importo>=0:
            form.dare.data=voce.importo
            form.avere.data=0.0
        else:
            form.dare.data=0.0
            form.avere.data=-voce.importo
    return render_template('voce_generico.html', voce=voce, form=form, conti=conti, imposte=imposte, partners=partners)

@app.route('/registra_generico/<id>', methods=['GET', 'POST'])
@login_required
def registra_generico(id):#registra la registrazione generica
    registrazione=Registrazione.query.get(id)
    if not validate(registrazione):
        flash('ERRORE DI VALIDAZIONE !')
        return redirect(url_for('generico', id=id))
    if registrazione.validazione_backref.first() == None:
        reg_generico(registrazione)
        #ritenuta=[]
        ritenute=Ritenuta.query.all()
        for voce in registrazione.voce:
            if voce.registro != None:# verifica se devo generare una ricevuta verso partenr
                ricevuta=Registrazione(registro=voce.registro)
                db.session.add(ricevuta)
                ricevuta.partner=registrazione.partner
                ricevuta.data_contabile=registrazione.data_contabile
                ricevuta.data_decorrenza=registrazione.data_contabile
                ricevuta.data_scadenza=registrazione.data_contabile
                ricevuta.importo=0
                ricevuta.saldo=0
                ricevuta.descrizione="Generato da "+registrazione.nome
                vo=Voce(registrazione=ricevuta, importo=voce.registro.segno*voce.importo, quantita=1, conto=voce.registro.conto, descrizione=registrazione.descrizione)
                db.session.add(vo)
                ricevuta.validazione=registrazione.validazione_backref.first()
                reg_ricevuta(ricevuta)
            for ritenuta in ritenute:# verifica se una delle voci della registrazione fa riferimento ad una ritenuta d'acconto e nel caso genera la registrazione
                if voce.conto==ritenuta.conto_transito_ritenuta:
                    ritenuta_acconto=Registrazione(registro=ritenuta.registro_ritenuta)
                    db.session.add(ritenuta_acconto)
                    ritenuta_acconto.descrizione=voce.descrizione+" generata da "+str(registrazione.nome)
                    ritenuta_acconto.partner=Impostazioni.query.get(1).erario
                    ritenuta_acconto.data_contabile=registrazione.data_contabile
                    anno=registrazione.data_contabile.year
                    mese=registrazione.data_contabile.month + 1
                    data_scadenza=datetime.strptime("16/"+str(mese)+"/"+str(anno),"%d/%m/%Y").date()
                    ritenuta_acconto.data_scadenza=data_scadenza
                    ritenuta_acconto.importo=0
                    ritenuta_acconto.saldo=0
                    vo=Voce(registrazione=ritenuta_acconto, importo=-voce.importo, quantita=1, conto=voce.conto)
                    db.session.add(vo)
                    vo.descrizione="Transito RA"
                    ritenuta_acconto.validazione=registrazione.validazione_backref.first()
                    reg_fattura(ritenuta_acconto)
    return redirect(url_for('generico', id=id))

def reg_generico(registrazione):#registra la registrazione generica
    validazione=Validazione(registrazione=registrazione)
    db.session.add(validazione)
    anno=registrazione.data_contabile.year
    dal=datetime.strptime("01/01/"+str(anno),"%d/%m/%Y").date()
    al=datetime.strptime("31/12/"+str(anno),"%d/%m/%Y").date()
    i=1
    while Registrazione.query.filter_by(registro=registrazione.registro).filter(and_(Registrazione.data_contabile >= dal, Registrazione.data_contabile <= al)).filter_by(numero=i).first()!=None:
        i=i+1
    registrazione.numero=i
    registrazione.nome=registrazione.registro.codice+"/"+str(anno)[2:]+"/"+ str(i).zfill(4)
    reg_saldo=[]

    voci=registrazione.voce.order_by(Voce.id).all()
    for v in voci:
        if v.conto!=None and v.descrizione!=None:
            movimento=Movimento(descrizione=v.descrizione, data_contabile=registrazione.data_contabile, importo=v.importo, conto=v.conto, partner=v.partner, registrazione=registrazione, validazione=validazione)
            db.session.add(movimento)
            if v.riconciliazione != None:
                riconciliazione=Riconciliazione(validazione=validazione, registrazione=v.riconciliazione, movimento=movimento)
                db.session.add(riconciliazione)
                reg_saldo.append(v.riconciliazione)
    if registrazione.partner!=None:partner_nome=registrazione.partner.nome
    else:partner_nome=""
    datalog="Validata registrazione ["+registrazione.nome+"] importo["+str(registrazione.importo)+"] partner["+partner_nome+"] data contabile["+format_date(registrazione.data_contabile)+"] data registrazione["+format_date(registrazione.data_decorrenza)+"] data scadenza["+format_date(registrazione.data_scadenza)+"]"
    log = Log(datalog=datalog, user=current_user.username, timestamp = func.now())
    db.session.add(log)
    db.session.commit()
    saldo(reg_saldo)
# G E N E R I C O #########################################################################



# C A S S A #########################################################################
@app.route('/cassa/<id>', methods=['GET', 'POST'])
@login_required
def cassa(id):#mostra la registrazione di cassa in visualizzazione o in editing
    partners = Partner.query.order_by(Partner.nome).with_entities(Partner.nome).all()
    ricevute = Registro.query.filter(Registro.categoria=="Ricevuta").all()
    registrazione=Registrazione.query.get(id)
    allegati=registrazione.allegato.order_by(Allegato.id).all()
    registrazioni_generate=Registrazione.query.filter_by(validazione=registrazione.validazione_backref.first()).all()
    dare=0
    avere=0
    validazione=registrazione.validazione_backref.first()
    if validazione == None:
        form = CassaForm()
        upload_form = UploadForm()
        if upload_form.submit2.data and upload_form.validate():
            allegato=Allegato(registrazione=registrazione, nome=upload_form.file.data.filename, binario=upload_form.file.data.read())
            db.session.add(allegato)
            db.session.commit()
            return redirect(url_for('cassa', id=id))
        if form.submit.data and form.validate():
            registrazione.descrizione=form.descrizione.data
            registrazione.data_contabile=form.data_contabile.data
            #registrazione.importo=form.importo.data
            registrazione.importo=Decimal(form.importo.data).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
            registrazione.partner=Partner.query.filter_by(nome=form.partner.data).first()
            voce=Voce.query.filter_by(registrazione=registrazione).filter_by(conto=registrazione.registro.conto).first()
            if voce is None:
                voce=Voce(registrazione=registrazione)
                db.session.add(voce)
            voce.descrizione=form.descrizione.data
            voce.conto=registrazione.registro.conto
            #voce.importo=form.importo.data
            voce.importo=registrazione.importo
            db.session.commit()
            flash('I dati sono stati salvati !')
        if form.is_submitted() and not form.validate():pass
        else:
            form.descrizione.data=registrazione.descrizione
            form.data_contabile.data=registrazione.data_contabile
            form.importo.data=registrazione.importo
            if registrazione.partner != None: form.partner.data=registrazione.partner.nome
        voci = Voce.query.join(Conto).join(Sottomastro).join(Mastro).filter(Voce.registrazione==registrazione).order_by(Mastro.codice).order_by(Sottomastro.codice).order_by(Conto.codice).order_by(Voce.id).all()
        voci = voci + registrazione.voce.filter(Voce.conto==None).order_by(Voce.id).all()
        for v in voci:
            if v.importo > 0: dare=dare+v.importo
            else: avere=avere-v.importo
        riconciliazioni=[]
        for v in voci:
            if v.riconciliazione != None: riconciliazioni.append(v.riconciliazione)
        #registrazioni=Registrazione.query.filter_by(partner=registrazione.partner).filter(Registrazione.validazione_backref != None).filter(Registrazione.saldo != 0).order_by(Registrazione.data_contabile).all()
        filtro="filter_by(partner=registrazione.partner)."
        if registrazione.partner!=None:filtro="filter(or_(Registrazione.partner==registrazione.partner, Registrazione.domiciliatario==registrazione.partner))."
        #filtro="filter(or_(Registrazione.partner==registrazione.partner, Registrazione.domiciliatario==registrazione.partner))."

        #registrazioni=Registrazione.query.filter(or_(Registrazione.partner==registrazione.partner, Registrazione.domiciliatario==registrazione.partner)).filter(Registrazione.validazione_backref != None).filter(Registrazione.saldo != 0).order_by(Registrazione.data_contabile).all()
        registrazioni=eval("Registrazione.query.filter(Registrazione.validazione_backref != None).filter(Registrazione.saldo != 0)."+filtro+"order_by(Registrazione.data_contabile).all()")
        for r in riconciliazioni: 
            try:registrazioni.remove(r)
            except:pass
        return render_template('edit_cassa.html', registrazione=registrazione, form=form, upload_form=upload_form, partners=partners, ricevute=ricevute, voci=voci, registrazioni=registrazioni, dare=dare, avere=avere, allegati=allegati)
    else:
        movimenti = Movimento.query.join(Conto).join(Sottomastro).join(Mastro).filter(Movimento.registrazione==registrazione).order_by(Mastro.codice).order_by(Sottomastro.codice).order_by(Conto.codice).order_by(Movimento.id).all()
        dare,avere = 0,0
        riconciliazioni=[]
        for m in movimenti:
            if m.importo > 0: dare=dare+m.importo
            else: avere=avere-m.importo
            riconciliazioni.append(Riconciliazione.query.filter_by(validazione=validazione).filter_by(movimento=m).first())
        return render_template('cassa.html', registrazione=registrazione, movimenti=movimenti, dare=dare, avere=avere, riconciliazioni=riconciliazioni, registrazioni_generate=registrazioni_generate, allegati=allegati)

@app.route('/voce_cassa/<id>', methods=['GET', 'POST'])
@login_required
def voce_cassa(id):#edita la voce di cassa
    partners = Partner.query.order_by(Partner.nome).with_entities(Partner.nome).all()
    voce = Voce.query.get(id)
    conti = Conto.query.with_entities(Conto.nome).filter(Conto.nome!=voce.registrazione.registro.conto.nome).all()
    imposte = Imposta.query.all()
    form = VoceCassaForm()
    if form.validate_on_submit():
        voce.descrizione=form.descrizione.data
        voce.conto=Conto.query.filter_by(nome=form.conto.data).first()
        #voce.importo=form.dare.data-form.avere.data
        voce.importo=Decimal(form.dare.data-form.avere.data).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        voce.partner=Partner.query.filter_by(nome=form.partner.data).first()
        db.session.commit()
        flash('I dati sono stati salvati !')
        return redirect(url_for('registrazione', id=voce.registrazione.id))
    if form.is_submitted() and not form.validate():pass
    else:
        form.descrizione.data=voce.descrizione
        if voce.partner != None: form.partner.data=voce.partner.nome
        if voce.conto!=None:form.conto.data=voce.conto.nome
        if voce.importo>=0:
            form.dare.data=voce.importo
            form.avere.data=0.0
        else:
            form.dare.data=0.0
            form.avere.data=-voce.importo
    return render_template('voce_cassa.html', voce=voce, form=form, conti=conti, imposte=imposte, partners=partners)

@app.route('/registra_cassa/<id>')
@login_required
def registra_cassa(id):#registra la registrazione tipo cassa e genera le registrazioni accessorie
    registrazione=Registrazione.query.get(id)
    if not validate(registrazione):
        flash('ERRORE DI VALIDAZIONE !')
        return redirect(url_for('cassa', id=id))
    if registrazione.validazione_backref.first() == None:
        reg_cassa(registrazione)
        #ritenuta=[]
        ritenute=Ritenuta.query.all()
        for voce in registrazione.voce:
            if voce.registro != None:# verifica se devo generare una ricevuta verso partenr
                ricevuta=Registrazione(registro=voce.registro)
                db.session.add(ricevuta)
                ricevuta.partner=registrazione.partner
                ricevuta.data_contabile=registrazione.data_contabile
                ricevuta.data_decorrenza=registrazione.data_contabile
                ricevuta.data_scadenza=registrazione.data_contabile
                ricevuta.importo=0
                ricevuta.saldo=0
                ricevuta.descrizione="Generato da "+registrazione.nome
                vo=Voce(registrazione=ricevuta, importo=voce.registro.segno*voce.importo, quantita=1, conto=voce.registro.conto, descrizione=registrazione.descrizione)
                db.session.add(vo)
                ricevuta.validazione=registrazione.validazione_backref.first()
                reg_ricevuta(ricevuta)
            for ritenuta in ritenute:# verifica se una delle voci della registrazione fa riferimento ad una ritenuta d'acconto e nel caso genera la registrazione
                if voce.conto==ritenuta.conto_transito_ritenuta:
                    ritenuta_acconto=Registrazione(registro=ritenuta.registro_ritenuta)
                    db.session.add(ritenuta_acconto)
                    ritenuta_acconto.descrizione=voce.descrizione+" generata da "+str(registrazione.nome)
                    ritenuta_acconto.partner=Impostazioni.query.get(1).erario
                    ritenuta_acconto.data_contabile=registrazione.data_contabile
                    anno=registrazione.data_contabile.year
                    mese=registrazione.data_contabile.month + 1
                    data_scadenza=datetime.strptime("16/"+str(mese)+"/"+str(anno),"%d/%m/%Y").date()
                    ritenuta_acconto.data_scadenza=data_scadenza
                    ritenuta_acconto.importo=0
                    ritenuta_acconto.saldo=0
                    vo=Voce(registrazione=ritenuta_acconto, importo=-voce.importo, quantita=1, conto=voce.conto)
                    db.session.add(vo)
                    vo.descrizione="Transito RA"
                    ritenuta_acconto.validazione=registrazione.validazione_backref.first()
                    reg_fattura(ritenuta_acconto)
    return redirect(url_for('registrazioni', id=registrazione.registro.id))

def reg_cassa(registrazione):#registra la registrazione tipo cassa
    validazione=Validazione(registrazione=registrazione)
    db.session.add(validazione)
    anno=registrazione.data_contabile.year
    dal=datetime.strptime("01/01/"+str(anno),"%d/%m/%Y").date()
    al=datetime.strptime("31/12/"+str(anno),"%d/%m/%Y").date()
    i=1
    while Registrazione.query.filter_by(registro=registrazione.registro).filter(and_(Registrazione.data_contabile >= dal, Registrazione.data_contabile <= al)).filter_by(numero=i).first()!=None:
        i=i+1
    registrazione.numero=i
    registrazione.nome=registrazione.registro.codice+"/"+str(anno)[2:]+"/"+ str(i).zfill(4)
    reg_saldo=[]

    voci=registrazione.voce.order_by(Voce.id).all()
    for v in voci:
        movimento=Movimento(descrizione=v.descrizione, data_contabile=registrazione.data_contabile, importo=v.importo, conto=v.conto, partner=v.partner, registrazione=registrazione, validazione=validazione)
        db.session.add(movimento)
        if v.riconciliazione != None:
            riconciliazione=Riconciliazione(validazione=validazione, registrazione=v.riconciliazione, movimento=movimento)
            db.session.add(riconciliazione)
            reg_saldo.append(v.riconciliazione)
    datalog="Validata registrazione ["+registrazione.nome+"] importo["+str(registrazione.importo)+"] partner["+nome(registrazione.partner)+"] data contabile["+format_date(registrazione.data_contabile)+"] data registrazione["+format_date(registrazione.data_decorrenza)+"] data scadenza["+format_date(registrazione.data_scadenza)+"]"
    log = Log(datalog=datalog, user=current_user.username, timestamp = func.now())
    db.session.add(log)
    db.session.commit()
    saldo(reg_saldo)
# C A S S A #########################################################################



# R I C E V U T A #########################################################################
@app.route('/ricevuta/<id>', methods=['GET', 'POST'])
@login_required
def ricevuta(id):#visualizza o modifica la ricevuta
    partners = Partner.query.order_by(Partner.nome).with_entities(Partner.nome).all()
    registrazione=Registrazione.query.get(id)
    allegati=registrazione.allegato.order_by(Allegato.id).all()
    voci=registrazione.voce.order_by(Voce.id).all()
    totale=0
    for v in voci:
        totale+=v.importo
    if registrazione.validazione_backref.first() == None:
        registrazione.importo=totale*registrazione.registro.segno
        db.session.commit()
        form = FatturaForm()
        upload_form = UploadForm()
        if upload_form.submit2.data and upload_form.validate():
            allegato=Allegato(registrazione=registrazione, nome=upload_form.file.data.filename, binario=upload_form.file.data.read())
            db.session.add(allegato)
            db.session.commit()
            return redirect(url_for('ricevuta', id=id))
        if form.submit.data and form.validate():
            registrazione.descrizione=form.descrizione.data
            registrazione.data_contabile=form.data_contabile.data
            registrazione.data_decorrenza=form.data_decorrenza.data
            registrazione.data_scadenza=form.data_scadenza.data
            current_user.data_decorrenza=form.data_decorrenza.data
            current_user.data_scadenza=form.data_scadenza.data
            registrazione.note=form.note.data
            registrazione.partner=Partner.query.filter_by(nome=form.partner.data).first()
            db.session.commit()
            flash('I dati sono stati salvati !')
        if form.is_submitted() and not form.validate():pass
        else:
            form.descrizione.data=registrazione.descrizione
            form.data_contabile.data=registrazione.data_contabile
            form.data_decorrenza.data=registrazione.data_decorrenza
            form.data_scadenza.data=registrazione.data_scadenza
            form.note.data=registrazione.note
            if registrazione.partner != None: form.partner.data=registrazione.partner.nome
        registrazioni=Registrazione.query.filter_by(partner=registrazione.partner).filter(Registrazione.validazione_backref != None).filter(Registrazione.saldo != 0).order_by(Registrazione.data_contabile).all()
        return render_template('edit_ricevuta.html', registrazione=registrazione, form=form, upload_form=upload_form, partners=partners, registrazioni=registrazioni, voci=voci, allegati=allegati)
    else:
        validazione=registrazione.validazione_backref.first()
        movimenti = Movimento.query.filter_by(registrazione=registrazione).order_by(Movimento.id).all()
        dare,avere = 0,0
        for m in movimenti:
            if m.importo > 0: dare=dare+m.importo
            else: avere=avere-m.importo
        riconciliazioni=Riconciliazione.query.filter_by(registrazione=registrazione).filter(Riconciliazione.validazione!=validazione).order_by(Riconciliazione.id).all()
        return render_template('ricevuta.html', registrazione=registrazione, voci=voci, totale=totale, movimenti=movimenti, dare=dare, avere=avere, riconciliazioni=riconciliazioni, Validazione=Validazione, allegati=allegati)

@app.route('/voce_ricevuta/<id>', methods=['GET', 'POST'])
@login_required
def voce_ricevuta(id):#modifica la voce della ricevuta
    conti = Conto.query.all()
    voce = Voce.query.get(id)
    form = VoceRicevutaForm()
    if voce.registrazione.validazione_backref.first() == None:
        if form.validate_on_submit():
            voce.descrizione=form.descrizione.data
            voce.conto=Conto.query.filter_by(nome=form.conto.data).first()
            voce.importo=form.importo.data
            db.session.commit()
            flash('I dati sono stati salvati !')
            return redirect(url_for('registrazione', id=voce.registrazione.id))
        if form.is_submitted() and not form.validate():pass
        else:
            form.descrizione.data=voce.descrizione
            if voce.conto!=None:form.conto.data=voce.conto.nome
            form.importo.data=voce.importo
    return render_template('voce_ricevuta.html', voce=voce, form=form, conti=conti)

@app.route('/registra_ricevuta/<id>')
@login_required#registra la ricevuta
def registra_ricevuta(id):
    registrazione=Registrazione.query.get(id)
    if registrazione.validazione_backref.first() == None:
        reg_ricevuta(registrazione)
    return redirect(url_for('ricevuta', id=id))

@app.route('/aggiungi_ricevuta/<id>', methods=['GET', 'POST'])
@login_required
def aggiungi_ricevuta(id):#aggiunge una ricevuta
    registro_id = request.args.get('registro_id')
    registro=Registro.query.get(registro_id)
    registrazione=Registrazione.query.get(id)
    importo=0
    for v in registrazione.voce:
        importo+=v.importo
    voce=Voce(registrazione=registrazione, conto=registro.conto, importo=-importo, quantita=1, registro=registro, descrizione=registrazione.descrizione)
    db.session.add(voce)
    db.session.commit()
    return redirect(url_for('registrazione', id=id))
# R I C E V U T A #########################################################################



# F A T T U R A #########################################################################
@app.route('/fattura/<id>', methods=['GET', 'POST'])
@login_required
def fattura(id):#visualizza o edita la fattura 
    #partners = Partner.query.order_by(Partner.nome).with_entities(Partner.nome).all()
    #domiciliatari = Domicilio.query.filter(Domicilio.partner==.nome).with_entities(Partner.nome).all()
    registrazione=Registrazione.query.get(id)
    note=registrazione.note
    if note!=None:causale=note.split("\r\n")
    else:causale=[]
    if registrazione.numero!=None:
        registrazione_successiva=Registrazione.query.filter(Registrazione.registro==registrazione.registro).filter(Registrazione.nome>registrazione.nome).order_by(Registrazione.nome).first()
        registrazione_precedente=Registrazione.query.filter(Registrazione.registro==registrazione.registro).filter(Registrazione.nome<registrazione.nome).order_by(Registrazione.nome.desc()).first()
    registrazioni_generate=Registrazione.query.filter_by(validazione=registrazione.validazione_backref.first()).all()
    allegati=registrazione.allegato.order_by(Allegato.id).all()
    voci=registrazione.voce.order_by(Voce.id).all()
    totale=0
    imposta=[]
    tot_imponibile=0
    tot_imposta=0

    voci_iva=Voce_iva.query.filter(Voce_iva.registrazione==registrazione).all()
    for voce in voci_iva:
        tot_imponibile+=voce.imponibile
        tot_imposta+=voce.iva
    totale=tot_imponibile+tot_imposta
    
    tot_ritenuta=0
    tot_imponibile_rit=0
    tot_ritenuta=0
    voci_ritenuta=Voce_ritenuta.query.filter(Voce_ritenuta.registrazione==registrazione).all()
    for voce in voci_ritenuta:
        tot_imponibile_rit+=voce.imponibile
        tot_ritenuta+=voce.ra
    totale_pagare=totale-tot_ritenuta

    if registrazione.validazione_backref.first() == None:
        registrazione.importo=totale*registrazione.registro.segno
        db.session.commit()
        form = FatturaForm()
        upload_form = UploadForm()
        if upload_form.submit2.data and upload_form.validate():
            nome=upload_form.file.data.filename
            allegato=Allegato(registrazione=registrazione, nome=nome, binario=upload_form.file.data.read())
            db.session.add(allegato)
            db.session.commit()
            return redirect(url_for('fattura', id=id))
        voci=registrazione.voce.order_by(Voce.id).all()
        domiciliatario=None
        if registrazione.partner!=None and registrazione.partner.amministratore!=None: domiciliatario=registrazione.partner.amministratore
        if registrazione.letturista: domiciliatario=registrazione.partner.letturista
        return render_template('edit_fattura.html', registrazione=registrazione, form=form, upload_form=upload_form, voci=voci, voci_iva=voci_iva, voci_ritenuta=voci_ritenuta, tot_imponibile=tot_imponibile, tot_imposta=tot_imposta, totale=totale, tot_imponibile_rit=tot_imponibile_rit, tot_ritenuta=tot_ritenuta, totale_pagare=totale_pagare, allegati=allegati, domiciliatario=domiciliatario, causale=causale)
    else:
        validazione=registrazione.validazione_backref.first()
        movimenti = Movimento.query.filter_by(registrazione=registrazione).order_by(Movimento.id).all()
        dare,avere = 0,0
        for m in movimenti:
            if m.importo > 0: dare=dare+m.importo
            else: avere=avere-m.importo
        riconciliazioni=Riconciliazione.query.filter_by(registrazione=registrazione).filter(Riconciliazione.validazione!=validazione).order_by(Riconciliazione.id).all()
        voci=registrazione.voce.order_by(Voce.id).all()
        domiciliatario=None
        if registrazione.partner!=None and registrazione.partner.amministratore!=None: domiciliatario=registrazione.partner.amministratore
        if registrazione.letturista: domiciliatario=registrazione.partner.letturista
        return render_template('fattura.html', registrazione=registrazione, voci=voci, voci_iva=voci_iva, voci_ritenuta=voci_ritenuta, tot_imponibile=tot_imponibile, tot_imposta=tot_imposta, totale=totale, tot_imponibile_rit=tot_imponibile_rit, tot_ritenuta=tot_ritenuta, totale_pagare=totale_pagare, movimenti=movimenti, dare=dare, avere=avere, riconciliazioni=riconciliazioni, Validazione=Validazione, registrazioni_generate=registrazioni_generate, allegati=allegati, registrazione_successiva=registrazione_successiva, registrazione_precedente=registrazione_precedente, domiciliatario=domiciliatario, causale=causale)

@app.route('/cambia_conto/<id>', methods=['GET', 'POST'])
@login_required
def cambia_conto(id):#modifica il conto per le voce della fattura
    conti = Conto.query.all()
    voce = Voce.query.get(id)
    vecchioconto = voce.conto
    form = CambiaContoForm()
    if form.validate_on_submit():
        voce.conto=Conto.query.filter_by(nome=form.conto.data).first()
        print(-voce.importo*voce.registrazione.registro.segno*voce.quantita,type(-voce.importo*voce.registrazione.registro.segno*voce.quantita))
        movimento=Movimento.query.filter_by(registrazione=voce.registrazione).filter_by(importo=-voce.importo*voce.registrazione.registro.segno*voce.quantita).first()
        movimento.conto=voce.conto
        db.session.commit()
        flash('I dati sono stati salvati !')
        return redirect(url_for('registrazione', id=voce.registrazione.id))
    if form.is_submitted() and not form.validate():pass
    else:
        if voce.conto!=None:form.conto.data=voce.conto.nome
    return render_template('cambia_conto.html', voce=voce, form=form, conti=conti)

@app.route('/voce_fattura/<id>', methods=['GET', 'POST'])
@login_required
def voce_fattura(id):#edita la voce fattura
    conti = Conto.query.all()
    imposte = Imposta.query.order_by(Imposta.posizione).all()
    ritenute = Ritenuta.query.all()
    voce = Voce.query.get(id)
    form = VoceFatturaForm()
    if voce.registrazione.validazione_backref.first() == None:
        if form.validate_on_submit():
            voce.descrizione=form.descrizione.data
            voce.conto=Conto.query.filter_by(nome=form.conto.data).first()
            voce.quantita=Decimal(form.quantita.data).quantize(Decimal('.00001'), rounding=ROUND_HALF_UP)
            voce.importo=Decimal(form.importo.data).quantize(Decimal('.00001'), rounding=ROUND_HALF_UP)
            voce.imposta=Imposta.query.filter_by(nome=form.imposta.data).first()
            voce.ritenuta=Ritenuta.query.filter_by(nome=form.ritenuta.data).first()
            voce.esercizio_precedente=form.esercizio_precedente.data
            db.session.commit()
            calcola_iva_ritenute(voce.registrazione)
            flash('I dati sono stati salvati !')
            return redirect(url_for('registrazione', id=voce.registrazione.id))
        if form.is_submitted() and not form.validate():pass
        else:
            form.descrizione.data=voce.descrizione
            if voce.conto!=None:form.conto.data=voce.conto.nome
            form.quantita.data=voce.quantita
            form.importo.data=voce.importo
            if voce.imposta!=None:form.imposta.data=voce.imposta.nome
            if voce.ritenuta!=None:form.ritenuta.data=voce.ritenuta.nome
            form.esercizio_precedente.data=voce.esercizio_precedente
    return render_template('voce_fattura.html', voce=voce, form=form, conti=conti, imposte=imposte, ritenute=ritenute)

@app.route('/registra_fattura/<id>', methods=['GET', 'POST'])
@login_required
def registra_fattura(id):#registra la fattura e genera le registrazioni accessorie
    registrazione=Registrazione.query.get(id)
    impostazioni=Impostazioni.query.get(1)
    if not validate_fattura(registrazione):
        flash('ERRORE DI VALIDAZIONE !')
        return redirect(url_for('fattura', id=id))
    if registrazione.validazione_backref.first() == None:
        reg_fattura(registrazione)
        voci=registrazione.voce.order_by(Voce.id).all()
        for v in voci:#genera le registrazioni per le Fatture da ricevere e da emettere
            #imponibile[imposta.index(v.imposta)]+=dec(v.importo*v.quantita)
            anno=registrazione.data_contabile.year
            if v.esercizio_precedente:
                fine_esercizio_anno=datetime.strptime(impostazioni.ultimo_giorno_esercizio+"/"+str(anno),"%d/%m/%Y").date()
                #if registrazione.data_contabile >= datetime.strptime("01/10/"+str(anno),"%d/%m/%Y").date():
                if registrazione.data_contabile > fine_esercizio_anno:
                    #data_precedente=datetime.strptime("30/09/"+str(anno),"%d/%m/%Y").date()
                    data_precedente=fine_esercizio_anno
                    #data_successivo=datetime.strptime("01/10/"+str(anno+1),"%d/%m/%Y").date()
                    #data_successivo=data_precedente+relativedelta(days=1)+relativedelta(years=1)
                else:
                    data_precedente=fine_esercizio_anno-relativedelta(years=1)
                    #data_precedente=datetime.strptime(impostazioni.ultimo_giorno_esercizio+str(anno-1),"%d/%m/%Y").date()
                    #data_precedente=datetime.strptime("30/09/"+str(anno-1),"%d/%m/%Y").date()
                    #data_successivo=datetime.strptime("01/10/"+str(anno),"%d/%m/%Y").date()
                    #data_successivo=data_precedente+relativedelta(days=1)+relativedelta(years=1)
                data_successivo=data_precedente+relativedelta(days=1)+relativedelta(years=1)
                misc=Registrazione(registro=impostazioni.registro_misc)
                db.session.add(misc)
                misc.partner=registrazione.partner
                misc.data_contabile=data_precedente
                misc.descrizione="Generato da "+registrazione.nome
                voce=Voce(registrazione=misc, descrizione=v.descrizione, conto=registrazione.registro.conto_precedente, importo=dec(v.importo*v.quantita*registrazione.registro.segno), partner=registrazione.partner)
                db.session.add(voce)
                voce=Voce(registrazione=misc, descrizione=v.descrizione, conto=v.conto, importo=dec(-v.importo*v.quantita*registrazione.registro.segno), partner=registrazione.partner)
                db.session.add(voce)
                misc.validazione=registrazione.validazione_backref.first()
                reg_cassa(misc)
        for voce_iva in registrazione.voce_iva:
            #iva[j]=dec(imponibile[j]*imposta[j].aliquota/100)
            #if voce_iva.imposta.natura!=None and voce_iva.imposta.natura[:2]=="N6" and voce_iva.imposta.registro_autofattura_rc!=None:#genera le registrazione per il reverse charge acquisto
            if voce_iva.imposta.rc:#genera le registrazione per il reverse charge acquisto
                autofattura=Registrazione(registro=impostazioni.registro_autofattura_rc)
                db.session.add(autofattura)
                autofattura.descrizione="FT RC generata da "+str(registrazione.nome)+" N. "+registrazione.numero_origine+" "+registrazione.partner.nome
                #autofattura.partner=registrazione.partner
                autofattura.partner=impostazioni.azienda
                autofattura.data_contabile=registrazione.data_contabile
                autofattura.data_decorrenza=registrazione.data_decorrenza
                voce=Voce(registrazione=autofattura, importo=voce_iva.imponibile, quantita=1, imposta=voce_iva.imposta, conto=impostazioni.registro_riconciliazione_rc.conto)
                db.session.add(voce)
                voce.descrizione="Transito RC"
                autofattura.validazione=registrazione.validazione_backref.first()
                calcola_iva_ritenute(autofattura)
                reg_fattura(autofattura)
                ricrc=Registrazione(registro=impostazioni.registro_riconciliazione_rc)
                db.session.add(ricrc)
                ricrc.descrizione="Ric. RC generata da "+str(registrazione.nome)+" N. "+registrazione.numero_origine+" "+registrazione.partner.nome
                #ricrc.partner=registrazione.partner
                ricrc.partner=impostazioni.azienda
                ricrc.data_contabile=registrazione.data_contabile
                riconciliazione=autofattura
                voce=Voce(registrazione=ricrc, descrizione=riconciliazione.descrizione, conto=riconciliazione.registro.conto, partner=riconciliazione.partner, importo=-(voce_iva.imponibile+voce_iva.iva), riconciliazione=riconciliazione)
                db.session.add(voce)
                riconciliazione=registrazione
                voce=Voce(registrazione=ricrc, descrizione="Riconciliazione RC", conto=riconciliazione.registro.conto, partner=riconciliazione.partner, importo=voce_iva.iva, riconciliazione=riconciliazione)
                db.session.add(voce)
                voce=Voce(registrazione=ricrc, descrizione="Riconciliazione RC", conto=ricrc.registro.conto, importo=voce_iva.imponibile, partner=impostazioni.azienda)
                db.session.add(voce)
                ricrc.validazione=registrazione.validazione_backref.first()
                reg_cassa(ricrc)
            if voce_iva.imposta.esigibilita=="S":#genera le registrazioni per lo split payment
                ricsp=Registrazione(registro=impostazioni.registro_riconciliazione_sp)
                db.session.add(ricsp)
                ricsp.descrizione="Ric. SP generata da "+str(registrazione.nome)+" "+registrazione.partner.nome
                ricsp.partner=registrazione.partner
                ricsp.data_contabile=registrazione.data_contabile
                riconciliazione=registrazione
                voce=Voce(registrazione=ricsp, descrizione="Giroconto IVA SP", conto=riconciliazione.registro.conto, partner=riconciliazione.partner, importo=-voce_iva.iva, riconciliazione=riconciliazione)
                db.session.add(voce)
                voce=Voce(registrazione=ricsp, descrizione="Giroconto IVA SP", conto=riconciliazione.registro.conto_iva, importo=voce_iva.iva)
                db.session.add(voce)
                ricsp.validazione=registrazione.validazione_backref.first()
                reg_cassa(ricsp)
        #if registrazione.registro==Impostazioni.query.get(1).registro.fatc:#se è fattura verso cliente
        if registrazione.registro.tipo_documento!=None:#prepara la fattura elettronica allegando il file xml e impostando alcuni campi
            registrazione.tipo_documento=registrazione.registro.tipo_documento#imposta il valore di default per il tipo di documento, in futuro prevedere scelta multipla, serve per la fattura elettronica
            nome=(registrazione.nome+".pdf").replace("/","_")
            filename=os.path.join(here,nome)
            for a in registrazione.allegato:
                if a.nome==nome:db.session.delete(a)
            for s in registrazione.sdi:
                if s.timestamp==None:db.session.delete(s)
            Stampa_fattura(registrazione, filename)
            with open(filename, 'rb') as bites:
                dati=io.BytesIO(bites.read())
            allegato=Allegato(registrazione=registrazione, nome=nome, binario=dati.read())
            db.session.add(allegato)
            os.remove(filename)

            progressivo=b62(impostazioni.sequenziale_sdi)
            azienda=impostazioni.azienda
            impostazioni.sequenziale_sdi+=1
            db.session.commit()

            nome="IT"+azienda.cf+"_"+progressivo+".xml"
            filename=os.path.join(here,nome)

            sdi=Sdi(nome=nome, inbox=False, fattura=True, registrazione=registrazione)
            db.session.add(sdi)

            genera_xml_fattura(registrazione, filename, progressivo)
            with open(filename, 'rb') as bites:
                dati=io.BytesIO(bites.read())
            allegato=Allegato(sdi=sdi, nome=nome, binario=dati.read())
            db.session.add(allegato)
            os.remove(filename)
            
            if registrazione.partner.amministratore!=None: registrazione.domiciliatario=registrazione.partner.amministratore
            if registrazione.letturista: registrazione.domiciliatario=registrazione.partner.letturista
        db.session.commit()
    return redirect(url_for('fattura', id=id))

@app.route('/edit_top_fattura/<id>', methods=['GET', 'POST'])
@login_required
def edit_top_fattura(id):#modifica la parte relativa al partner, date ecc
    registrazione=Registrazione.query.get(id)
    form = FatturaForm()
    partners = Partner.query.order_by(Partner.nome).with_entities(Partner.nome).all()
    if registrazione.validazione_backref.first() == None:
        if form.submit.data and form.validate():
            registrazione.descrizione=form.descrizione.data
            registrazione.numero_origine=form.numero_origine.data
            registrazione.data_contabile=form.data_contabile.data
            registrazione.data_decorrenza=form.data_decorrenza.data
            registrazione.data_scadenza=form.data_scadenza.data
            #registrazione.lav_autonomo=form.lav_autonomo.data
            current_user.data_decorrenza=form.data_decorrenza.data
            current_user.data_scadenza=form.data_scadenza.data
            registrazione.partner=Partner.query.filter_by(nome=form.partner.data).first()
            registrazione.lav_autonomo=registrazione.partner.lav_autonomo
            db.session.commit()
            flash('I dati sono stati salvati !')
            return redirect(url_for('registrazione', id=registrazione.id))
        if form.is_submitted() and not form.validate():pass
        else:
            form.descrizione.data=registrazione.descrizione
            form.numero_origine.data=registrazione.numero_origine
            form.data_contabile.data=registrazione.data_contabile
            form.data_decorrenza.data=registrazione.data_decorrenza
            form.data_scadenza.data=registrazione.data_scadenza
            form.lav_autonomo.data=registrazione.lav_autonomo
            if registrazione.partner != None: form.partner.data=registrazione.partner.nome
        return render_template('edit_top_fattura.html', form=form, partners=partners)
    else: return redirect(url_for('fattura', id=id))

@app.route('/edit_top_fattura1/<id>', methods=['GET', 'POST'])
@login_required
def edit_top_fattura1(id):#modifica la parte relativa al domiciliatario, condizioni di pagamento e causale
    registrazione=Registrazione.query.get(id)
    form = FatturaForm1()
    #domicili = Domicilio.query.filter(Domicilio.partner==registrazione.partner).all()
    pagamenti = Pagamento.query.order_by(Pagamento.posizione).all()
    if registrazione.validazione_backref.first() == None:
        if form.submit.data and form.validate():
            #registrazione.domiciliatario=Partner.query.filter_by(nome=form.domiciliatario.data).first()
            registrazione.letturista=form.letturista.data
            registrazione.note=form.note.data
            registrazione.pagamento=Pagamento.query.filter_by(nome=form.pagamento.data).first()
            db.session.commit()
            flash('I dati sono stati salvati !')
            return redirect(url_for('registrazione', id=registrazione.id))
        if form.is_submitted() and not form.validate():pass
        else:
            #if registrazione.domiciliatario != None: form.domiciliatario.data=registrazione.domiciliatario.nome
            form.letturista.data=registrazione.letturista
            form.note.data=registrazione.note
            if registrazione.pagamento != None: form.pagamento.data=registrazione.pagamento.nome
        return render_template('edit_top_fattura1.html', form=form, pagamenti=pagamenti)
    else: return redirect(url_for('fattura', id=id))

def Stampa_fattura(fattura, filename):#genera il pdf della fattura
    voci=fattura.voce.order_by(Voce.id).all()
    totale=0
    importo_pagamento=0
    imposta=[]
    tot_imponibile=0
    tot_imposta=0
    tot_imposta_S=0

    voci_iva=Voce_iva.query.filter(Voce_iva.registrazione==fattura).all()
    for voce in voci_iva:
        tot_imponibile+=voce.imponibile
        tot_imposta+=voce.iva
        if voce.imposta.esigibilita=="S":tot_imposta_S+=voce.iva
    totale=tot_imponibile+tot_imposta
    importo_pagamento=totale-tot_imposta_S

    tab=[[40,"l"],[340,"r"],[410,"r"],[480,"r"],[550,"r"],[350,"l"],[250,"r"]]
    des=["Descrizione","Quantità","Prezzo €","Imposta","Importo €"]
    azienda=Impostazioni.query.get(1).azienda
    footer=azienda.nome+" - "+azienda.indirizzo+" - "+azienda.cap+" "+azienda.citta+" - P.IVA "+azienda.iva+" - CF "+azienda.cf
    footer2="IBAN: "+azienda.iban+" - Email: "+azienda.email+" - Tel: "+azienda.telefono+" - Fax: "+azienda.fax
    can=document(filename, pagesize=A4, tab=tab, des=des, footer=footer, footer2=footer2)
    can.drawImage(os.path.join(here, 'logo.png'), 40, 700, 100, 100)#1 punto sono circa 0.35 mm
    can.writemediumbold(5,"Destinatario")
    can.newline()
    can.writemedium(5,fattura.partner.nome)
    can.newline()
    can.writemedium(5,fattura.partner.indirizzo)
    can.newline()
    can.writemedium(5,fattura.partner.cap+" "+fattura.partner.citta)
    if fattura.partner.cf!=None:
        can.newline()
        can.writemedium(5,"CF: "+fattura.partner.cf)
    if fattura.partner.iva!=None:
        can.newline()
        can.writemedium(5,"P.IVA: "+fattura.partner.iva)
    domiciliatario=None
    if fattura.partner.amministratore!=None: domiciliatario=fattura.partner.amministratore
    if fattura.letturista: domiciliatario=fattura.partner.letturista
    if domiciliatario!=None:
        can.newline()
        can.newline()
        can.writemediumbold(5,"Domiciliatario")
        can.newline()
        can.writemedium(5,domiciliatario.nome)
        can.newline()
        can.writemedium(5,domiciliatario.indirizzo)
        can.newline()
        can.writemedium(5,domiciliatario.cap+" "+domiciliatario.citta)
        # if fattura.domiciliatario.cf!=None:
            # can.newline()
            # can.writemedium(5,"CF: "+fattura.domiciliatario.cf)
        # if fattura.domiciliatario.iva!=None:
            # can.newline()
            # can.writemedium(5,"PIVA: "+fattura.domiciliatario.iva)
    else:
        can.newline()
        can.newline()
        can.newline()
        can.newline()
    can.newline()
    can.newline()
    can.writemediumbold(0,fattura.tipo_documento.descrizione)
    can.writemediumbold(6,str(fattura.nome))
    can.newline()
    can.newline()
    can.writemedium(0,"Data di emissione:")
    can.writemedium(6,fattura.data_decorrenza.strftime("%d/%m/%Y"))
    can.newline()
    can.writemedium(0,"Data di scadenza:")
    can.writemedium(6,fattura.data_scadenza.strftime("%d/%m/%Y"))
    can.newline()
    can.newline()

    ##print (stringWidth(fattura.descrizione, "Times-Roman", 10))
    #lines = simpleSplit(fattura.descrizione, "Times-Roman", 10, 495)
    #for i in range(len(lines)):
    #    if i!=0:can.newline()
    #    can.write(0,lines[i])
    #can.newline()

    can.write(0,fattura.descrizione)
    can.newline()
    if fattura.note!=None:
        note=fattura.note.split("\r\n")
        for n in note:
            can.write(0,n)
            can.newline()

    #can.drawline()
    can.newline()
    for i in [0,1,2,3,4]:
        can.writebold(i,des[i])
    can.newline()
    can.drawline()
    for voce in voci:
        #can.newline()
        can.newline()
        can.write(1,valutalong(voce.quantita))
        can.write(2,valutalong(voce.importo))
        lines_imposta = simpleSplit(voce.imposta.nome, "Times-Roman", 10, 60)
        #can.write(3,voce.imposta.nome)
        can.write(4,valuta(voce.quantita*voce.importo))
        #print (stringWidth(voce.descrizione, "Times-Roman", 12))
        lines_descrizione = simpleSplit(voce.descrizione, "Times-Roman", 10, 250)
        for i in range(max(len(lines_imposta),len(lines_descrizione))):
            if i!=0:can.newline()
            try:can.write(0,lines_descrizione[i])
            except:pass
            try:can.write(3,lines_imposta[i])
            except:pass
    can.newline()
    can.newline()
    #can.drawline()
    can.newline()
    can.writebold(2,"Imponibile €")
    can.writebold(3,"Imposta")
    can.writebold(4,"Importo €")
    can.newline()
    can.drawhalflineright()
    for voce in voci_iva:
        #can.newline()
        can.newline()
        can.write(2,valuta(voce.imponibile))
        #can.write(3,voce.imposta.nome)
        lines_imposta = simpleSplit(voce.imposta.nome, "Times-Roman", 10, 60)
        can.write(4,valuta(voce.iva))
        for i in range(len(lines_imposta)):
            if i!=0:can.newline()
            can.write(3,lines_imposta[i])

    can.newline()
    can.newline()
    can.newline()
    can.writemedium(3,"Totale imponibile €")
    can.writemedium(4,valuta(tot_imponibile))
    can.newline()
    can.newline()
    can.writemedium(3,"Totale imposte €")
    can.writemedium(4,valuta(tot_imposta))
    can.newline()
    can.newline()
    can.writemediumbold(3,"Totale €")
    can.writemediumbold(4,valuta(totale))
    can.newline()
    can.newline()
    if importo_pagamento!=totale:
        can.writemediumbold(3,"Totale da pagare €")
        can.writemediumbold(4,valuta(importo_pagamento))
        can.newline()
        can.newline()
    if fattura.pagamento!=None:can.writemedium(0,"Metodo di pagamento: "+fattura.pagamento.nome)
    can.newline()
    can.newline()
    testo="Il presente documento è la copia della fattura elettronica trasmessa attraverso il Sistema di Interscambio e disponibile nella Vostra area riservata del sito web dell'Agenzia delle Entrate."
    lines = simpleSplit(testo, "Times-Roman", 10, 495)
    for i in range(len(lines)):
        if i!=0:can.newline()
        can.write(0,lines[i])
    can.save()

@app.route('/edit_voce_iva/<id>', methods=['GET', 'POST'])
@login_required
def edit_voce_iva(id):#modifica la voce IVA. Serve quando a causa degli arrotondamenti nelle fatture acquisto l'IVA non torna
    voce_iva=Voce_iva.query.get(id)
    form = EditIVAForm()
    if form.validate_on_submit():
        #voce_iva.iva = form.iva.data
        voce_iva.iva=Decimal(form.iva.data).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        db.session.commit()
        flash('I dati sono stati salvati !')
        return redirect(url_for('registrazione', id=voce_iva.registrazione.id))
    form.iva.data=voce_iva.iva
    return render_template('edit_voce_iva.html', form=form)

def calcola_iva_ritenute(registrazione):#calcola l'IVA e le ritenute per la fattura
    for voce in registrazione.voce_iva:db.session.delete(voce)
    for voce in registrazione.voce_ritenuta:db.session.delete(voce)
    db.session.commit()

    voci=registrazione.voce.order_by(Voce.id).all()

    imposta=[]
    for v in voci:
        if v.imposta not in imposta: imposta.append(v.imposta)
    imponibile=[0]*len(imposta)
    for v in voci:
        imponibile[imposta.index(v.imposta)]+=dec(v.importo*v.quantita)
    for i in range(len(imposta)):
        voce_iva=Voce_iva(registrazione=registrazione,imposta=imposta[i],imponibile=imponibile[i],iva=dec(imponibile[i]*imposta[i].aliquota/100))
        db.session.add(voce_iva)
    db.session.commit()

    rit=[]
    for v in voci:
        if v.ritenuta!= None and v.ritenuta not in rit: rit.append(v.ritenuta)
    imponibile=[0]*len(rit)
    for v in voci:
        if v.ritenuta!= None: imponibile[rit.index(v.ritenuta)]+=dec(v.importo*v.quantita)
    #print(rit)
    #print(len(rit))
    for i in range(len(rit)):
        voce_ritenuta=Voce_ritenuta(registrazione=registrazione,ritenuta=rit[i],imponibile=imponibile[i],ra=dec(imponibile[i]*rit[i].aliquota/100))
        db.session.add(voce_ritenuta)
    db.session.commit()

def genera_xml_fattura(fattura, filename, progressivo):#genera il file xml della fattura elettronica
    azienda=Impostazioni.query.get(1).azienda

    partner=fattura.partner
    voci=fattura.voce.order_by(Voce.id).all()
    totale=0
    imposta=[]
    tot_imponibile=0
    tot_imposta=0
    tot_imposta_S=0

    voci_iva=Voce_iva.query.filter(Voce_iva.registrazione==fattura).all()
    for voce in voci_iva:
        tot_imponibile+=voce.imponibile
        tot_imposta+=voce.iva
        if voce.imposta.esigibilita=="S":tot_imposta_S+=voce.iva
    totale=tot_imponibile+tot_imposta
    importo_pagamento=totale-tot_imposta_S

    FatturaElettronica = etree.Element('FatturaElettronica')
    FatturaElettronicaHeader = etree.SubElement(FatturaElettronica, "FatturaElettronicaHeader")
    DatiTrasmissione = etree.SubElement(FatturaElettronicaHeader, "DatiTrasmissione")
    IdTrasmittente = etree.SubElement(DatiTrasmissione, "IdTrasmittente")

    etree.SubElement(IdTrasmittente, "IdPaese").text = "IT"
    etree.SubElement(IdTrasmittente, "IdCodice").text = azienda.cf
    etree.SubElement(DatiTrasmissione, "ProgressivoInvio").text = progressivo
    if partner.pa:etree.SubElement(DatiTrasmissione, "FormatoTrasmissione").text = "FPA12"
    else:etree.SubElement(DatiTrasmissione, "FormatoTrasmissione").text = "FPR12"
    if fattura.partner.amministratore!=None: etree.SubElement(DatiTrasmissione, "CodiceDestinatario").text = partner.amministratore.codice_destinatario
    else: etree.SubElement(DatiTrasmissione, "CodiceDestinatario").text = partner.codice_destinatario

    CedentePrestatore = etree.SubElement(FatturaElettronicaHeader, "CedentePrestatore")
    DatiAnagraficiCedente = etree.SubElement(CedentePrestatore, "DatiAnagrafici")
    IdFiscaleIVACedente = etree.SubElement(DatiAnagraficiCedente, "IdFiscaleIVA")
    etree.SubElement(IdFiscaleIVACedente, "IdPaese").text = "IT"
    etree.SubElement(IdFiscaleIVACedente, "IdCodice").text = azienda.iva[2:]
    etree.SubElement(DatiAnagraficiCedente, "CodiceFiscale").text = azienda.cf
    AnagraficaCedente = etree.SubElement(DatiAnagraficiCedente, "Anagrafica")
    etree.SubElement(AnagraficaCedente, "Denominazione").text = azienda.nome
    etree.SubElement(DatiAnagraficiCedente, "RegimeFiscale").text = azienda.regime_fiscale

    Sede = etree.SubElement(CedentePrestatore, "Sede")
    etree.SubElement(Sede, "Indirizzo").text = azienda.indirizzo
    etree.SubElement(Sede, "CAP").text = azienda.cap
    etree.SubElement(Sede, "Comune").text = azienda.citta
    etree.SubElement(Sede, "Provincia").text = azienda.provincia
    etree.SubElement(Sede, "Nazione").text = "IT"

    IscrizioneREA = etree.SubElement(CedentePrestatore, "IscrizioneREA")
    etree.SubElement(IscrizioneREA, "Ufficio").text = azienda.rea_ufficio
    etree.SubElement(IscrizioneREA, "NumeroREA").text = azienda.rea_codice
    etree.SubElement(IscrizioneREA, "StatoLiquidazione").text = azienda.rea_stato_liquidatione

    CessionarioCommittente = etree.SubElement(FatturaElettronicaHeader, "CessionarioCommittente")
    DatiAnagraficiCessionario = etree.SubElement(CessionarioCommittente, "DatiAnagrafici")
    if partner.iva!=None and partner.iva!="":
        IdFiscaleIVA = etree.SubElement(DatiAnagraficiCessionario, "IdFiscaleIVA")
        etree.SubElement(IdFiscaleIVA, "IdPaese").text = "IT"
        etree.SubElement(IdFiscaleIVA, "IdCodice").text = partner.iva[2:]
    if partner.cf!=None and partner.cf!="":
        etree.SubElement(DatiAnagraficiCessionario, "CodiceFiscale").text = partner.cf
    AnagraficaCessionario = etree.SubElement(DatiAnagraficiCessionario, "Anagrafica")
    etree.SubElement(AnagraficaCessionario, "Denominazione").text = partner.nome

    Sede = etree.SubElement(CessionarioCommittente, "Sede")
    etree.SubElement(Sede, "Indirizzo").text = partner.indirizzo
    etree.SubElement(Sede, "CAP").text = partner.cap
    etree.SubElement(Sede, "Comune").text = partner.citta
    etree.SubElement(Sede, "Provincia").text = partner.provincia
    etree.SubElement(Sede, "Nazione").text = "IT"

    FatturaElettronicaBody = etree.SubElement(FatturaElettronica, "FatturaElettronicaBody")
    DatiGenerali = etree.SubElement(FatturaElettronicaBody, "DatiGenerali")
    DatiGeneraliDocumento = etree.SubElement(DatiGenerali, "DatiGeneraliDocumento")
    etree.SubElement(DatiGeneraliDocumento, "TipoDocumento").text = fattura.tipo_documento.codice
    etree.SubElement(DatiGeneraliDocumento, "Divisa").text = "EUR"
    etree.SubElement(DatiGeneraliDocumento, "Data").text = fattura.data_decorrenza.strftime("%Y-%m-%d")
    etree.SubElement(DatiGeneraliDocumento, "Numero").text = fattura.nome
    etree.SubElement(DatiGeneraliDocumento, "ImportoTotaleDocumento").text = str(totale)
    etree.SubElement(DatiGeneraliDocumento, "Causale").text = fattura.descrizione
    if fattura.note!=None:
        note=fattura.note.split("\r\n")
        for n in note:
            if n!="":etree.SubElement(DatiGeneraliDocumento, "Causale").text = n
    DatiBeniServizi = etree.SubElement(FatturaElettronicaBody, "DatiBeniServizi")
    DettaglioLinee=[]
    for i in range(len(voci)):DettaglioLinee.append(etree.SubElement(DatiBeniServizi, "DettaglioLinee"))
    for i in range(len(voci)):
        etree.SubElement(DettaglioLinee[i], "NumeroLinea").text = str(i+1)
        etree.SubElement(DettaglioLinee[i], "Descrizione").text = voci[i].descrizione
        etree.SubElement(DettaglioLinee[i], "Quantita").text = str5dec(voci[i].quantita)#minimo 4 caratteri con punto
        etree.SubElement(DettaglioLinee[i], "PrezzoUnitario").text = str5dec(voci[i].importo)#minimo 4 caratteri con punto
        etree.SubElement(DettaglioLinee[i], "PrezzoTotale").text = str2dec(voci[i].importo*voci[i].quantita)#minimo 4 caratteri con punto
        etree.SubElement(DettaglioLinee[i], "AliquotaIVA").text = str2dec(voci[i].imposta.aliquota)#minimo 4 caratteri con punto
        if voci[i].imposta.natura!=None:etree.SubElement(DettaglioLinee[i], "Natura").text = voci[i].imposta.natura
        #<EsigibilitaIVA>S</EsigibilitaIVA>

    DatiRiepilogo=[]
    for i in range(len(voci_iva)):DatiRiepilogo.append(etree.SubElement(DatiBeniServizi, "DatiRiepilogo"))
    for i in range(len(voci_iva)):
        etree.SubElement(DatiRiepilogo[i], "AliquotaIVA").text = str2dec(voci_iva[i].imposta.aliquota)
        if voci_iva[i].imposta.natura!=None:etree.SubElement(DatiRiepilogo[i], "Natura").text = voci_iva[i].imposta.natura
        etree.SubElement(DatiRiepilogo[i], "ImponibileImporto").text = str2dec(voci_iva[i].imponibile)
        etree.SubElement(DatiRiepilogo[i], "Imposta").text = str2dec(voci_iva[i].iva)
        if voci_iva[i].imposta.natura!=None:etree.SubElement(DatiRiepilogo[i], "RiferimentoNormativo").text = voci_iva[i].imposta.riferimento_normativo
        if voci_iva[i].imposta.esigibilita=="S":etree.SubElement(DatiRiepilogo[i], "EsigibilitaIVA").text = "S"

    DatiPagamento = etree.SubElement(FatturaElettronicaBody, "DatiPagamento")
    etree.SubElement(DatiPagamento, "CondizioniPagamento").text = fattura.pagamento.condizioni
    DettaglioPagamento = etree.SubElement(DatiPagamento, "DettaglioPagamento")
    etree.SubElement(DettaglioPagamento, "ModalitaPagamento").text = fattura.pagamento.modalita
    etree.SubElement(DettaglioPagamento, "DataScadenzaPagamento").text = fattura.data_scadenza.strftime("%Y-%m-%d")
    etree.SubElement(DettaglioPagamento, "ImportoPagamento").text = str(importo_pagamento)
    etree.SubElement(DettaglioPagamento, "IBAN").text = azienda.iban

    allegati=fattura.allegato.all()
    Allegati=[]
    for i in range(len(allegati)):Allegati.append(etree.SubElement(FatturaElettronicaBody, "Allegati"))
    for i in range(len(allegati)):
        etree.SubElement(Allegati[i], "NomeAttachment").text = allegati[i].nome
        etree.SubElement(Allegati[i], "Attachment").text = base64.b64encode(allegati[i].binario)

    #objectify.deannotate(FatturaElettronica)
    #etree.cleanup_namespaces(FatturaElettronica)

    #xml = etree.tostring(FatturaElettronica, xml_declaration=True, encoding='iso-8859-1', pretty_print=True)

    #xml[0]='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    #xml[1]='<p:FatturaElettronica xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2" versione="FPR12">'
    Tree=etree.ElementTree(FatturaElettronica)
    Tree.write(filename, encoding='UTF-8', xml_declaration=True, method="xml", pretty_print=True)

    f = open(filename, "r")
    xml=f.readlines()
    f.close()
    xml[0]='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    if partner.pa:xml[1]='<p:FatturaElettronica xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2" versione="FPA12">\n'
    else:xml[1]='<p:FatturaElettronica xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2" versione="FPR12">\n'
    xml[-1]='</p:FatturaElettronica>\n'
    f = open(filename, "w")
    for r in xml:
        f.write(r)
    f.close()   

def str5dec(value):
    return str(Decimal(value+0).quantize(Decimal('.00001'), rounding=ROUND_HALF_UP))

def str2dec(value):
    return str(Decimal(value+0).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))

def b62(num):#converte da decimale a base 62, serve per generare il nome (univoco) della fattura elettronica
    b62=""
    for i in range(5):
        d=int(num/62**(4-i))
        b62+=L[d]
        num=num-d*62**(4-i)
    return b62
# F A T T U R A #########################################################################



# I M P O S T A Z I O N I #########################################################################
@app.route('/impostazioni')
@login_required
def impostazioni():
    return render_template('impostazioni.html')

@app.route('/imposta_mastri')
@login_required
def imposta_mastri():
    mastri = Mastro.query.order_by(Mastro.codice).all()
    return render_template('imposta_mastri.html', mastri=mastri)

@app.route('/log')
@login_required
def log():
    start=current_user.data-relativedelta(months=12)
    logs = Log.query.filter(Log.timestamp>start).order_by(Log.id.desc()).all()
    return render_template('log.html', logs=logs)

@app.route('/imposta_mastro/<id>', methods=['GET', 'POST'])
@login_required
def imposta_mastro(id):
    mastro=Mastro.query.get(id)
    sottomastri=Sottomastro.query.filter_by(mastro=mastro).order_by(Sottomastro.codice).all()
    form = MastroForm()
    if form.validate_on_submit():
        mastro.nome=form.nome.data
        mastro.tipo=form.tipo.data
        mastro.codice=form.codice.data
        db.session.commit()
        flash('I dati sono stati salvati !')
        return redirect(url_for('imposta_mastri'))
    if form.is_submitted() and not form.validate():pass
    else:
        form.nome.data=mastro.nome
        form.tipo.data=mastro.tipo
        form.codice.data=mastro.codice
    return render_template('imposta_mastro.html', mastro=mastro, sottomastri=sottomastri, form=form)

@app.route('/aggiungi_mastro')
@login_required
@requires_roles('admin')
def aggiungi_mastro():
    mastro=Mastro(nome="Nuovo mastro")
    db.session.add(mastro)
    db.session.commit()
    #return redirect(url_for('imposta_mastri'))
    return redirect(url_for('imposta_mastro', id=mastro.id))

@app.route('/rimuovi_mastro/<id>')
@login_required
@requires_roles('admin')
def rimuovi_mastro(id):
    mastro=Mastro.query.get(id)
    db.session.delete(mastro)
    db.session.commit()
    return redirect(url_for('imposta_mastri'))

@app.route('/imposta_sottomastro/<id>', methods=['GET', 'POST'])
@login_required
def imposta_sottomastro(id):
    sottomastro=Sottomastro.query.get(id)
    conti=Conto.query.filter_by(sottomastro=sottomastro).order_by(Conto.codice).all()
    form = SottomastroForm()
    mastri = Mastro.query.all()
    if form.validate_on_submit():
        sottomastro.nome=form.nome.data
        sottomastro.mastro=Mastro.query.filter_by(nome=form.mastro.data).first()
        sottomastro.codice=form.codice.data
        db.session.commit()
        flash('I dati sono stati salvati !')
        return redirect(url_for('imposta_mastro', id=sottomastro.mastro.id))
    if form.is_submitted() and not form.validate():pass
    else:
        form.nome.data=sottomastro.nome
        form.codice.data=sottomastro.codice
        if sottomastro.mastro!=None:form.mastro.data=sottomastro.mastro.nome
    return render_template('imposta_sottomastro.html', sottomastro=sottomastro, mastri=mastri, conti=conti, form=form)

@app.route('/aggiungi_sottomastro/<id>')
@login_required
@requires_roles('admin')
def aggiungi_sottomastro(id):
    mastro=Mastro.query.get(id)
    sottomastro=Sottomastro(nome="Nuovo sottomastro", mastro=mastro)
    db.session.add(sottomastro)
    db.session.commit()
    #return redirect(url_for('imposta_mastro', id=id))
    return redirect(url_for('imposta_sottomastro', id=sottomastro.id))

@app.route('/rimuovi_sottomastro/<id>')
@login_required
@requires_roles('admin')
def rimuovi_sottomastro(id):
    sottomastro=Sottomastro.query.get(id)
    id=sottomastro.mastro.id
    db.session.delete(sottomastro)
    db.session.commit()
    return redirect(url_for('imposta_mastro', id=id))

@app.route('/imposta_conto/<id>', methods=['GET', 'POST'])
@login_required
def imposta_conto(id):
    conto=Conto.query.get(id)
    form = ContoForm()
    sottomastri = Sottomastro.query.all()
    if form.validate_on_submit():
        conto.descrizione=form.descrizione.data
        conto.codice=form.codice.data
        conto.sottomastro=Sottomastro.query.filter_by(nome=form.sottomastro.data).first()
        conto.nome=str(conto.sottomastro.mastro.codice).zfill(2)+"."+str(conto.sottomastro.codice).zfill(2)+"."+str(conto.codice).zfill(3)+" "+conto.descrizione
        db.session.commit()
        flash('I dati sono stati salvati !')
        return redirect(url_for('imposta_sottomastro', id=conto.sottomastro.id))
    if form.is_submitted() and not form.validate():pass
    else:
        form.descrizione.data=conto.descrizione
        form.codice.data=conto.codice
        if conto.sottomastro!=None:form.sottomastro.data=conto.sottomastro.nome
    return render_template('imposta_conto.html', conto=conto, sottomastri=sottomastri, form=form)

@app.route('/aggiungi_conto/<id>')
@login_required
@requires_roles('admin')
def aggiungi_conto(id):
    sottomastro=Sottomastro.query.get(id)
    conto=Conto(nome="Nuovo conto", sottomastro=sottomastro)
    db.session.add(conto)
    db.session.commit()
    #return redirect(url_for('imposta_sottomastro', id=sottomastro.id))
    return redirect(url_for('imposta_conto', id=conto.id))

@app.route('/rimuovi_conto/<id>')
@login_required
@requires_roles('admin')
def rimuovi_conto(id):
    conto=Conto.query.get(id)
    id=conto.sottomastro.id
    db.session.delete(conto)
    db.session.commit()
    return redirect(url_for('imposta_sottomastro', id=id))

@app.route('/imposta_registri')
@login_required
@requires_roles('admin')
def imposta_registri():
    registri = Registro.query.order_by(Registro.posizione).all()
    return render_template('imposta_registri.html', registri=registri)

@app.route('/imposta_registro/<id>', methods=['GET', 'POST'])
@login_required
@requires_roles('admin')
def imposta_registro(id):
    registro=Registro.query.get(id)
    conti = Conto.query.all()
    tipi_documento = Tipo_documento.query.all()
    form = RegistroForm()
    if form.validate_on_submit():
        registro.segno=form.segno.data
        registro.codice=form.codice.data
        registro.nome=form.nome.data
        registro.categoria=form.categoria.data
        registro.posizione=form.posizione.data
        registro.tipo_documento=Tipo_documento.query.filter_by(codice=form.tipo_documento.data).first()
        registro.conto=Conto.query.filter_by(nome=form.conto.data).first()
        registro.conto_precedente=Conto.query.filter_by(nome=form.conto_precedente.data).first()
        registro.conto_iva=Conto.query.filter_by(nome=form.conto_iva.data).first()
        db.session.commit()
        flash('I dati sono stati salvati !')
        return redirect(url_for('imposta_registri'))
    if form.is_submitted() and not form.validate():pass
    else:
        form.codice.data=registro.codice
        form.segno.data=registro.segno
        form.nome.data=registro.nome
        form.categoria.data=registro.categoria
        form.posizione.data=registro.posizione
        if registro.tipo_documento!=None:form.tipo_documento.data=registro.tipo_documento.codice
        if registro.conto!=None:form.conto.data=registro.conto.nome
        if registro.conto_precedente!=None:form.conto_precedente.data=registro.conto_precedente.nome
        if registro.conto_iva!=None:form.conto_iva.data=registro.conto_iva.nome
    return render_template('imposta_registro.html', registro=registro, conti=conti, form=form, tipi_documento=tipi_documento)

@app.route('/aggiungi_registro')
@login_required
@requires_roles('admin')
def aggiungi_registro():
    registro=Registro(nome="Nuovo registro")
    db.session.add(registro)
    db.session.commit()
    #return redirect(url_for('imposta_registri'))
    return redirect(url_for('imposta_registro', id=registro.id))

@app.route('/rimuovi_registro/<id>')
@login_required
@requires_roles('admin')
def rimuovi_registro(id):
    registro=Registro.query.get(id)
    db.session.delete(registro)
    db.session.commit()
    return redirect(url_for('imposta_registri'))

@app.route('/imposta_imposte')
@login_required
def imposta_imposte():
    imposte = Imposta.query.order_by(Imposta.posizione).all()
    return render_template('imposta_imposte.html', imposte=imposte)

@app.route('/imposta_imposta/<id>', methods=['GET', 'POST'])
@login_required
def imposta_imposta(id):
    imposta=Imposta.query.get(id)
    form = ImpostaForm()
    registri=Registro.query.all()
    if form.validate_on_submit():
        imposta.nome=form.nome.data
        imposta.posizione=form.posizione.data
        imposta.aliquota=form.aliquota.data
        imposta.natura=form.natura.data
        imposta.esigibilita=form.esigibilita.data
        imposta.indetraibile=form.indetraibile.data
        imposta.riferimento_normativo=form.riferimento_normativo.data
        imposta.rc=form.rc.data
        imposta.no_lipe=form.no_lipe.data
        db.session.commit()
        flash('I dati sono stati salvati !')
        return redirect(url_for('imposta_imposte'))
    if form.is_submitted() and not form.validate():pass
    else:
        form.nome.data=imposta.nome
        form.posizione.data=imposta.posizione
        form.aliquota.data=imposta.aliquota
        form.natura.data=imposta.natura
        form.esigibilita.data=imposta.esigibilita
        form.indetraibile.data=imposta.indetraibile
        form.riferimento_normativo.data=imposta.riferimento_normativo
        form.rc.data=imposta.rc
        form.no_lipe.data=imposta.no_lipe
    return render_template('imposta_imposta.html', imposta=imposta, registri=registri, form=form)

@app.route('/aggiungi_imposta')
@login_required
@requires_roles('admin')
def aggiungi_imposta():
    imposta=Imposta(nome="Nuova imposta")
    db.session.add(imposta)
    db.session.commit()
    return redirect(url_for('imposta_imposta', id=imposta.id))

@app.route('/rimuovi_imposta/<id>')
@login_required
@requires_roles('admin')
def rimuovi_imposta(id):
    imposta=Imposta.query.get(id)
    db.session.delete(imposta)
    db.session.commit()
    return redirect(url_for('imposta_imposte'))

@app.route('/imposta_ritenute')
@login_required
def imposta_ritenute():
    ritenute = Ritenuta.query.all()
    return render_template('imposta_ritenute.html', ritenute=ritenute)

@app.route('/imposta_ritenuta/<id>', methods=['GET', 'POST'])
@login_required
def imposta_ritenuta(id):
    ritenuta=Ritenuta.query.get(id)
    form = RitenutaForm()
    registri=Registro.query.all()
    conti=Conto.query.all()
    if form.validate_on_submit():
        ritenuta.nome=form.nome.data
        ritenuta.aliquota=form.aliquota.data
        ritenuta.registro_ritenuta=Registro.query.filter_by(nome=form.registro_ritenuta.data).first()
        ritenuta.conto_transito_ritenuta=Conto.query.filter_by(nome=form.conto_transito_ritenuta.data).first()
        db.session.commit()
        flash('I dati sono stati salvati !')
        return redirect(url_for('imposta_ritenute'))
    if form.is_submitted() and not form.validate():pass
    else:
        form.nome.data=ritenuta.nome
        form.aliquota.data=ritenuta.aliquota
        if ritenuta.registro_ritenuta!=None:form.registro_ritenuta.data=ritenuta.registro_ritenuta.nome
        if ritenuta.conto_transito_ritenuta!=None:form.conto_transito_ritenuta.data=ritenuta.conto_transito_ritenuta.nome
    return render_template('imposta_ritenuta.html', ritenuta=ritenuta, form=form, registri=registri, conti=conti)

@app.route('/aggiungi_ritenuta')
@login_required
@requires_roles('admin')
def aggiungi_ritenuta():
    ritenuta=Ritenuta(nome="Nuova ritenuta")
    db.session.add(ritenuta)
    db.session.commit()
    return redirect(url_for('imposta_ritenuta', id=ritenuta.id))

@app.route('/rimuovi_ritenuta/<id>')
@login_required
@requires_roles('admin')
def rimuovi_ritenuta(id):
    ritenuta=Ritenuta.query.get(id)
    db.session.delete(ritenuta)
    db.session.commit()
    return redirect(url_for('imposta_ritenute'))

@app.route('/imposta_registri_stampa')
@login_required
@requires_roles('admin')
def imposta_registri_stampa():
    registri = Registro_stampa.query.order_by(Registro_stampa.posizione).all()
    return render_template('imposta_registri_stampa.html', registri=registri)

@app.route('/imposta_registro_stampa/<id>', methods=['GET', 'POST'])
@login_required
@requires_roles('admin')
def imposta_registro_stampa(id):
    registro=Registro_stampa.query.get(id)
    form = RegistroStampaForm()
    if form.validate_on_submit():
        registro.nome=form.nome.data
        registro.categoria=form.categoria.data
        registro.posizione=form.posizione.data
        #registro.registro=Registro.query.filter_by(nome=form.registro.data).first()
        db.session.commit()
        flash('I dati sono stati salvati !')
        return redirect(url_for('imposta_registri_stampa'))
    if form.is_submitted() and not form.validate():pass
    else:
        form.nome.data=registro.nome
        form.categoria.data=registro.categoria
        form.posizione.data=registro.posizione
        #if registro.registro!=None:form.registro.data=registro.registro.nome
    registri=Registro.query.order_by(Registro.posizione).all()
    filtro_registro=registro.filtro_registro.all()
    return render_template('imposta_registro_stampa.html', registro_stampa=registro, form=form, registri=registri, filtro_registro=filtro_registro)

@app.route('/aggiungi_registro_stampa')
@login_required
@requires_roles('admin')
def aggiungi_registro_stampa():
    registro=Registro_stampa(nome="Nuovo registro stampa")
    db.session.add(registro)
    db.session.commit()
    #return redirect(url_for('imposta_registri'))
    return redirect(url_for('imposta_registro_stampa', id=registro.id))

@app.route('/rimuovi_registro_stampa/<id>')
@login_required
@requires_roles('admin')
def rimuovi_registro_stampa(id):
    registro=Registro_stampa.query.get(id)
    db.session.delete(registro)
    db.session.commit()
    return redirect(url_for('imposta_registri_stampa'))


@app.route('/aggiungi_filtro_registro/<id>')
@login_required
@requires_roles('admin')
def aggiungi_filtro_registro(id):
    registro_stampa=Registro_stampa.query.get(id)
    filtro_registro=Filtro_registro(registro_stampa=registro_stampa)
    db.session.add(filtro_registro)
    db.session.commit()
    return redirect(url_for('filtro_registro', id=filtro_registro.id))

@app.route('/filtro_registro/<id>', methods=['GET', 'POST'])
@login_required
@requires_roles('admin')
def filtro_registro(id):
    registri = Registro.query.all()
    form = FiltroRegistroForm()
    filtro = Filtro_registro.query.get(id)
    if form.validate_on_submit():
        filtro.registro=Registro.query.filter_by(nome=form.registro.data).first()
        db.session.commit()
        flash('I dati sono stati salvati !')
        return redirect(url_for('imposta_registro_stampa', id=filtro.registro_stampa.id))
    if form.is_submitted() and not form.validate():pass
    else:
        if filtro.registro != None: form.registro.data=filtro.registro.nome
    return render_template('filtro_registro.html', form=form, registri=registri)

@app.route('/rimuovi_filtro_registro/<id>')
@login_required
@requires_roles('admin')
def rimuovi_filtro_registro(id):
    filtro=Filtro_registro.query.get(id)
    id=filtro.registro_stampa.id
    db.session.delete(filtro)
    db.session.commit()
    return redirect(url_for('imposta_registro_stampa', id=id))

@app.route('/impostazioni_generali', methods=['GET', 'POST'])
@login_required
@requires_roles('admin')
def impostazioni_generali():
    impostazioni=Impostazioni.query.get(1)
    registri = Registro.query.all()
    conti = Conto.query.with_entities(Conto.nome).all()
    partners = Partner.query.order_by(Partner.nome).with_entities(Partner.nome, Partner.id).all()
    form = ImpostazioniForm()
    if form.validate_on_submit():
        impostazioni.azienda=Partner.query.filter_by(nome=form.azienda.data).first()
        impostazioni.erario=Partner.query.filter_by(nome=form.erario.data).first()
        impostazioni.registro_misc=Registro.query.filter_by(nome=form.registro_misc.data).first()
        impostazioni.registro_fatf=Registro.query.filter_by(nome=form.registro_fatf.data).first()
        impostazioni.registro_notf=Registro.query.filter_by(nome=form.registro_notf.data).first()
        impostazioni.registro_fatc=Registro.query.filter_by(nome=form.registro_fatc.data).first()
        impostazioni.registro_notc=Registro.query.filter_by(nome=form.registro_notc.data).first()
        impostazioni.registro_autofattura_rc=Registro.query.filter_by(nome=form.registro_autofattura_rc.data).first()
        impostazioni.registro_riconciliazione_rc=Registro.query.filter_by(nome=form.registro_riconciliazione_rc.data).first()
        impostazioni.registro_riconciliazione_sp=Registro.query.filter_by(nome=form.registro_riconciliazione_sp.data).first()
        impostazioni.conto_perdite_profitti=Conto.query.filter_by(nome=form.conto_perdite_profitti.data).first()
        impostazioni.conto_utile=Conto.query.filter_by(nome=form.conto_utile.data).first()
        impostazioni.conto_chiusura=Conto.query.filter_by(nome=form.conto_chiusura.data).first()
        impostazioni.conto_apertura=Conto.query.filter_by(nome=form.conto_apertura.data).first()
        impostazioni.conto_lav_autonomo=Conto.query.filter_by(nome=form.conto_lav_autonomo.data).first()
        impostazioni.starting_date=form.starting_date.data
        impostazioni.imap_server=form.imap_server.data
        impostazioni.imap_user=form.imap_user.data
        impostazioni.imap_pwd=form.imap_pwd.data
        impostazioni.smtp_server=form.smtp_server.data
        impostazioni.smtp_user=form.smtp_user.data
        impostazioni.smtp_pwd=form.smtp_pwd.data
        impostazioni.pec_sdi=form.pec_sdi.data
        impostazioni.sequenziale_sdi=form.sequenziale_sdi.data
        impostazioni.ultimo_giorno_esercizio=form.ultimo_giorno_esercizio.data
        print(type(form.starting_date.data),form.starting_date.data)
        db.session.commit()
        flash('I dati sono stati salvati !')
        return redirect(url_for('impostazioni_generali'))
    if form.is_submitted() and not form.validate():pass
    else:
        if impostazioni.azienda!=None:form.azienda.data=impostazioni.azienda.nome
        if impostazioni.erario!=None:form.erario.data=impostazioni.erario.nome
        if impostazioni.registro_misc!=None:form.registro_misc.data=impostazioni.registro_misc.nome
        if impostazioni.registro_fatf!=None:form.registro_fatf.data=impostazioni.registro_fatf.nome
        if impostazioni.registro_notf!=None:form.registro_notf.data=impostazioni.registro_notf.nome
        if impostazioni.registro_fatc!=None:form.registro_fatc.data=impostazioni.registro_fatc.nome
        if impostazioni.registro_notc!=None:form.registro_notc.data=impostazioni.registro_notc.nome
        if impostazioni.registro_autofattura_rc!=None:form.registro_autofattura_rc.data=impostazioni.registro_autofattura_rc.nome
        if impostazioni.registro_riconciliazione_rc!=None:form.registro_riconciliazione_rc.data=impostazioni.registro_riconciliazione_rc.nome
        if impostazioni.registro_riconciliazione_sp!=None:form.registro_riconciliazione_sp.data=impostazioni.registro_riconciliazione_sp.nome
        if impostazioni.conto_perdite_profitti!=None:form.conto_perdite_profitti.data=impostazioni.conto_perdite_profitti.nome
        if impostazioni.conto_utile!=None:form.conto_utile.data=impostazioni.conto_utile.nome
        if impostazioni.conto_chiusura!=None:form.conto_chiusura.data=impostazioni.conto_chiusura.nome
        if impostazioni.conto_apertura!=None:form.conto_apertura.data=impostazioni.conto_apertura.nome
        if impostazioni.conto_lav_autonomo!=None:form.conto_lav_autonomo.data=impostazioni.conto_lav_autonomo.nome
        form.starting_date.data=impostazioni.starting_date

        print(type(form.starting_date.data),form.starting_date.data)
        print(type(impostazioni.starting_date),impostazioni.starting_date)


        form.imap_server.data=impostazioni.imap_server
        form.imap_user.data=impostazioni.imap_user
        form.imap_pwd.data=impostazioni.imap_pwd
        form.smtp_server.data=impostazioni.smtp_server
        form.smtp_user.data=impostazioni.smtp_user
        form.smtp_pwd.data=impostazioni.smtp_pwd
        form.pec_sdi.data=impostazioni.pec_sdi
        form.sequenziale_sdi.data=impostazioni.sequenziale_sdi
        form.ultimo_giorno_esercizio.data=impostazioni.ultimo_giorno_esercizio
    return render_template('edit_impostazioni.html', partners=partners, registri=registri, conti=conti, form=form)
# I M P O S T A Z I O N I #########################################################################



# C O M M O N #########################################################################
def lock():
    while LOCK[0]:time.sleep(0.1)
    LOCK[0]=True

def unlock():
    LOCK[0]=False

def daterange(date1, date2):
    for n in range(int ((date2 - date1).days)+1):
        yield date1 + timedelta(n)

def dec(d):
    return Decimal(d).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)

def dec5(d):
    return Decimal(d).quantize(Decimal('.00001'), rounding=ROUND_HALF_UP)

def saldo(registrazioni):
    for r in registrazioni:
        if r!=None:
            riconciliazioni=Riconciliazione.query.filter_by(registrazione=r).all()
            saldo=0
            for ric in riconciliazioni:
                saldo+=ric.movimento.importo
            r.saldo=saldo
            print (r.nome,r.saldo)
    db.session.commit()

def valuta(value):
    return locale.format('%20.2f', dec(value+0), grouping=True)

def valutalong(value):
    return locale.format('%20.5f', dec5(value+0), grouping=True)

def sign(a):
    if a!=0:s=a/abs(a)
    else:s=1
    return s

def nome(x):
    if x!=None:n=x.nome
    else:n=""
    return n

@app.template_filter('formatdate')
def format_date(value, format="%d/%m/%Y"):
    if value is None:
        return ""
    return value.strftime(format)

@app.template_filter('formatnumero')
def format_number(value):
    if value is None:
        return "Bozza"
    #return "{:04n}".format(value)
    #return ("%04d") % value
    return str(165).zfill(4)

@app.template_filter('format2')
def format_number(value):
    if value is None:
        return "**"
    return str(value).zfill(2)

@app.template_filter('format3')
def format_number(value):
    if value is None:
        return "***"
    return str(value).zfill(3)

@app.template_filter('formatimporto')
def format_number(value):
    if value is None:
        return "0,00"
    #return "{0:.2f}".format(value)
    return locale.format('%20.2f', dec(value+0), grouping=True)#+0 e' un trucco per eliminare il -0

@app.template_filter('formatimportolong')
def format_number(value):
    if value is None:
        return "0,00"
    #return "{0:.2f}".format(value)
    return locale.format('%20.5f', Decimal(value+0).quantize(Decimal('.00001'), rounding=ROUND_HALF_UP), grouping=True)

class document(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        self.tab=kwargs.pop('tab')
        self.des=kwargs.pop('des')
        self.footer=kwargs.pop('footer')
        self.footer2=kwargs.pop('footer2')
        self.row=0
        super(document, self).__init__(*args, **kwargs)
        self.foot()

    def newpage(self):
        self.showPage()
        self.foot()
        self.row=1

    def newline(self):
        if self.row == 55:self.newpage()
        else:self.row+=1

    def foot(self):
        self.setFont('Times-Roman', 10)
        self.drawString(40,52,self.footer)
        self.drawString(40,40,self.footer2)
        self.line(40,67,550,67)

    def drawline(self):
        self.line(40,785-self.row*12,550,785-self.row*12)

    def drawhalflineright(self):
        self.line(295,785-self.row*12,550,785-self.row*12)

    def Write(self,i,txt):
        if self.tab[i][1]=="l":self.drawString(self.tab[i][0],782-self.row*12,txt)
        else:self.drawRightString(self.tab[i][0],782-self.row*12,txt)

    def write(self,i,txt):
        self.setFont('Times-Roman', 10)
        self.Write(i,txt)

    def writebold(self,i,txt):
        self.setFont('Times-Bold', 10)
        self.Write(i,txt)

    def writebig(self,i,txt):
        self.setFont('Times-Roman', 16)
        self.Write(i,txt)

    def writemedium(self,i,txt):
        self.setFont('Times-Roman', 12)
        self.Write(i,txt)

    def writemediumbold(self,i,txt):
        self.setFont('Times-Bold', 12)
        self.Write(i,txt)

class document2(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        self.page=kwargs.pop('page')
        self.page_0=self.page+0
        self.year=kwargs.pop('year')
        self.tab=kwargs.pop('tab')
        self.des=kwargs.pop('des')
        self.header=kwargs.pop('header')
        self.footer=kwargs.pop('footer')
        self.row=0
        super(document2, self).__init__(*args, **kwargs)
        self.headfoot()

    def newpage(self):
        self.showPage()
        #if self.page!=self.page_0:self.showPage()
        self.page+=1
        self.headfoot()
        self.row=1

    def newline(self):
        if self.row == 60:self.newpage()
        else:self.row+=1

    def headfoot(self):
        self.setFont('Courier', 8)
        self.drawString(40,805,self.header)
        self.drawString(40,40,self.footer)
        self.setFont('Courier-Bold', 8)
        for i in range(len(self.des)):
            if self.tab[i][1]=="l":self.drawString(self.tab[i][0],787,self.des[i])
            else:self.drawRightString(self.tab[i][0],787,self.des[i])
        self.setFont('Courier', 8)
        self.line(40,800,550,800)
        self.line(40,782,550,782)
        self.drawRightString(550,805,str(self.year)+"/"+str(self.page))
        self.line(40,55,550,55)

    def write(self,i,txt):
        if self.tab[i][1]=="l":self.drawString(self.tab[i][0],782-self.row*12,txt)
        else:self.drawRightString(self.tab[i][0],782-self.row*12,txt)

    def writebold(self,i,txt):
        self.setFont('Courier-Bold', 8)
        self.write(i,txt)
        self.setFont('Courier', 8)

class document3(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        self.page=kwargs.pop('page')
        self.page_0=self.page+0
        self.year=kwargs.pop('year')
        self.tab=kwargs.pop('tab')
        self.des=kwargs.pop('des')
        self.header=kwargs.pop('header')
        self.footer=kwargs.pop('footer')
        self.row=0
        self.top=550
        self.bottom=40
        super(document3, self).__init__(*args, **kwargs)
        self.headfoot()

    def newpage(self):
        self.showPage()
        #if self.page!=self.page_0:self.showPage()
        self.page+=1
        self.headfoot()
        self.row=1

    def newline(self):
        if self.row == 42:self.newpage()
        else:self.row+=1

    def headfoot(self):
        self.setFont('Courier', 8)
        self.drawString(40,self.top+23,self.header)
        self.drawString(40,self.bottom-15,self.footer)
        self.setFont('Courier-Bold', 8)
        for i in range(len(self.des)):
            if self.tab[i][1]=="l":self.drawString(self.tab[i][0],self.top+5,self.des[i])
            else:self.drawRightString(self.tab[i][0],self.top+5,self.des[i])
        self.setFont('Courier', 8)
        self.line(40,self.top+18,800,self.top+18)
        self.line(40,self.top,800,self.top)
        self.drawRightString(805,self.top+23,str(self.year)+"/"+str(self.page))
        self.line(40,self.bottom,800,self.bottom)

    def write(self,i,txt):
        if self.tab[i][1]=="l":self.drawString(self.tab[i][0],self.top-self.row*12,txt)
        else:self.drawRightString(self.tab[i][0],self.top-self.row*12,txt)

    def writebold(self,i,txt):
        self.setFont('Courier-Bold', 8)
        self.write(i,txt)
        self.setFont('Courier', 8)

def reg_ricevuta(registrazione):#registra la ricevuta
    validazione=Validazione(registrazione=registrazione)
    db.session.add(validazione)
    anno=registrazione.data_contabile.year
    dal=datetime.strptime("01/01/"+str(anno),"%d/%m/%Y").date()
    al=datetime.strptime("31/12/"+str(anno),"%d/%m/%Y").date()
    i=1
    while Registrazione.query.filter_by(registro=registrazione.registro).filter(and_(Registrazione.data_contabile >= dal, Registrazione.data_contabile <= al)).filter_by(numero=i).first()!=None:
        i=i+1
    registrazione.numero=i
    registrazione.nome=registrazione.registro.codice+"/"+str(anno)[2:]+"/"+ str(i).zfill(4)

    voci=registrazione.voce.order_by(Voce.id).all()
    totale=0
    for v in voci:
        totale+=v.importo
    registrazione.importo=totale*registrazione.registro.segno
    movimento=Movimento(descrizione=registrazione.descrizione, data_contabile=registrazione.data_contabile, importo=totale*registrazione.registro.segno, conto=registrazione.registro.conto, partner=registrazione.partner, registrazione=registrazione, validazione=validazione)
    db.session.add(movimento)
    riconciliazione=Riconciliazione(validazione=validazione, registrazione=registrazione, movimento=movimento)
    db.session.add(riconciliazione)

    for v in voci:
        movimento=Movimento(descrizione=v.descrizione, data_contabile=registrazione.data_contabile, importo=dec(-v.importo*v.quantita*registrazione.registro.segno), conto=v.conto, registrazione=registrazione, validazione=validazione)
        db.session.add(movimento)
    datalog="Validata registrazione ["+registrazione.nome+"] importo["+str(registrazione.importo)+"] partner["+nome(registrazione.partner)+"] data contabile["+format_date(registrazione.data_contabile)+"] data registrazione["+format_date(registrazione.data_decorrenza)+"] data scadenza["+format_date(registrazione.data_scadenza)+"]"
    log = Log(datalog=datalog, user=current_user.username, timestamp = func.now())
    db.session.add(log)
    db.session.commit()
    saldo([registrazione])

def reg_fattura(registrazione):#registra la fattura
    impostazioni=Impostazioni.query.get(1)
    validazione=Validazione(registrazione=registrazione)
    db.session.add(validazione)
    anno=registrazione.data_contabile.year
    dal=datetime.strptime("01/01/"+str(anno),"%d/%m/%Y").date()
    al=datetime.strptime("31/12/"+str(anno),"%d/%m/%Y").date()
    i=1
    while Registrazione.query.filter_by(registro=registrazione.registro).filter(and_(Registrazione.data_contabile >= dal, Registrazione.data_contabile <= al)).filter_by(numero=i).first()!=None:
        i=i+1
    registrazione.numero=i
    registrazione.nome=registrazione.registro.codice+"/"+str(anno)[2:]+"/"+ str(i).zfill(4)

    voci=registrazione.voce.order_by(Voce.id).all()
    totale=0
    imposta=[]
    if registrazione.registro.conto_iva!=None:#Fattura normale
        for voce_iva in registrazione.voce_iva:
            totale+=voce_iva.imponibile+voce_iva.iva
    else:
        for v in voci:
            totale+=v.importo
    registrazione.importo=totale*registrazione.registro.segno
    if registrazione.lav_autonomo:conto=impostazioni.conto_lav_autonomo
    else:conto=registrazione.registro.conto
    movimento=Movimento(descrizione=registrazione.descrizione, data_contabile=registrazione.data_contabile, importo=totale*registrazione.registro.segno, conto=conto, partner=registrazione.partner, registrazione=registrazione, validazione=validazione)
    db.session.add(movimento)
    riconciliazione=Riconciliazione(validazione=validazione, registrazione=registrazione, movimento=movimento)
    db.session.add(riconciliazione)


    fine_esercizio_anno=datetime.strptime(impostazioni.ultimo_giorno_esercizio+"/"+str(anno),"%d/%m/%Y").date()
    if registrazione.data_contabile > fine_esercizio_anno:data_precedente=fine_esercizio_anno
    else:data_precedente=fine_esercizio_anno-relativedelta(years=1)
    data_successivo=data_precedente+relativedelta(days=1)+relativedelta(years=1)



    # if registrazione.data_contabile >= datetime.strptime("01/10/"+str(anno),"%d/%m/%Y").date():
        # data_precedente=datetime.strptime("30/09/"+str(anno),"%d/%m/%Y").date()
        # data_successivo=datetime.strptime("01/10/"+str(anno+1),"%d/%m/%Y").date()
    # else:
        # data_precedente=datetime.strptime("30/09/"+str(anno-1),"%d/%m/%Y").date()
        # data_successivo=datetime.strptime("01/10/"+str(anno),"%d/%m/%Y").date()
    for v in voci:
        if v.esercizio_precedente:#Fatture e note da ricevere e da emettere
            movimento=Movimento(descrizione=v.descrizione, data_contabile=registrazione.data_contabile, importo=dec(-v.importo*v.quantita*registrazione.registro.segno), conto=registrazione.registro.conto_precedente, registrazione=registrazione, validazione=validazione, partner=registrazione.partner)
        else:
            movimento=Movimento(descrizione=v.descrizione, data_contabile=registrazione.data_contabile, importo=dec(-v.importo*v.quantita*registrazione.registro.segno), conto=v.conto, registrazione=registrazione, validazione=validazione, partner=registrazione.partner)
        db.session.add(movimento)

    for voce_iva in registrazione.voce_iva:
        if voce_iva.iva!=0:
            if voce_iva.imposta.indetraibile:
                for v in voci:
                    if v.imposta==voce_iva.imposta:
                        conto=v.conto
                        break
            else: conto=registrazione.registro.conto_iva
            movimento=Movimento(descrizione=voce_iva.imposta.nome, data_contabile=registrazione.data_contabile, importo=-voce_iva.iva*registrazione.registro.segno, conto=conto, registrazione=registrazione, validazione=validazione)
            db.session.add(movimento)
    datalog="Validata registrazione ["+registrazione.nome+"] importo["+str(registrazione.importo)+"] partner["+nome(registrazione.partner)+"] data contabile["+format_date(registrazione.data_contabile)+"] data registrazione["+format_date(registrazione.data_decorrenza)+"] data scadenza["+format_date(registrazione.data_scadenza)+"]"
    log = Log(datalog=datalog, user=current_user.username, timestamp = func.now())
    db.session.add(log)
    db.session.commit()
    saldo([registrazione])

def calcola_IVA(registrazione):#calcola vari parametri per l'IVA
    registri_fatture=Registro.query.filter(Registro.categoria=="Fattura").order_by(Registro.posizione).all()
    conto_iva=[]
    for r in registri_fatture:
        if r.conto_iva not in conto_iva: conto_iva.append(r.conto_iva)
    imposta=Imposta.query.order_by(Imposta.posizione).all()
    imponibile,iva=[],[]
    for i in range(len(imposta)):
        imponibile.append([0]*len(conto_iva))
        iva.append([0]*len(conto_iva))
    for registro in registri_fatture:
        fatture=Registrazione.query.filter_by(registro=registro).filter(and_(Registrazione.data_contabile >= registrazione.data_decorrenza, Registrazione.data_contabile <= registrazione.data_scadenza)).filter(Registrazione.numero!=None).all()
        for r in fatture:
            imponibile_parziale=[]
            for i in range(len(imposta)):
                imponibile_parziale.append([0]*len(conto_iva))
            for v in r.voce_iva:
                imponibile[imposta.index(v.imposta)][conto_iva.index(r.registro.conto_iva)]+=v.imponibile*r.registro.segno
                iva[imposta.index(v.imposta)][conto_iva.index(r.registro.conto_iva)]+=v.iva*r.registro.segno

    IVA=[0]*len(conto_iva)
    for i in range(len(imposta)):
        if (not imposta[i].indetraibile) and imposta[i].esigibilita!="S":#esclude l'iva indetraibile e lo split payment dal totale iva
            for c in range(len(conto_iva)):
                IVA[c]+=iva[i][c]
    return registri_fatture, conto_iva, imposta, imponibile, iva, IVA

def validate(r):#verifica che la scrittura sia quadrata e completa
    val=True
    voci=r.voce.all()
    somma=0
    for v in voci:
        if v.conto==None or v.descrizione==None:val=False
        somma+=v.importo
    if somma!=0:val=False
    return val

def validate_fattura(registrazione):#verifica che la fattura sia completa
    val=True
    if registrazione.registro.tipo_documento!=None:# Fattura o nota di credito cliente
        if registrazione.pagamento==None:val=False
        if registrazione.partner==None:val=False
        if registrazione.descrizione==None:val=False
        if registrazione.data_contabile==None:val=False
        if registrazione.data_decorrenza==None:val=False
        if registrazione.data_scadenza==None:val=False
    return val
# C O M M O N #########################################################################



# S D I #########################################################################
@app.route('/sdi_edit')
@login_required
def sdi_edit():#modifica la tabella sdi, solo per esperti 
    records = Sdi.query.order_by(Sdi.timestamp.desc()).all()
    return render_template('sdi_edit.html', records=records)

@app.route('/sdi_in')
@login_required
def sdi_in():#mostra i record sdi in ingresso
    records = Sdi.query.filter(Sdi.registrazione==None).filter(Sdi.fattura==True).filter(Sdi.inbox==True).order_by(Sdi.timestamp.desc()).all()
    return render_template('sdi_in.html', records=records)

@app.route('/sdi/<id>', methods=['GET', 'POST'])
@login_required
def sdi(id):#visualizza il singolo record sdi
    record_sdi=Sdi.query.get(id)
    upload_form = UploadForm()
    if upload_form.submit2.data and upload_form.validate():
        nome=upload_form.file.data.filename
        allegato=Allegato(sdi=record_sdi, nome=nome, binario=upload_form.file.data.read())
        db.session.add(allegato)
        db.session.commit()
    return render_template('sdi.html', record_sdi=record_sdi, upload_form=upload_form)

@app.route('/rimuovi_allegato_sdi/<id>', methods=['GET', 'POST'])
@login_required
def rimuovi_allegato_sdi(id):#rimuove allegato da record sdi
    allegato=Allegato.query.get(id)
    form = ConfermaForm()
    if form.validate_on_submit():
        id=allegato.sdi.id
        db.session.delete(allegato)
        db.session.commit()
        return redirect(url_for('sdi', id=id))
    testo=allegato.nome
    if testo==None:testo="None"
    return render_template('conferma.html', testo="Rimozione dell'allegato "+testo, form=form)

@app.route('/invia_fattura_sdi/<id>', methods=['GET', 'POST'])
@login_required
def invia_fattura_sdi(id):#invia la fattura elettronica all'SDI tramite PEC
    allegato=Allegato.query.get(id)
    form = ConfermaForm()
    if form.validate_on_submit():
        return render_template('wait.html', id=id, link="invia_fattura_sdi_")
    testo=allegato.nome
    if testo==None:testo="None"
    return render_template('conferma.html', testo="Inviare la fattura "+testo+" al sistema di interscambio ?", form=form)

@app.route('/invia_fattura_sdi_/<id>', methods=['GET', 'POST'])
@login_required
def invia_fattura_sdi_(id):#invia la fattura elettronica all'SDI tramite PEC
    impostazioni=Impostazioni.query.get(1)
    app.config['MAIL_SERVER']=impostazioni.smtp_server
    app.config['MAIL_USERNAME']=impostazioni.smtp_user
    app.config['MAIL_PASSWORD']=impostazioni.smtp_pwd
    allegato=Allegato.query.get(id)
    id=allegato.sdi.registrazione.id
    nome=allegato.nome
    msg = Message(nome, sender=impostazioni.smtp_user, recipients=[impostazioni.pec_sdi])
    msg.attach(nome, "text/xml", allegato.binario)
    if allegato.sdi.sent!=True:#per evitare i doppi invii in caso di click compulsivi con back
        Mail(app).send(msg)
        #mail.send(msg)
        allegato.sdi.sent=True
        allegato.sdi.timestamp=func.now()
        db.session.commit()
    return redirect(url_for('fattura', id=id))

@app.route('/rimuovi_record_sdi/<id>', methods=['GET', 'POST'])
@login_required
def rimuovi_record_sdi(id):#rimuove un record sdi
    record_sdi=Sdi.query.get(id)
    form = ConfermaForm()
    if form.validate_on_submit():
        nome=record_sdi.nome
        db.session.delete(record_sdi)
        db.session.commit()
        flash("Il record "+nome+" è stato rimosso !")
        return redirect(url_for('sdi_edit'))
    return render_template('conferma.html', testo="Rimozione del record "+record_sdi.nome, form=form)

@app.route('/importa_fattura_sdi/<id>')
@login_required
def importa_fattura_sdi(id):
    return render_template('wait.html', id=id, link="importa_fattura_sdi_")

@app.route('/importa_fattura_sdi_/<id>')
@login_required
def importa_fattura_sdi_(id):#importa la fattura elettronica dal record sdi
    lock()
    impostazioni=Impostazioni.query.get(1)
    record_sdi=Sdi.query.get(id)
    if record_sdi.registrazione==None:

        for a in record_sdi.allegato:#cerca l'allegato fattura elettronica
            if a.nome[-3:].lower()=="xml" and len(a.nome)>12 and not "_" in a.nome[-9:]:break

        nome=a.nome
        print(nome)
        filename=os.path.join(here,nome)
        
        f = open(filename, 'wb')
        f.write(a.binario)
        f.close()

        nome = nome[:-4]
        tree = ET.parse(filename)
        root = tree.getroot()

        DatiGenerali=root.find('FatturaElettronicaBody/DatiGenerali')
        DatiGeneraliDocumento=DatiGenerali.find('DatiGeneraliDocumento')
        TipoDocumento=text(DatiGeneraliDocumento.find('TipoDocumento'))
        if TipoDocumento=="TD04":registro=impostazioni.registro_notf
        else:registro=impostazioni.registro_fatf

        registrazione=Registrazione(registro=registro, importo=0, saldo=0, data_contabile=current_user.data)
        db.session.add(registrazione)
        record_sdi.registrazione=registrazione

        RegFisc={"RF01":"Ordinario","RF02":"Contribuenti minimi","RF03":"Nuove iniziative produttive","RF04":"Agricoltura e attività connesse e pesca","RF05":"Vendita sali e tabacchi","RF06":"Commercio","RF07":"Editoria","RF08":"Gestione di servizi di telefonia pubblica","RF09":"Rivendita di documenti di trasporto pubblico e di sosta","RF10":"Intrattenimenti, giochi e altre attività","RF11":"Agenzie di viaggi e turismo","RF12":"Agriturismo","RF13":"Vendite a domicilio","RF14":"Rivendita di beni usati, di oggetti d’arte, d’antiquariato o da collezione","RF15":"Agenzie di vendite all’asta di oggetti d’arte, antiquariato o da collezione","RF16":"IVA per cassa P.A.","RF17":"IVA per cassa","RF18":"Altro","RF19":"Forfettario"}
        TipoDoc={"TD01":"FATTURA", "TD02":"Acconto/Anticipo su fattura", "TD03":"Acconto/Anticipo su parcella", "TD04":"NOTA DI CREDITO", "TD05":"NOTA DI DEBITO", "TD06":"Parcella", "":"Errore"}
        CondPag={"TP01":"Pagamento a rate","TP02":"Pagamento completo","TP03":"Anticipo"}
        ModPag={"MP01":"Contanti","MP02":"Assegno","MP03":"Assegno circolare","MP04":"Contanti presso Tesoreria","MP05":"Bonifico","MP06":"Vaglia cambiario","MP07":"Bollettino bancario","MP08":"Carta di pagamento","MP09":"RID","MP10":"RID utenze","MP11":"RID veloce","MP12":"Riba","MP13":"MAV","MP14":"Quietanza erario stato","MP15":"Giroconto su conti di contabilità speciale","MP16":"Domiciliazione bancaria","MP17":"Domiciliazione postale","MP18":"Bollettino di c/c postale","MP19":"SEPA Direct Debit","MP20":"SEPA Direct Debit CORE","MP21":"SEPA Direct Debit B2B","MP22":"Trattenuta su somme già riscosse"}
        Nat={"N1":"Escluse ex art.15","N2":"Non soggette","N3":"Non imponibili","N4":"Esenti","N5":"Regime del margine","N6":"Inversione contabile","N7":"IVA assolta in altro stato UE"}
        filename2=os.path.join(here, 'FATTURA.pdf')
        can = canvas.Canvas(filename2, pagesize=A4)
        can.setLineWidth(.6)
        can.setFont('Times-Bold',12)
        can.drawString(40,780,'Fornitore')
        can.drawString(300,780,'Cliente')

        CedentePrestatore = root.find('FatturaElettronicaHeader/CedentePrestatore')
        DatiAnagrafici = CedentePrestatore.find('DatiAnagrafici')
        Denominazione = text(DatiAnagrafici.find('Anagrafica/Denominazione'))
        if Denominazione == "":
            Nome = text(DatiAnagrafici.find('Anagrafica/Nome'))
            Cognome = text(DatiAnagrafici.find('Anagrafica/Cognome'))
            if Nome != Cognome: Denominazione = Cognome + " " + Nome
            else: Denominazione = Nome
        can.setFont('Times-Roman', 12)
        can.drawString(40,760,Denominazione[:34])
        Sede=CedentePrestatore.find('Sede')
        can.drawString(40,745,text(Sede.find('Indirizzo')))
        can.drawString(40,730,text(Sede.find('CAP'))+" "+text(Sede.find('Comune'))+" ("+text(Sede.find('Provincia'))+ ") - "+text(Sede.find('Nazione')))
        can.drawString(40,715,"P.IVA "+text(DatiAnagrafici.find('IdFiscaleIVA/IdPaese'))+text(DatiAnagrafici.find('IdFiscaleIVA/IdCodice')))
        can.drawString(40,700,"C.F. "+text(DatiAnagrafici.find('CodiceFiscale')))
        cf=DatiAnagrafici.find('CodiceFiscale')
        if cf!=None:registrazione.partner=Partner.query.filter(Partner.cf==text(cf)).first()
        if registrazione.partner==None:
            piva=DatiAnagrafici.find('IdFiscaleIVA/IdPaese').text+DatiAnagrafici.find('IdFiscaleIVA/IdCodice').text
            #print(piva)
            registrazione.partner=Partner.query.filter(Partner.iva==piva).first()
        RegimeFiscale=text(DatiAnagrafici.find('RegimeFiscale'))
        if RegimeFiscale in RegFisc:RegimeFiscale+=" ("+RegFisc[RegimeFiscale]+")"
        can.drawString(40,685,"Regime Fiscale: "+RegimeFiscale)

        CessionarioCommittente = root.find('FatturaElettronicaHeader/CessionarioCommittente')
        DatiAnagrafici = CessionarioCommittente.find('DatiAnagrafici')
        Denominazione = text(DatiAnagrafici.find('Anagrafica/Denominazione'))
        if Denominazione == "":
            Nome = text(DatiAnagrafici.find('Anagrafica/Nome'))
            Cognome = text(DatiAnagrafici.find('Anagrafica/Cognome'))
            if Nome != Cognome: Denominazione = Cognome + " " + Nome
            else: Denominazione = Nome
        can.drawString(300,760,Denominazione[:34])
        Sede=CessionarioCommittente.find('Sede')
        can.drawString(300,745,text(Sede.find('Indirizzo')))
        can.drawString(300,730,text(Sede.find('CAP'))+" "+text(Sede.find('Comune'))+" ("+text(Sede.find('Provincia'))+ ") - "+text(Sede.find('Nazione')))
        can.drawString(300,715,"P.IVA "+text(DatiAnagrafici.find('IdFiscaleIVA/IdPaese'))+text(DatiAnagrafici.find('IdFiscaleIVA/IdCodice')))
        can.drawString(300,700,"C.F. "+text(DatiAnagrafici.find('CodiceFiscale')))
        r=685-15
        DatiGenerali=root.find('FatturaElettronicaBody/DatiGenerali')
        DatiGeneraliDocumento=DatiGenerali.find('DatiGeneraliDocumento')
        can.line(40,r+5,550,r+5)
        r=r-15
        can.setFont('Times-Bold',12)
        can.drawString(40,r,"Tipo di documento")
        can.drawString(200,r,"Numero")
        can.drawString(300,r,"Data")
        can.drawString(400,r,"Contratto")
        can.setFont('Times-Roman', 12)
        r=r-15
        TipoDocumento=text(DatiGeneraliDocumento.find('TipoDocumento'))
        if TipoDocumento in TipoDoc:TipoDocumento+=" ("+TipoDoc[TipoDocumento]+")"
        can.drawString(40,r,TipoDocumento)
        can.drawString(200,r,text(DatiGeneraliDocumento.find('Numero')))
        registrazione.numero_origine=text(DatiGeneraliDocumento.find('Numero'))
        can.drawString(300,r,data(DatiGeneraliDocumento.find('Data')))
        registrazione.data_decorrenza=datetime.strptime(DatiGeneraliDocumento.find('Data').text,"%Y-%m-%d").date()
        can.drawString(400,r,text(DatiGenerali.find('DatiContratto/IdDocumento')))
        r=r-15
        can.line(40,r+5,550,r+5)
        r=r-15
        Causale=DatiGeneraliDocumento.findall('Causale')
        if len(Causale)>0:
            can.setFont('Times-Bold',12)
            can.drawString(40,r,"Causale")
            can.setFont('Times-Roman', 12)
            r=r-15
            for Causa in Causale:
                can.drawString(40,r,text(Causa))
                r=r-15
            can.line(40,r+5,550,r+5)
            r=r-15
        can.setFont('Times-Bold',12)
        can.drawString(40,r,"Descrizione")
        can.drawRightString(290,r,"Quantità")
        can.drawRightString(390,r,"Prezzo")
        can.drawString(450,r,"IVA%")
        can.drawRightString(550,r,"Importo")
        can.setFont('Times-Roman', 12)
        r=r-15
        DatiBeniServizi = root.findall('FatturaElettronicaBody/DatiBeniServizi/DettaglioLinee')
        for Dati in DatiBeniServizi:
            can.drawString(40,r,text(Dati.find("Descrizione"))[:30])
            can.drawRightString(310,r,align(Dati.find("Quantita")))
            can.drawRightString(410,r,align(Dati.find("PrezzoUnitario")))
            can.drawRightString(480,r,text(Dati.find("AliquotaIVA")))
            can.drawRightString(550,r,duedecimali(Dati.find("PrezzoTotale")))
            r=r-15
        DatiCassaPrevidenziale = DatiGeneraliDocumento.find('DatiCassaPrevidenziale')
        if DatiCassaPrevidenziale != None:
            can.drawString(40,r,"Cassa Previdenziale "+text(DatiCassaPrevidenziale.find("TipoCassa")))
            can.drawRightString(480,r,text(DatiCassaPrevidenziale.find("AliquotaIVA")))
            can.drawRightString(550,r,duedecimali(DatiCassaPrevidenziale.find("ImportoContributoCassa")))
            r=r-15

        can.line(40,r+5,550,r+5)
        r=r-15
        can.setFont('Times-Bold',12)
        can.drawString(40,r,"Imponibile")
        can.drawString(140,r,"IVA%")
        can.drawString(240,r,"Imposta")
        can.drawString(350,r,"Natura")
        DatiRiepilogo = root.findall('FatturaElettronicaBody/DatiBeniServizi/DatiRiepilogo')
        can.setFont('Times-Roman', 12)
        r=r-15

        IVA=0.0
        Imponibile=0.0
        for Dati in DatiRiepilogo:
            AliquotaIVA = duedecimali(Dati.find("AliquotaIVA"))
            ImponibileImporto = duedecimali(Dati.find("ImponibileImporto"))
            Imponibile=Imponibile+float(ImponibileImporto)
            Imposta = duedecimali(Dati.find("Imposta"))
            IVA=IVA+float(Imposta)
            can.drawRightString(95,r,ImponibileImporto)
            can.drawRightString(170,r,AliquotaIVA)
            can.drawRightString(280,r,Imposta)
            Natura = text(Dati.find("Natura"))
            if Natura != "":
                if Natura in Nat:Natura+=" ("+Nat[Natura]+")"
                can.drawString(350,r,Natura)
            r=r-15
        can.line(40,r+5,550,r+5)
        r=r-15
        R=r
        can.setFont('Times-Bold',12)
        can.drawString(380,r,"Totale imponibile")
        can.setFont('Times-Roman', 12)
        can.drawRightString(550,r,'{:.2f}'.format(Imponibile))
        r=r-15
        can.setFont('Times-Bold',12)
        can.drawString(380,r,"Totale imposte")
        can.setFont('Times-Roman', 12)
        can.drawRightString(550,r,'{:.2f}'.format(IVA))
        r=r-15
        can.setFont('Times-Bold',12)
        can.drawString(380,r,"Totale")
        can.setFont('Times-Roman', 12)
        can.drawRightString(550,r,duedecimali(DatiGeneraliDocumento.find('ImportoTotaleDocumento')))
        r=r-15
        DatiRitenuta = DatiGeneraliDocumento.find('DatiRitenuta')
        if DatiRitenuta != None:
            can.setFont('Times-Bold',12)
            can.drawString(380,r,"Ritenuta d'acconto")
            can.setFont('Times-Roman', 12)
            can.drawRightString(550,r,text(DatiRitenuta.find("ImportoRitenuta")))

        r=R
        DatiPagamento = root.find('FatturaElettronicaBody/DatiPagamento')
        if DatiPagamento != None:
            #can.line(40,r+20,240,r+20)
            can.setFont('Times-Bold',12)
            can.drawString(40,r,"Condizioni di pagamento")
            can.setFont('Times-Roman', 12)
            CondizioniPagamento=text(DatiPagamento.find("CondizioniPagamento"))
            if CondizioniPagamento in CondPag:CondizioniPagamento+" ("+CondPag[CondizioniPagamento]+")"
            can.drawString(180,r,CondizioniPagamento)
            r=r-15
            can.setFont('Times-Bold',12)
            can.drawString(40,r,"Modalità di pagamento")
            can.setFont('Times-Roman', 12)
            ModalitaPagamento=text(DatiPagamento.find("DettaglioPagamento/ModalitaPagamento"))
            if ModalitaPagamento in ModPag:ModalitaPagamento+=" ("+ModPag[ModalitaPagamento]+")"
            can.drawString(180,r,ModalitaPagamento)
            r=r-15
            can.setFont('Times-Bold',12)
            can.drawString(40,r,"IBAN")
            can.setFont('Times-Roman', 12)
            can.drawString(180,r,text(DatiPagamento.find("DettaglioPagamento/IBAN")))
            r=r-15
            can.setFont('Times-Bold',12)
            can.drawString(40,r,"Scadenza pagamento")
            can.setFont('Times-Roman', 12)
            data_scadenza=DatiPagamento.find("DettaglioPagamento/DataScadenzaPagamento")
            can.drawString(180,r,data(data_scadenza))
            if data_scadenza!=None:registrazione.data_scadenza=datetime.strptime(data_scadenza.text,"%Y-%m-%d").date()
            else:registrazione.data_scadenza=None
            r=r-15
            can.setFont('Times-Bold',12)
            can.drawString(40,r,"Totale da pagare")
            can.setFont('Times-Roman', 12)
            can.drawString(180,r,text(DatiPagamento.find("DettaglioPagamento/ImportoPagamento")))

        can.showPage()
        can.save()

        with open(filename2, 'rb') as bites:
            dati=io.BytesIO(bites.read())
        allegato=Allegato(registrazione=registrazione, nome=nome+".pdf", binario=dati.read())
        db.session.add(allegato)
        os.remove(filename2)

        dom = etree.parse(filename)
        xslt =etree.parse(os.path.join(here, "Foglio_di_stile_fatturaordinaria_v1.2.1.xsl"))
        transform = etree.XSLT(xslt)
        newdom = transform(dom)

        out_file=open(os.path.join(here, 'FATTURA.html'),"wb")
        out_file.write(etree.tostring(newdom, pretty_print=True))
        out_file.close()

        with open(os.path.join(here, 'FATTURA.html'), 'rb') as bites:
            dati=io.BytesIO(bites.read())
        allegato=Allegato(registrazione=registrazione, nome=nome+".html", binario=dati.read())
        db.session.add(allegato)

        allegati = root.findall('FatturaElettronicaBody/Allegati')
        for allegato in allegati:
            filen=text(allegato.find('NomeAttachment'))
            attach = allegato.find('Attachment').text
            base64_img_bytes = attach.encode('utf-8')
            decoded_image_data = base64.decodebytes(base64_img_bytes)
            allegato=Allegato(registrazione=registrazione, nome=filen, binario=decoded_image_data)
            db.session.add(allegato)
        os.remove(filename)
        db.session.commit()
        flash('La fattura elettronica è stata importata')
    unlock()
    return redirect(url_for('sdi_in'))
    #return redirect(url_for('registrazione', id=registrazione.id))

@app.route('/check_sdi')
@login_required
def check_sdi():
    return render_template('wait.html', link="check_sdi_")

@app.route('/check_sdi_')
@login_required
def check_sdi_():#scarica email da PEC e popola i records sdi
    lock()
    impostazioni=Impostazioni.query.get(1)
    imap = imaplib.IMAP4_SSL(impostazioni.imap_server)
    imap.login(impostazioni.imap_user, impostazioni.imap_pwd)
    status, messages = imap.select("INBOX")
    messages = int(messages[0])
    n=0
    (retcode, messages) = imap.search(None, '(UNSEEN)')
    if retcode == 'OK':
        for num in messages[0].split() :
            print ('Processing ')
            n=n+1
            res, msg = imap.fetch(num,'(RFC822)')
            for response in msg:
                if isinstance(response, tuple):
                    msg = email.message_from_bytes(response[1])
                    subject = decode_header(msg["Subject"])[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode()
                    print("Subject:", subject)
                    data = decode_header(msg["Date"])[0][0]
                    sdi=Sdi(nome=subject, timestamp=email.utils.parsedate_to_datetime(data), inbox=True)
                    db.session.add(sdi)
                    if subject[:29]=="POSTA CERTIFICATA: Invio File":sdi.fattura=True
                    if subject[:13]=="ACCETTAZIONE:":
                        S=Sdi.query.filter(Sdi.nome==subject[-23:]).first()#cerca nel caso sia .xml
                        if S==None:S=Sdi.query.filter(Sdi.nome==subject[-27:-4]).first()#cerca nel caso sia .p7m
                        if S!=None:sdi.registrazione=S.registrazione
                    if subject[:9]=="CONSEGNA:":
                        S=Sdi.query.filter(Sdi.nome==subject[-23:]).first()#cerca nel caso sia .xml
                        if S==None:S=Sdi.query.filter(Sdi.nome==subject[-27:-4]).first()#cerca nel caso sia .p7m
                        if S!=None:
                            sdi.registrazione=S.registrazione
                            sdi.registrazione.stato="Inviato"
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            if "attachment" in content_disposition:
                                filename = part.get_filename()
                                if (filename[-3:].lower()=="xml" or filename[-3:].lower()=="p7m"):
                                    allegato=Allegato(sdi=sdi, nome=filename, binario=part.get_payload(decode=True))
                                    db.session.add(allegato)
                                if filename[-3:].lower()=="xml" and filename[-10:-8]=="RC":
                                    S=Sdi.query.filter(Sdi.nome==filename[:19]+".xml").first()
                                    if S!=None:
                                        sdi.registrazione=S.registrazione
                                        sdi.registrazione.stato="Consegnato"
                                if filename[-3:].lower()=="xml" and filename[-10:-8]=="MC":
                                    S=Sdi.query.filter(Sdi.nome==filename[:19]+".xml").first()
                                    if S!=None:
                                        sdi.registrazione=S.registrazione
                                        sdi.registrazione.stato="Accettato"
                                if filename[-3:].lower()=="xml" and filename[-10:-8]=="NS":
                                    S=Sdi.query.filter(Sdi.nome==filename[:19]+".xml").first()
                                    if S!=None:
                                        sdi.registrazione=S.registrazione
                                        sdi.registrazione.stato="Scartato"
                                if filename[-3:].lower()=="xml" and filename[-10:-8]=="NE":#Notifica esito fattura verso PA
                                    S=Sdi.query.filter(Sdi.nome==filename[:19]+".xml").first()
                                    if S!=None:
                                        sdi.registrazione=S.registrazione
                                if filename[-3:].lower()=="xml" and filename[-10:-8]=="DT":#Notifica decorrenza termini fattura verso PA
                                    S=Sdi.query.filter(Sdi.nome==filename[:19]+".xml").first()
                                    if S!=None:
                                        sdi.registrazione=S.registrazione
                    for a in sdi.allegato:
                        if a.nome[-8:].lower()==".xml.p7m":
                            nome=a.nome
                            filename=os.path.join(here,nome)
                            f = open(filename, 'wb')
                            f.write(a.binario)
                            f.close()
                            cmd = ["openssl", "smime", "-verify", "-inform", "DER", "-in", filename, "-noverify", "-out", filename[:-4]]
                            call(cmd)
                            if not os.path.isfile(filename[:-4]):
                                cmd = ["openssl", "cms", "-verify", "-inform", "DER", "-in", filename, "-noverify", "-out", filename[:-4]]
                                call(cmd)
                            if not os.path.isfile(filename[:-4]):
                                data = open(filename).read()
                                os.remove(filename)
                                decoded = base64.b64decode(data)
                                f = open(filename, 'wb')
                                f.write(decoded)
                                f.close()
                                cmd = ["openssl", "smime", "-verify", "-inform", "DER", "-in", filename, "-noverify", "-out", filename[:-4]]
                                call(cmd)
                            if not os.path.isfile(filename[:-4]):
                                cmd = ["openssl", "cms", "-verify", "-inform", "DER", "-in", filename, "-noverify", "-out", filename[:-4]]
                                call(cmd)


# Concordo, la mia procedura con gli xml.p7m per esteso fa i seguenti tentativi:
# 1)openssl smime
# 2)openssl cms
# 3)base -d e se ha successo di nuovo la sequenza
# 3.1)openssl smime
# 3.2)openssl cms

# Forse non è efficiente ma per ora mi ha sempre funzionato…

# import base64
# >>> data = open("IT07441150963_H00DY.xml.p7m", "r").read()
# >>> decoded = base64.b64decode(data)
# >>> f = open("test.xml", 'wb')
# >>> f.write(decoded)
# >>> f.close()


                            os.remove(filename)
                            filename = filename[:-4]
                            nome = nome[:-4]
                            with open(filename, 'rb') as bites:
                                dati=io.BytesIO(bites.read())
                            allegato=Allegato(sdi=sdi, nome=nome, binario=dati.read())
                            os.remove(filename)
                            db.session.add(allegato)
                    db.session.commit()
    imap.close()
    imap.logout()
    flash('Il sistema di interscambio è stato interrogato')
    unlock()
    return redirect(url_for('sdi_in'))

def text(v):
    if v == None: return ""
    else: return v.text

def data(d):
    if d == None: return ""
    else:
        d=d.text
        anno=d[0:4]
        mese=d[5:7]
        giorno=d[8:10]
        d=giorno+"/"+mese+"/"+anno
        return d

def duedecimali(n):
    if n == None: return ""
    else:
        n=float(n.text)
        return '{:.2f}'.format(n)

def align(n):
    if n == None: return ""
    else:
        n=float(n.text)
        a=str(n)
        b=a.split(".")
        for i in range(8-len(b[1])):
            a=a+" "
        return a
# S D I #########################################################################
