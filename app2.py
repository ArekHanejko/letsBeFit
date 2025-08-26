from flask import Flask, render_template
from flask import Flask, render_template, session, request, redirect, url_for,send_file
from flask_session import Session
import hashlib
import psycopg2
import os
from paypalrestsdk import Payment
import paypalrestsdk
from flask_paginate import Pagination, get_page_args
from flask_mail import Mail, Message
import random
import string
from itsdangerous import URLSafeTimedSerializer #x
from itsdangerous import BadSignature, SignatureExpired
from flask_wtf.csrf import CSRFProtect
def dbConnect():
    dbConnection = psycopg2.connect(host=os.getenv("DB_HOST"),database=os.getenv("DB_DATABASE"),user=os.getenv("DB_USER"),password=os.getenv("DB_PASSWORD"), sslmode=os.getenv("DB_SSLMODE"))
    return dbConnection

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
csrf = CSRFProtect(app)


# Inicjalizacja klienta PayPal API
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")  
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")  
paypal_mode = os.getenv("PAYPAL_MODE", "sandbox")  
paypalrestsdk.configure({
    "mode": paypal_mode,
    "client_id": PAYPAL_CLIENT_ID,
    "client_secret": PAYPAL_CLIENT_SECRET
})

app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER")
app.config['MAIL_PORT'] = os.getenv("MAIL_PORT") 
app.config['MAIL_USE_TLS'] = os.getenv("MAIL_USE_TLS")
app.config['MAIL_USE_SSL'] = os.getenv("MAIL_USE_SSL")
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
mail = Mail(app) 

PER_PAGE = 9
# Inicjalizacja serializera do tworzenia tokenów resetowania hasła
serializer = URLSafeTimedSerializer(app.secret_key) #x
def generate_token(length=20):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

@app.route('/')
def index():
	msg=''
	if msg in request.args:
		msg=request.args['msg']
	return render_template("index.html",msg=msg)
@app.route('/karnety')
def karnety():
	if 'login'  in session:
		if session['rola'] not in ('uzytkownik'):
			return redirect('/')
	
	dbConnection = dbConnect()
	dbCursor = dbConnection.cursor()
	dbCursor.execute("SELECT cena from karnet_ceny order by cena asc");
	res = dbCursor.fetchall()
	normal = res[0][0]
	pro = res[1][0]
	max = res[2][0]
	
	dbConnection.commit()
	dbCursor.close()
	dbConnection.close()

	return render_template("karnety.html",normal=normal, pro=pro,max=max)

#@app.route('/logowanie')
#def logowanie():
#	if 'login' in session:
#		return redirect("/")
#	return render_template("logowanie.html")
@app.route('/logowanie', methods=["POST","GET"])
def logowanie_action():
	if 'login' in session:
		return redirect("/")
	if request.method == "POST":
		login = request.form["login"].lower()
		haslo = request.form["haslo"]
		if login=="" or haslo=="":
			msg = "Nie wszystkie pola zostały wypełnione"
		else:
			haslo = hashlib.sha256(haslo.encode('utf-8')).hexdigest()
			dbConnection = dbConnect()
			dbCursor = dbConnection.cursor()
			dbCursor.execute("SELECT id_uzytkownika, haslo, rola, weryfikacja FROM uzytkownicy WHERE login = '{}'".format(login))
			haslo2 = dbCursor.fetchall()
			if len(haslo2)==0 or haslo!=haslo2[0][1]:
				msg = "Błędne dane logowania"
				return render_template("logowanie.html", msg=msg)
			else:
				if haslo2[0][3] == False:
					msg = 'Konto nie zostało jeszcze aktywowane. Zaloguj się na pocztę i wejdz w link aktywacyjny.'
					return render_template('logowanie.html',msg=msg)
				if haslo2[0][2] == 'ban':
					msg = 'Konto zostało zbanowane.'
					return render_template('logowanie.html', msg=msg)
				session['login'] = login
				session['userid'] = haslo2[0][0]
				session['rola'] = haslo2[0][2]
				return redirect("/")
		return render_template("logowanie.html", msg=msg)	
	return render_template("logowanie.html")

#@app.route('/rejestracja')
#def rejestracja():
#	if 'login' in session:
#		return redirect("/")
#	return render_template("rejestracja.html")
	
@app.route('/rejestracja', methods=['POST','GET'])
def rejestracja():
	if 'login' in session:
		return redirect("/")
	msg=''
	if request.method == "POST":
		login = request.form["login"].lower()
		haslo = request.form["haslo"]
		haslo2 = request.form["haslo2"]
		imie = request.form["imie"]	
		nazwisko = request.form["nazwisko"]
		nr_tel = request.form["nr_tel"]
		plec = request.form["plec"]
		
		if haslo != haslo2:
			msg = "Hasła nie są takie same"
		elif login=="" or haslo=="" or haslo2=="":
			msg = "Nie wszystkie pola zostały wypełnione"
		else:
			dbConnection = dbConnect()
			dbCursor = dbConnection.cursor()

			dbCursor.execute("SELECT login FROM uzytkownicy WHERE login = '{}';".format(login))
			check = dbCursor.fetchall()
			if len(check)!=0:
				msg = "Istnieje już użytkownik o podanej nazwie"
				return render_template("rejestracja.html", msg=msg)
			else:
				
				confirmation_token = generate_token()
				
				haslo = hashlib.sha256(haslo.encode('utf-8')).hexdigest()
				dbCursor.execute('''INSERT INTO uzytkownicy VALUES (default,%s,%s,%s, %s, %s,%s, CURRENT_DATE,default,default,%s)''', (imie, nazwisko, nr_tel, login, haslo, plec,confirmation_token))
				dbConnection.commit()
				msg = Message('Potwierdzenie rejestracji', sender='letsbefit.silownia@gmail.com', recipients=[login])
				msg.body = f'Kliknij poniższy link, aby potwierdzić rejestrację: {url_for("confirm", token=confirmation_token, _external=True)}'
				mail.send(msg)
				msg = "Konto utworzone prawidłowo, aby móc się zalogować wejdź w link aktywacyjny wysłany na podanego maila"
			dbCursor.close()
			dbConnection.close()
			return render_template("index.html",msg=msg)
	
	return render_template("rejestracja.html",msg=msg)



@app.route('/confirm/<token>')
def confirm(token):
    # Znajdź użytkownika po tokenie
	dbConnection = dbConnect()
	dbCursor = dbConnection.cursor()
	dbCursor.execute("SELECT * FROM uzytkownicy WHERE token_potwierdzajacy = %s", (token,))
	user = dbCursor.fetchone()

	if user:
        # Zaktualizuj status potwierdzenia
		dbCursor.execute("UPDATE uzytkownicy SET weryfikacja = true WHERE id_uzytkownika = %s", (user[0],))
		dbConnection.commit()

		msg='Rejestracja potwierdzona. Możesz się teraz zalogować.'
	else:
		msg='Błąd potwierdzenia rejestracji. Spróbuj ponownie lub skontaktuj się z administratorem.'
	
	return redirect(url_for('index',msg=msg))


@app.route('/reset_hasla', methods=['GET', 'POST'])
def reset_hasla():
	if request.method == 'POST':
		email = request.form['email']
		dbConnection = dbConnect()
		dbCursor = dbConnection.cursor()
		dbCursor.execute("SELECT * FROM uzytkownicy WHERE login = 'arekimmobile@gmail.com'")  #%s", (email,))
		user = dbCursor.fetchone()

		if user:
			token = serializer.dumps(email, salt='reset-hasla-salt')
			msg = Message('Resetowanie hasła', sender='letsbefit.silownia@gmail.com', recipients=[email])
			#reset_url = url_for('reset_hasla_potwierdzenie', token=token, _external=True)
			confirmation_url = url_for('reset_hasla_potwierdzenie', token=token, _external=True)
			msg.body = f'Aby zresetować hasło, kliknij poniższy link:\n{confirmation_url}'
			mail.send(msg)
			msgSuccess = 'Link resetujący hasło został wysłany na podany adres e-mail.'
			return render_template('reset_hasla.html',msgSuccess=msgSuccess)

	return render_template('reset_hasla.html')

# Endpoint do potwierdzenia resetowania hasła
@app.route('/reset_hasla_potwierdzenie/<token>', methods=['GET', 'POST'])
def reset_hasla_potwierdzenie(token):
	try:
		email = serializer.loads(token, salt='reset-hasla-salt', max_age=3600)
    
	except Exception as e:
		print(f"Błąd przy odczycie tokenu: {e}")
		return redirect(url_for('index'))

	if request.method == 'POST':
		nowe_haslo = request.form['nowe_haslo']
		nowe_haslo2 = request.form['nowe_haslo2']

		if nowe_haslo != nowe_haslo2:
			msg = 'Hasła nie są takie same'
			return render_template('reset_hasla_potwierdzenie.html', token=token, email=email,msg=msg)
		else:
			nowe_haslo = request.form['nowe_haslo']
			nowe_haslo_hash = hashlib.sha256(nowe_haslo.encode('utf-8')).hexdigest()
			dbConnection = dbConnect()
			dbCursor = dbConnection.cursor()
			dbCursor.execute("UPDATE uzytkownicy SET haslo = %s WHERE login ='arekimmobile@gmail.com'",(nowe_haslo_hash,))# %s", (nowe_haslo_hash, email))
			dbConnection.commit()
			msg= 'Hasło zostało zresetowane. Możesz się teraz zalogować.'
			return redirect(url_for('logowanie_action'))

	return render_template('reset_hasla_potwierdzenie.html', token=token,email=email)



@app.route('/wyloguj')
def wyloguj():
	if 'login' in session:
		session.clear()
	return redirect("/")




# Trasa do przetwarzania płatności PayPal
@app.route('/pay', methods=['POST','GET'])
def pay():
	if request.method=='POST':
		powod = request.form["zakup"]
		dbConnection = dbConnect()
		dbCursor = dbConnection.cursor()
		#dbCursor.execute("INSERT INTO karnet_ceny VALUES ({},50)".format(powod))
		#wartosc = request.form["cena_zajec"]
		if powod == "karnet":
			kupiony_produkt = request.form["typ_karnetu"]
			wartosc = request.form["cena"]
			data_rozpoczecia = request.form["data_rozpoczecia"]
			data_konca = request.form["data_konca"]
			url_arguments = {
            	'data_konca': data_konca,
            	'typ_karnetu': kupiony_produkt,
            	'wartosc': wartosc,
            	'data_rozpoczecia': data_rozpoczecia,
				'zakup': powod
        	}
		elif powod == "zajecia":
			id_zajec = request.form["id_zajec"]
			wartosc = request.form["cena_zajec"]
			kupiony_produkt = request.form["nazwa_zajec"]
			url_arguments = {
            	'id_zajec': id_zajec,
            	'wartosc': wartosc,
            	'kupiony_produkt': kupiony_produkt,
				'zakup': powod
        	}
		dbConnection = dbConnect()
		dbCursor = dbConnection.cursor()
		dbCursor.execute("SELECT imie, nazwisko FROM uzytkownicy WHERE id_uzytkownika = '{}';".format(session["userid"]))
		res =  dbCursor.fetchall()
		dbConnection.commit()
		dbCursor.close()
		dbConnection.close()
		imie = res[0][0]
		nazwisko = res[0][1]
    	# Tworzenie płatności PayPal
		payment = Payment({
    	"intent": "sale",
    	"payer": {
        	"payment_method": "paypal",
        	"payer_info": {
           		"first_name": imie,
            	"last_name": nazwisko
        	}
    	},
    	"redirect_urls": {
            	"return_url": url_for('success', _external=True, **url_arguments),
				"cancel_url": url_for('cancel', _external=True)
    	},
    	"transactions": [{
        	"item_list": {
            	"items": [{
                	"name": kupiony_produkt,
                	"price": wartosc,
                	"currency": "PLN",
                	"quantity": 1,
				
            	}]
        	},
        	"amount": {
            	"total": wartosc,
            	"currency": "PLN"
        	},
        	"description": "Opłacenie zakupu karnetu/zajęć"
    	}]
	})

    	# Utwórz płatność
		if payment.create():
		
			return redirect(payment.links[1].href)
		else:
			return 'Błąd podczas tworzenia płatności PayPal: %s' % payment.error
	else:
		return redirect("/")	
# Trasa po udanej płatności
@app.route('/success')
def success():
	
	dbConnection = dbConnect()
	dbCursor = dbConnection.cursor()
	wartosc = request.args['wartosc']
	zakup=request.args["zakup"]
	if(zakup=="karnet"):
		typ_karnetu = request.args['typ_karnetu']
		data_rozpoczecia = request.args['data_rozpoczecia']
		data_konca = request.args['data_konca']
		dbCursor.execute('''INSERT INTO karnet VALUES (default,%s,%s,%s, CURRENT_DATE, %s, %s)''', (session['userid'], typ_karnetu, wartosc,data_rozpoczecia,data_konca))
	elif(zakup=="zajecia"):
		id_zajec = request.args["id_zajec"]
		id_uzytkownika = session["userid"]
		dbCursor.execute('''INSERT INTO zajecia_zapisy VALUES (default,%s,%s, CURRENT_DATE)''', (id_uzytkownika, id_zajec))

	dbConnection.commit()
	dbCursor.close()
	dbConnection.close()
	msg = "Płatność została zrealizowana"

	
	return redirect(url_for('payment_success'))
@app.route('/payment_success')
def payment_success():
	msg = "Płatność została zrealizowana"
	return render_template("index.html", msg=msg)

# Trasa po anulowanej płatności
@app.route('/cancel')
def cancel(): 
	msg = 'Płatność PayPal została anulowana.'
	return render_template("index.html", msg=msg)

@app.route('/payment_summary', methods=['GET', 'POST'])
def payment_summary():
	if request.method == 'POST':
		dbConnection = dbConnect()
		dbCursor = dbConnection.cursor()
		zakup = request.form["zakup"]
		if zakup == "karnet":
			typ_karnetu = request.form["ticketType"]
			data_rozpoczecia = request.form["inputDate"]
			data_konca = request.form["inputEndDate"]
			dbCursor.execute("SELECT cena FROM karnet_ceny WHERE typ_karnetu = '{}'".format(typ_karnetu))
			res = dbCursor.fetchall()
			cena=res[0][0]
		elif zakup == "zajecia":
			id_zajec = request.form["id_zajec"]
			wartosc = request.form["cena_zajec"]
			if session['rola']=='recepcjonista':
				klient=request.form['obslugiwany_uzytkownik']
				dbCursor.execute("insert into zajecia_zapisy values(DEFAULT,9999,%s,CURRENT_DATE)",(id_zajec,))

			#dbCursor.execute("insert into karnet_ceny values('xdd',{})".format(wartosc))

			kupiony_produkt = request.form["nazwa_zajec"]
		login= session['login']
		if session['rola']=='recepcjonista':
			login = klient
		dbCursor.execute("SELECT imie,nazwisko FROM uzytkownicy WHERE login = '{}'".format(login))
		userData = dbCursor.fetchall()
		imie = userData[0][0]
		nazwisko = userData[0][1]
		dbConnection.commit()
		dbCursor.close()
		dbConnection.close()
		if zakup=="karnet":
			return render_template("payment_summary.html",imie=imie, nazwisko=nazwisko, typ_karnetu=typ_karnetu,cena=cena, data_rozpoczecia=data_rozpoczecia, data_konca=data_konca, zakup=zakup)
		return render_template("payment_summary.html",imie=imie, nazwisko=nazwisko, id_zajec=id_zajec, wartosc=wartosc, kupiony_produkt=kupiony_produkt,zakup=zakup,login=login)
	else:
		return redirect("/")
@app.route('/profil')
def profil():
	if 'login' not in session:
		return redirect('/')
	page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
	userid = session['userid']
	login = session['login']

	dbConnection = dbConnect()
	dbCursor = dbConnection.cursor()
	dbCursor.execute("SELECT id_uzytkownika, imie, nazwisko, nr_tel, login, plec, data_dolaczenia FROM uzytkownicy WHERE login = '{}'".format(login))
	res = dbCursor.fetchall()
	dbCursor.execute("SELECT uzytkownicy.id_uzytkownika FROM uzytkownicy, karnet WHERE uzytkownicy.id_uzytkownika=karnet.id_wlasciciela and (current_date between karnet.data_rozpoczecia_karnetu and karnet.data_zakonczenia_karnetu) and uzytkownicy.id_uzytkownika = '{}' ".format(userid))
	res2 = dbCursor.fetchall()
	if(res2):	status_karnetu="aktywny"
	else:	status_karnetu="nieaktywny"
	# Zlicz wszystkie rekordy przed zastosowaniem paginacji
	dbCursor.execute("SELECT idkarnetu, typ_karnetu, wartosc, data_zakupu, data_rozpoczecia_karnetu, data_zakonczenia_karnetu FROM karnet WHERE id_wlasciciela = %s ORDER BY data_zakupu desc,idkarnetu desc", (userid,))
	total_records = dbCursor.rowcount
	# Ograniczenie zapytania do odpowiedniej strony
	pagination = Pagination(page=page, per_page=per_page, total=total_records, css_framework='bootstrap5')
    
	dbCursor.execute("SELECT idkarnetu, typ_karnetu, wartosc, data_zakupu, data_rozpoczecia_karnetu, data_zakonczenia_karnetu FROM karnet WHERE id_wlasciciela = %s ORDER BY data_zakupu desc, idkarnetu desc LIMIT %s OFFSET %s", (userid, PER_PAGE, offset))
	res3 = dbCursor.fetchall()
	karnety_ids=[]
	if 'login' in session:
			dbCursor.execute("SELECT idkarnetu FROM karnet WHERE id_wlasciciela = %s and current_date between karnet.data_rozpoczecia_karnetu and karnet.data_zakonczenia_karnetu", (session['userid'],))
			karnety_ids = [result[0] for result in dbCursor.fetchall()]
	dbConnection.commit()
	dbCursor.close()
	dbConnection.close()

	return render_template("profil.html", pagination=pagination,karnety_ids=karnety_ids, ticket_list=res3, id=res[0][0], imie=res[0][1], nazwisko=res[0][2], nr_tel=res[0][3], login=res[0][4], plec=res[0][5], data_dolaczenia=res[0][6], status_karnetu=status_karnetu)


@app.route('/zajecia')
def zajecia():
	#if 'login' not in session:
	#	return redirect('/')
		#return redirect('/')
		if 'login' in session and session['rola'] == 'trener':
			return redirect('/')
		msg = request.args.get('msg')
		page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
		uzytkownicy_lista = ''
		dbConnection = dbConnect()
		dbCursor = dbConnection.cursor()
		dbCursor.execute("select nazwa_zajec, opis_zajec, czas_zajec, data_zajec, ilosc_miejsc_na_zajecia, id_trenera, uzytkownicy.imie, uzytkownicy.nazwisko from zajecia, uzytkownicy where uzytkownicy.id_uzytkownika=zajecia.id_trenera and data_zajec BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '1 MONTH'  ")
		total_records = dbCursor.rowcount
		pagination = Pagination(page=page, per_page=per_page, total=total_records, css_framework='bootstrap4')
		#dbCursor.execute("select nazwa_zajec, opis_zajec, data_zajec, godzina_zajec, czas_zajec, cena_zajec, ilosc_miejsc_na_zajecia, id_trenera,uzytkownicy.imie, uzytkownicy.nazwisko, id_zajec from zajecia, uzytkownicy where uzytkownicy.id_uzytkownika=zajecia.id_trenera ORDER BY data_zajec,czas_zajec desc LIMIT %s OFFSET %s   ",(PER_PAGE, offset))
		dbCursor.execute("SELECT z.nazwa_zajec, z.opis_zajec, z.data_zajec, z.godzina_zajec, z.czas_zajec, z.cena_zajec, z.ilosc_miejsc_na_zajecia, z.id_trenera, u.imie, u.nazwisko,z.id_zajec, COUNT(zz.id_zajec) AS liczba_zapisow FROM zajecia z JOIN uzytkownicy u ON u.id_uzytkownika = z.id_trenera LEFT JOIN zajecia_zapisy zz ON zz.id_zajec = z.id_zajec where  z.data_zajec BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '1 MONTH' GROUP BY z.id_zajec, u.imie, u.nazwisko ORDER BY z.data_zajec ASC, z.godzina_zajec ASC  LIMIT %s OFFSET %s", ( PER_PAGE, offset))

		res = dbCursor.fetchall()
		if 'login' in session:
			dbCursor.execute("SELECT id_zajec FROM zajecia_zapisy WHERE id_uczestnika = %s", (session['userid'],))
			zajecia_zapisy_ids = [result[0] for result in dbCursor.fetchall()]
	
	
		# rola=session['rola']
		# if(rola == 'admin'):
		# 	dbCursor.execute("SELECT id_uzytkownika, imie, nazwisko, login FROM uzytkownicy")
		# 	uzytkownicy_lista = dbCursor.fetchall()

		dbConnection.commit()
		dbCursor.close()
		dbConnection.close()
		#zakup = request.form["zakup"]
		if 'login' not in session:
			return render_template("zajecia.html", lista_zajec = res, pagination=pagination, msg=msg,  uzytkownicy_lista=uzytkownicy_lista)

		else:
			return render_template("zajecia.html", lista_zajec = res, pagination=pagination, msg=msg,  zajecia_zapisy_ids= zajecia_zapisy_ids,uzytkownicy_lista=uzytkownicy_lista)

@app.route('/profil_trenera')
def profil_trenera():
	if 'login' not in session:
		return redirect('/')
	elif session['rola'] != 'trener':
		return redirect('/')
	page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
	userid = session['userid']
	login = session['login']

	dbConnection = dbConnect()
	dbCursor = dbConnection.cursor()
	dbCursor.execute("SELECT id_uzytkownika, imie, nazwisko, nr_tel, login, plec, data_dolaczenia FROM uzytkownicy WHERE login = '{}'".format(login))
	res = dbCursor.fetchall()
	dbCursor.execute("SELECT uzytkownicy.id_uzytkownika FROM uzytkownicy, karnet WHERE uzytkownicy.id_uzytkownika=karnet.id_wlasciciela and (current_date between karnet.data_rozpoczecia_karnetu and karnet.data_zakonczenia_karnetu) and uzytkownicy.id_uzytkownika = '{}' ".format(userid))
	res2 = dbCursor.fetchall()
	if(res2):	status_karnetu="aktywny"
	else:	status_karnetu="nieaktywny"
    # Zlicz wszystkie rekordy przed zastosowaniem paginacji
	dbCursor.execute("SELECT nazwa_zajec, opis_zajec, data_zajec, godzina_zajec, czas_zajec, id_zajec FROM zajecia WHERE id_trenera = %s and data_zajec>CURRENT_DATE  ORDER BY data_zajec asc, godzina_zajec asc", (userid,))
	total_records = dbCursor.rowcount
    # Ograniczenie zapytania do odpowiedniej strony
	pagination = Pagination(page=page, per_page=per_page, total=total_records, css_framework='bootstrap4')
    
	dbCursor.execute("SELECT nazwa_zajec, opis_zajec, data_zajec, godzina_zajec, czas_zajec, id_zajec FROM zajecia WHERE id_trenera = %s and data_zajec>CURRENT_DATE ORDER BY data_zajec asc, godzina_zajec asc  LIMIT %s OFFSET %s", (userid, PER_PAGE, offset))

	res3 = dbCursor.fetchall()

	dbConnection.commit()
	dbCursor.close()
	dbConnection.close()

	return render_template("profil_trenera.html", pagination=pagination, lista_zajec=res3, id=res[0][0], imie=res[0][1], nazwisko=res[0][2], nr_tel=res[0][3], login=res[0][4], plec=res[0][5], data_dolaczenia=res[0][6])

@app.route('/dodaj_zajecia', methods = ['POST','GET'])
def dodaj_zajecia():
	if request.method=='POST':
		nazwa_zaj = request.form['nazwa_zajec']
		opis_zaj = request.form['opis_zajec']
		data_zaj = request.form['data_zajec']
		godz_zaj = request.form['godz_zajec']
		czas_zaj = request.form['czas_zajec']
		cena_zaj = request.form['cena_zajec']
		liczba_miejsc = request.form['liczba_miejsc']
		userid = session['userid']
		dbConnection = dbConnect()
		dbCursor = dbConnection.cursor()
		dbCursor.execute("insert into zajecia values(DEFAULT, %s, %s, %s, %s, %s, %s, %s, %s )",(userid, nazwa_zaj, opis_zaj, godz_zaj, czas_zaj,cena_zaj,data_zaj,liczba_miejsc))
		msg="Wydarzenie zostało dodane"
		dbConnection.commit()
		dbCursor.close()
		dbConnection.close()
		return redirect(url_for('zajecia',msg=msg))
	else:
		return redirect('/')
@app.route('/panel_admina')
def panel_admina():
	if 'login' not in session:
		return redirect('/')
	elif session['rola'] != 'admin':
		return redirect('/')
	msgSuccess=' '
	msgWarning=' '
	#msgWarning=request.args['msgWarning']
	#msgSuccess=request.args['msgSuccess']
	dbConnection = dbConnect()
	dbCursor = dbConnection.cursor()
	dbCursor.execute(" select * from karnet_ceny order by cena desc;")
	res = dbCursor.fetchall()
	dbCursor.execute("SELECT id_uzytkownika, imie, nazwisko, login FROM uzytkownicy order by id_uzytkownika asc")
	uzytkownicy_lista = dbCursor.fetchall()
	dbConnection.commit()
	dbCursor.close()
	dbConnection.close()
	return render_template("panel_admina.html", max=res[0][1],pro=res[1][1],normal=res[2][1],msgWarning=msgWarning,msgSuccess=msgSuccess,uzytkownicy_lista=uzytkownicy_lista)

@app.route('/zmien_ceny',methods = ['POST','GET'])
def zmien_ceny():
	if request.method=='POST':
		dbConnection = dbConnect()
		dbCursor = dbConnection.cursor()
		nowa_cena_max = request.form['nowa_cena_max']
		nowa_cena_pro = request.form['nowa_cena_pro']
		nowa_cena_normal = request.form['nowa_cena_normal']

		dbCursor.execute("update karnet_ceny set cena=%s where typ_karnetu='NORMAL';",(nowa_cena_normal,))
		dbCursor.execute("update karnet_ceny set cena=%s where typ_karnetu='PRO';",(nowa_cena_pro,))
		dbCursor.execute("update karnet_ceny set cena=%s where typ_karnetu='MAX';",(nowa_cena_max,))
		dbConnection.commit()
		dbCursor.close()
		dbConnection.close()
		msg = "Zmiany zostały zapisane"
		return render_template("panel_admina.html",msg=msg,nowa_cena_max=nowa_cena_max, nowa_cena_normal=nowa_cena_normal, nowa_cena_pro=nowa_cena_pro)
	else:
		return redirect('/')
@app.route('/zmien_role',methods = ['POST','GET'])
def zmien_role():
	if request.method=='POST':
		dbConnection = dbConnect()
		dbCursor = dbConnection.cursor()
		nowa_rola=request.form['rola']
		uzytkownik_z_nowa_rola=request.form['id_uzytkownika']
		msgWarning = ''
		msgSuccess = ''
		msg = ''
		dbCursor.execute("select id_uzytkownika from uzytkownicy;")
		listaId = [str(item[0]) for item in dbCursor.fetchall()]
		if uzytkownik_z_nowa_rola in listaId:
			dbCursor.execute("update uzytkownicy set rola=%s where id_uzytkownika=%s;",(nowa_rola,uzytkownik_z_nowa_rola,))
			msgSuccess = "Rola została zmieniona"
		else:
			msgWarning="Użytkownik o podanym Id nie istnieje"
			return redirect(url_for('zmiany_zapisane',msgWarning=msgWarning,msgSuccess=msgSuccess,msg=msg))
	
		dbConnection.commit()
		dbCursor.close()
		dbConnection.close()
		return redirect(url_for('zmiany_zapisane',msgSuccess=msgSuccess,msgWarning=msgWarning,msg=msg))
	else:
		return redirect('/')
@app.route('/zmiany_zapisane')
def zmiany_zapisane():
	if request.method == 'GET':
		return redirect('/')
	#max=request.args['nowa_cena_max']
	#pro=request.args['nowa_cena_pro']
	#normal=request.args['nowa_cena_normal']
	msgWarning = request.args.get('msgWarning', '')
	msgSuccess = request.args.get('msgSuccess', '')
	msg = request.args.get('msg', '')
	return render_template('panel_admina.html',msg=msg, msgSuccess=msgSuccess,msgWarning=msgWarning)#msg=msg,max=max, normal=normal, pro=pro)
@app.route('/odwolaj_zajecia', methods=['POST','GET'])
def odwolaj_zajecia():
	if request.method=='POST':
		id_zajec_do_wypisania_sie = request.form['id_zajec']
		id_uzytkownika = session['userid']
		dbConnection = dbConnect()
		dbCursor = dbConnection.cursor()
		dbCursor.execute("delete from zajecia_zapisy where id_zajec=%s and id_uczestnika=%s;",(id_zajec_do_wypisania_sie,id_uzytkownika))
		dbConnection.commit()
		dbCursor.close()
		dbConnection.close()
		msg = "Zmiany zostały zapisane"
		return redirect("/zajecia")
	else:
		return redirect('/')
#update karnet_ceny set cena=50 where typ_karnetu='NORMAL';


@app.route('/zajecia_recepcja')
def zajecia_recepcja():
	if 'login' not in session:
		return redirect('/')
	elif session['rola'] != 'recepcjonista':
		return redirect('/')
	msgWarning = request.args.get('msgWarning')
	msgSuccess = request.args.get('msgSuccess')
	page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
	uzytkownicy_lista = ''
	dbConnection = dbConnect()
	dbCursor = dbConnection.cursor()
	dbCursor.execute("select nazwa_zajec, opis_zajec, czas_zajec, data_zajec, ilosc_miejsc_na_zajecia, id_trenera, uzytkownicy.imie, uzytkownicy.nazwisko from zajecia, uzytkownicy where uzytkownicy.id_uzytkownika=zajecia.id_trenera and data_zajec BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '1 MONTH'  ")
	total_records = dbCursor.rowcount
	pagination = Pagination(page=page, per_page=per_page, total=total_records, css_framework='bootstrap4')
	#dbCursor.execute("select nazwa_zajec, opis_zajec, data_zajec, godzina_zajec, czas_zajec, cena_zajec, ilosc_miejsc_na_zajecia, id_trenera,uzytkownicy.imie, uzytkownicy.nazwisko, id_zajec from zajecia, uzytkownicy where uzytkownicy.id_uzytkownika=zajecia.id_trenera ORDER BY data_zajec,czas_zajec desc LIMIT %s OFFSET %s   ",(PER_PAGE, offset))
	dbCursor.execute("SELECT z.nazwa_zajec, z.opis_zajec, z.data_zajec, z.godzina_zajec, z.czas_zajec, z.cena_zajec, z.ilosc_miejsc_na_zajecia, z.id_trenera, u.imie, u.nazwisko,z.id_zajec, COUNT(zz.id_zajec) AS liczba_zapisow FROM zajecia z JOIN uzytkownicy u ON u.id_uzytkownika = z.id_trenera LEFT JOIN zajecia_zapisy zz ON zz.id_zajec = z.id_zajec where  z.data_zajec BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '1 MONTH' GROUP BY z.id_zajec, u.imie, u.nazwisko ORDER BY z.data_zajec ASC, z.godzina_zajec ASC  LIMIT %s OFFSET %s", ( PER_PAGE, offset))

	res = dbCursor.fetchall()
	dbCursor.execute("SELECT id_zajec FROM zajecia_zapisy WHERE id_uczestnika = %s", (session['userid'],))
	zajecia_zapisy_ids = [result[0] for result in dbCursor.fetchall()]
	
	dbCursor.execute("SELECT id_uzytkownika, imie, nazwisko, login FROM uzytkownicy order by id_uzytkownika asc")
	uzytkownicy_lista = dbCursor.fetchall()

	dbConnection.commit()
	dbCursor.close()
	dbConnection.close()
	#zakup = request.form["zakup"]

	return render_template("zajecia_recepcja.html", lista_zajec = res, pagination=pagination, msgWarning=msgWarning, msgSuccess=msgSuccess,  zajecia_zapisy_ids= zajecia_zapisy_ids,uzytkownicy_lista=uzytkownicy_lista)

@app.route('/recepcja_zapisz_na_zajecia', methods = ['POST','GET'])
def recepcja_zapisz_na_zajecia():
	if request.method=='POST':
		id_zajec = request.form['id_zajec']
		userlogin = request.form['obslugiwany_uzytkownik']
		status_oplacenia=request.form['status_oplacenia']
		msgSuccess=''
		dbConnection = dbConnect()
		dbCursor = dbConnection.cursor()
		dbCursor.execute("SELECT id_uzytkownika FROM uzytkownicy WHERE login = %s",(userlogin,))
		userid = (dbCursor.fetchall())[0][0]
		dbCursor.execute("select * from zajecia_zapisy where id_uczestnika = {} and id_zajec = {}".format(userid, id_zajec))
		res = dbCursor.fetchall()
		if (res):
			msgWarning='Użytkownik jest już zapisany na te zajęcia'
			dbCursor.execute("delete from zajecia_zapisy where id_uczestnika=9999")
			dbConnection.commit()
			return redirect(url_for('zajecia_recepcja',msgWarning=msgWarning))
		if(status_oplacenia=='oplacony'):
			dbCursor.execute("update zajecia_zapisy set id_uczestnika=%s where id_uczestnika=9999",(userid,))
			msgSuccess="Użytkownik został zapisany na zajęcia"

		elif(status_oplacenia=='nieoplacony'):
			dbCursor.execute("delete from zajecia_zapisy where id_uczestnika=9999")
			dbConnection.commit()
			dbCursor.close()
			dbConnection.close()
			#return redirect('/zajecia_recepcja')
			return redirect(url_for('zajecia_recepcja',msgSuccess=msgSuccess))
		#dbCursor.execute("insert into zajecia_zapisy values(DEFAULT, %s, %s, CURRENT_DATE )",(userid, id_zajec))
		#dbCursor.execute("update zajecia_zapisy values(DEFAULT, %s, %s, CURRENT_DATE )",(userid, id_zajec))
		dbCursor.execute("delete from zajecia_zapisy where id_uczestnika=9999")
		dbConnection.commit()
		dbCursor.close()
		dbConnection.close()
		return redirect(url_for('zajecia_recepcja',msgSuccess=msgSuccess))
	else:
		return redirect('/')

@app.route('/karnety_recepcja')
def karnety_recepcja():
	if 'login' not in session:
		return redirect('/')
	elif session['rola'] != 'recepcjonista':
		return redirect('/')
	msgSuccess = request.args.get('msgSuccess')
	dbConnection = dbConnect()
	dbCursor = dbConnection.cursor()
	dbCursor.execute("SELECT id_uzytkownika, imie, nazwisko, login FROM uzytkownicy order by id_uzytkownika asc")
	
	uzytkownicy_lista = dbCursor.fetchall()
	dbCursor.execute("SELECT cena from karnet_ceny order by cena asc");
	ceny_karnetow = dbCursor.fetchall()
	normal = ceny_karnetow[0][0]
	pro = ceny_karnetow[1][0]
	max = ceny_karnetow[2][0]
	dbConnection.commit()
	dbCursor.close()
	dbConnection.close()
	

	return render_template("karnety_recepcja.html",uzytkownicy_lista=uzytkownicy_lista, normal=normal, max=max, pro=pro, msgSuccess=msgSuccess)

@app.route('/recepcja_zapisz_karnet', methods = ['POST','GET'])
def recepcja_zapisz_karnet():
	if request.method=='POST':	
		typ_karnetu = request.form['ticketType']
		userid = request.form['obslugiwany_uzytkownik']
		data_rozpoczecia_karnetu = request.form['inputDate']
		data_wygasniecia_karnetu = request.form['inputEndDate']
		dbConnection = dbConnect()
		dbCursor = dbConnection.cursor()
		dbCursor.execute("SELECT cena from karnet_ceny where typ_karnetu=%s",(typ_karnetu,));
		wartosc = (dbCursor.fetchall())[0]
		dbCursor.execute("insert into karnet values(DEFAULT, %s, %s, %s,CURRENT_DATE ,%s,%s)",(userid, typ_karnetu, wartosc ,data_rozpoczecia_karnetu,data_wygasniecia_karnetu))
		msgSuccess="Użytkownik został zapisany na zajęcia"
		dbConnection.commit()
		dbCursor.close()
		dbConnection.close()
	
		msgSuccess="Karnet został przypisany do użytkownika"

		return render_template('karnety_recepcja.html',msgSuccess=msgSuccess)
	else:
		return redirect('/')

@app.route('/recepcja_wejscia')
def recepcja_wejscia():
	if 'login' not in session:
		return redirect('/')
	elif session['rola'] != 'recepcjonista':
		return redirect('/')
	msgSuccess = request.args.get('msgSuccess')
	msgWarning = request.args.get('msgWarning')

	dbConnection = dbConnect()
	dbCursor = dbConnection.cursor()
	dbCursor.execute("SELECT id_uzytkownika, imie, nazwisko, login FROM uzytkownicy order by id_uzytkownika asc")	
	uzytkownicy_lista = dbCursor.fetchall()	
	dbConnection.commit()
	dbCursor.close()
	dbConnection.close()
	

	return render_template("recepcja_wejscia.html", uzytkownicy_lista=uzytkownicy_lista, msgSuccess=msgSuccess,msgWarning=msgWarning)
@app.route('/recepcja_wejscia_sprawdz', methods = ['POST','GET'])
def recepcja_wejscia_sprawdz():
	if request.method=='POST':
		userid = request.form['obslugiwany_uzytkownik']
		msgWarning=''
		msgSuccess=''
		dbConnection = dbConnect()
		dbCursor = dbConnection.cursor()
		dbCursor.execute("SELECT uzytkownicy.id_uzytkownika FROM uzytkownicy, karnet WHERE uzytkownicy.id_uzytkownika=karnet.id_wlasciciela and (current_date between karnet.data_rozpoczecia_karnetu and karnet.data_zakonczenia_karnetu) and uzytkownicy.id_uzytkownika = '{}' ".format(userid))
		aktywneKarnety = dbCursor.fetchall()
		if aktywneKarnety:
			dbCursor.execute("insert into wejscia values(DEFAULT, {}, CURRENT_DATE ,CURRENT_TIME)".format(userid))
			msgSuccess="Wejscie zostało wpisane do bazy danych"

		else:
			msgWarning="Użytkownik nie posiada aktywnego karnetu"
		dbCursor.execute("SELECT id_uzytkownika, imie, nazwisko, login FROM uzytkownicy order by id_uzytkownika asc")	
		uzytkownicy_lista = dbCursor.fetchall()	
		dbConnection.commit()
		dbCursor.close()
		dbConnection.close()
	

		return redirect(url_for('recepcja_wejscia', uzytkownicy_lista=[], msgSuccess=msgSuccess,msgWarning=msgWarning))
	else:
		return redirect('/')

@app.route('/lista_uczestnikow_zajec', methods = ['POST','GET'])
def lista_uczestnikow_zajec():

	if request.method=='POST':
		id_zajec = request.form['id_zajec_do_listowania']
		dbConnection = dbConnect()
		dbCursor = dbConnection.cursor()
		dbCursor.execute("SELECT uzytkownicy.id_uzytkownika, uzytkownicy.imie, uzytkownicy.nazwisko FROM uzytkownicy, zajecia_zapisy WHERE uzytkownicy.id_uzytkownika=zajecia_zapisy.id_uczestnika and zajecia_zapisy.id_zajec= {} ".format(id_zajec))
		lista_uczestnikow = dbCursor.fetchall()
		dbCursor.execute("select nazwa_zajec, godzina_zajec, czas_zajec, data_zajec, ilosc_miejsc_na_zajecia from zajecia where id_zajec = {} ".format(id_zajec))
		dane_o_zajeciach = dbCursor.fetchall()
		dbConnection.commit()
		dbCursor.close()
		dbConnection.close()
		return render_template("lista_uczestnikow_zajec.html",id_zajec=id_zajec, dane_o_zajeciach=dane_o_zajeciach, lista_uczestnikow=lista_uczestnikow)
	else:
		return redirect("/")
	
@app.route('/statystyki')
def statystyki():

	
		dbConnection = dbConnect()
		dbCursor = dbConnection.cursor()
		dbCursor.execute("SELECT godzina, COALESCE(COUNT(id_wejscia), 0) AS liczba_wejsc FROM generate_series(0, 23) godzina LEFT JOIN wejscia ON EXTRACT(HOUR FROM godzina_wejscia) = godzina GROUP BY godzina ORDER BY godzina; ")
		res = dbCursor.fetchall()
		
		dbConnection.commit()
		dbCursor.close()
		dbConnection.close()
		return render_template("statystyki.html",res=res)
	
	
	
@app.route('/recepcja_zmiana_hasla_klienta', methods = ['POST','GET'])
def recepcja_zmiana_hasla_klienta():
	dbConnection = dbConnect()
	dbCursor = dbConnection.cursor()
	dbCursor.execute("SELECT id_uzytkownika, imie, nazwisko, login FROM uzytkownicy order by id_uzytkownika asc")	
	uzytkownicy_lista = dbCursor.fetchall()	
	if request.method=='POST':
		userid = request.form['obslugiwany_uzytkownik']
		msg=''		
		id = request.form['obslugiwany_uzytkownik']
		haslo = request.form['haslo']
		haslo2 = request.form['haslo2']
		if  haslo!=haslo2:
				msg = "Błędne dane logowania"
				dbCursor.close()
				dbConnection.close()
				return render_template("recepcja_zmiana_hasla_klienta.html", msg=msg)
		else:
			haslo = hashlib.sha256(haslo.encode('utf-8')).hexdigest()
			dbCursor.execute("update uzytkownicy set haslo = %s where id_uzytkownika=%s",(haslo,id))
			msg='Hasło zostało zmienione'
				
	else:
		msg=''
		dbConnection.commit()
		dbCursor.close()
		dbConnection.close()
		return render_template("recepcja_zmiana_hasla_klienta.html",msg=msg, uzytkownicy_lista=uzytkownicy_lista)
	dbConnection.commit()
	dbCursor.close()
	dbConnection.close()
	return render_template('recepcja_zmiana_hasla_klienta.html',msg=msg, uzytkownicy_lista=uzytkownicy_lista)

if __name__ == "__main__":
    app.run(debug=True)


