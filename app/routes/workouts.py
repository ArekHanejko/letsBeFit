from flask import Blueprint, render_template, request, redirect, url_for, session
from flask_paginate import Pagination, get_page_args
from app.models.database import dbConnect, PER_PAGE

workouts_bp = Blueprint('workouts', __name__)

@workouts_bp.route('/karnety')
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


@workouts_bp.route('/karnety_recepcja')
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


@workouts_bp.route('/zajecia')
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

@workouts_bp.route('/dodaj_zajecia', methods = ['POST','GET'])
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
		return redirect(url_for('workouts.zajecia',msg=msg))
	else:
		return redirect('/')

@workouts_bp.route('/odwolaj_zajecia', methods=['POST','GET'])
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

@workouts_bp.route('/lista_uczestnikow_zajec', methods = ['POST','GET'])
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