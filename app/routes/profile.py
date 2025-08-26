from flask import Blueprint, render_template, session, redirect
from flask_paginate import Pagination, get_page_args
from app.models.database import dbConnect, PER_PAGE

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/profil')
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


@profile_bp.route('/profil_trenera')
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
