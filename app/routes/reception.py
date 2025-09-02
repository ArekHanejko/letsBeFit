from flask import Blueprint, render_template, request, redirect, url_for, session
from flask_paginate import Pagination, get_page_args
from app.models.database import dbConnect, PER_PAGE
import hashlib
reception_bp = Blueprint('reception', __name__)

@reception_bp.route('/recepcja_zmiana_hasla_klienta', methods = ['POST','GET'])
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

@reception_bp.route('/zajecia_recepcja')
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

@reception_bp.route('/recepcja_zapisz_na_zajecia', methods = ['POST','GET'])
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
			return redirect(url_for('reception.zajecia_recepcja',msgWarning=msgWarning))
		if(status_oplacenia=='oplacony'):
			dbCursor.execute("update zajecia_zapisy set id_uczestnika=%s where id_uczestnika=9999",(userid,))
			msgSuccess="Użytkownik został zapisany na zajęcia"

		elif(status_oplacenia=='nieoplacony'):
			dbCursor.execute("delete from zajecia_zapisy where id_uczestnika=9999")
			dbConnection.commit()
			dbCursor.close()
			dbConnection.close()
			#return redirect('/zajecia_recepcja')
			return redirect(url_for('reception.zajecia_recepcja',msgSuccess=msgSuccess))
		#dbCursor.execute("insert into zajecia_zapisy values(DEFAULT, %s, %s, CURRENT_DATE )",(userid, id_zajec))
		#dbCursor.execute("update zajecia_zapisy values(DEFAULT, %s, %s, CURRENT_DATE )",(userid, id_zajec))
		dbCursor.execute("delete from zajecia_zapisy where id_uczestnika=9999")
		dbConnection.commit()
		dbCursor.close()
		dbConnection.close()
		return redirect(url_for('reception.zajecia_recepcja',msgSuccess=msgSuccess))
	else:
		return redirect('/')

@reception_bp.route('/karnety_recepcja')
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

@reception_bp.route('/recepcja_zapisz_karnet', methods = ['POST','GET'])
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

@reception_bp.route('/recepcja_wejscia')
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
@reception_bp.route('/recepcja_wejscia_sprawdz', methods = ['POST','GET'])
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
	

		return redirect(url_for('reception.recepcja_wejscia', uzytkownicy_lista=[], msgSuccess=msgSuccess,msgWarning=msgWarning))
	else:
		return redirect('/')
