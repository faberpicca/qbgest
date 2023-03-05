import os

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'koijonco824xmiufh83kj'
    SQLALCHEMY_DATABASE_URI = "postgresql://user:password@myserver.it:5432/database"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SEND_FILE_MAX_AGE_DEFAULT = 0

    #SMTP settings
    MAIL_PORT=465
    MAIL_USE_TLS=False
    MAIL_USE_SSL=True
    MAIL_DEBUG=False

