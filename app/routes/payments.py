from flask import Blueprint, render_template, request, redirect, url_for, session
from paypalrestsdk import Payment
from app.models.database import dbConnect

payments_bp = Blueprint('payments', __name__)

# Trasa do przetwarzania płatności PayPal
@payments_bp.route('/pay', methods=['POST','GET'])
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
            	"return_url": url_for('payments.success', _external=True, **url_arguments),
				"cancel_url": url_for('payments.cancel', _external=True)
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
@payments_bp.route('/success')
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

	
	return redirect(url_for('payments.payment_success'))
@payments_bp.route('/payment_success')
def payment_success():
	msg = "Płatność została zrealizowana"
	return render_template("index.html", msg=msg)

# Trasa po anulowanej płatności
@payments_bp.route('/cancel')
def cancel(): 
	msg = 'Płatność PayPal została anulowana.'
	return render_template("index.html", msg=msg)

@payments_bp.route('/payment_summary', methods=['GET', 'POST'])
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
				dbCursor.execute("insert into zajecia_zapisy values(DEFAULT,%s,%s,CURRENT_DATE)",(klient, id_zajec,))

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
