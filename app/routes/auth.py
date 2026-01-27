from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
from flask_mail import Message
import hashlib
import random
import string
from itsdangerous import URLSafeTimedSerializer
from app.models.database import dbConnect
import os
from mailjet_rest import Client

auth_bp = Blueprint('auth', __name__)

def generate_token(length=20):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

def send_mailjet_email(to_email, subject, text_body):
    api_key = os.getenv("MAIL_USERNAME")
    api_secret = os.getenv("MAIL_PASSWORD")
    sender = os.getenv("MAIL_SENDER")

    mailjet = Client(auth=(api_key, api_secret), version='v3.1')

    data = {
        'Messages': [
            {
                "From": {
                    "Email": sender,
                    "Name": "LetsBeFit Siłownia"
                },
                "To": [
                    {"Email": to_email}
                ],
                "Subject": subject,
                "TextPart": text_body
            }
        ]
    }
    result = mailjet.send.create(data=data)
    if result.status_code not in [200, 201]:
        print("Błąd wysyłania maila:", result.status_code, result.json())
    else:
        print("E-mail wysłany:", to_email)

@auth_bp.route('/logowanie', methods=["POST","GET"])
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
	
@auth_bp.route('/rejestracja', methods=['POST','GET'])
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
				confirm_url = url_for("auth.confirm", token=confirmation_token, _external=True)
				body = f'Kliknij poniższy link, aby potwierdzić rejestrację:\n{confirm_url}'
				send_mailjet_email(login, "Potwierdzenie rejestracji", body)
				msg = "Konto utworzone prawidłowo, aby móc się zalogować wejdź w link aktywacyjny wysłany na podanego maila"
			dbCursor.close()
			dbConnection.close()
			return render_template("index.html",msg=msg)
	
	return render_template("rejestracja.html",msg=msg)



@auth_bp.route('/confirm/<token>')
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
	
	return redirect(url_for('admin.index',msg=msg))


@auth_bp.route('/reset_hasla', methods=['GET', 'POST'])
def reset_hasla():
	if request.method == 'POST':
		email = request.form['email']
		dbConnection = dbConnect()
		dbCursor = dbConnection.cursor()
		dbCursor.execute("SELECT * FROM uzytkownicy WHERE login = %s", (email,))
		user = dbCursor.fetchone()

		if user:
			serializer = URLSafeTimedSerializer(current_app.secret_key)
			token = serializer.dumps(email, salt='reset-hasla-salt')
			confirmation_url = url_for('auth.reset_hasla_potwierdzenie', token=token, _external=True)
			body = f'Aby zresetować hasło, kliknij poniższy link:\n{confirmation_url}'
			send_mailjet_email(email, "Resetowanie hasła", body)
			msgSuccess = 'Link resetujący hasło został wysłany na podany adres e-mail.'
			return render_template('reset_hasla.html',msgSuccess=msgSuccess)

	return render_template('reset_hasla.html')

@auth_bp.route('/reset_hasla_potwierdzenie/<token>', methods=['GET', 'POST'])
def reset_hasla_potwierdzenie(token):
	try:
		serializer = URLSafeTimedSerializer(current_app.secret_key)
		email = serializer.loads(token, salt='reset-hasla-salt', max_age=3600)
    
	except Exception as e:
		print(f"Błąd przy odczycie tokenu: {e}")
		return redirect(url_for('auth.index'))

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
			dbCursor.execute("UPDATE uzytkownicy SET haslo = %s WHERE login = %s", (nowe_haslo_hash, email))
			dbConnection.commit()
			msg= 'Hasło zostało zresetowane. Możesz się teraz zalogować.'
			return redirect(url_for('auth.logowanie_action', msg=msg))

	return render_template('reset_hasla_potwierdzenie.html', token=token,email=email)



@auth_bp.route('/wyloguj')
def wyloguj():
	if 'login' in session:
		session.clear()
	return redirect("/")
