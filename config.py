import os

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'koijonco824xmiufh83kj'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SEND_FILE_MAX_AGE_DEFAULT = 0

    #SMTP settings
    MAIL_PORT=465
    MAIL_USE_TLS=False
    MAIL_USE_SSL=True
    MAIL_DEBUG=False

