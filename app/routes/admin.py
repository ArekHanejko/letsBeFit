from flask import Blueprint, render_template, request, redirect, url_for, session
from app.models.database import dbConnect

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/')
def index():
    msg=''
    if 'msg' in request.args:
        msg=request.args['msg']
    return render_template("index.html",msg=msg)

@admin_bp.route('/panel_admina')
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

@admin_bp.route('/zmien_ceny',methods = ['POST','GET'])
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
@admin_bp.route('/zmien_role',methods = ['POST','GET'])
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
			return redirect(url_for('admin.zmiany_zapisane',msgWarning=msgWarning,msgSuccess=msgSuccess,msg=msg))
	
		dbConnection.commit()
		dbCursor.close()
		dbConnection.close()
		return redirect(url_for('admin.zmiany_zapisane',msgSuccess=msgSuccess,msgWarning=msgWarning,msg=msg))
	else:
		return redirect('/')
@admin_bp.route('/zmiany_zapisane')
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

@admin_bp.route('/statystyki')
def statystyki():

	
		dbConnection = dbConnect()
		dbCursor = dbConnection.cursor()
		dbCursor.execute("SELECT godzina, COALESCE(COUNT(id_wejscia), 0) AS liczba_wejsc FROM generate_series(0, 23) godzina LEFT JOIN wejscia ON EXTRACT(HOUR FROM godzina_wejscia) = godzina GROUP BY godzina ORDER BY godzina; ")
		res = dbCursor.fetchall()
		
		dbConnection.commit()
		dbCursor.close()
		dbConnection.close()
		return render_template("statystyki.html",res=res)
	
	