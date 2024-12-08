# -*- coding: utf-8 -*-
import sys, os
sys.path.append('/home/j/j0mutyp2/thesashki.ru/thesaski.ru') # указываем директорию с проектом
sys.path.append('/home/j/j0mutyp2/thesashki.ru/venv/lib/python3.10/site-packages') # указываем директорию с библиотеками, куда поставили Flask
from Shashki import app as application # когда Flask стартует, он ищет application. Если не указать 'as application', сайт не заработает
from werkzeug.debug import DebuggedApplication # Опционально: подключение модуля отладки
application.wsgi_app = DebuggedApplication(application.wsgi_app, True) # Опционально: включение модуля отадки
application.debug = False  # Опционально: True/False устанавливается по необходимости в отладке