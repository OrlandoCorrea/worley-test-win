import os
import smtplib
import ssl
import pandas as pd
from flask_mail import Mail, Message
from dotenv import load_dotenv
from email.message import EmailMessage
from flask import Flask, render_template, redirect, request, session
from flask_mysqldb import MySQL
from sodapy import Socrata
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import bcrypt
from flask import send_file
from io import BytesIO


# Initialize Flask app
app = Flask(__name__, template_folder='template')
app.secret_key = os.urandom(24)

# Load environment variables
load_dotenv()

app.config['MYSQL_HOST'] ='worley-db-covid19.mysql.database.azure.com'
app.config['MYSQL_USER'] ='admin_ofcv'
app.config['MYSQL_PASSWORD'] ='Clave123'
app.config['MYSQL_DB'] ='worley-schema-covid19'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'ocorreave@gmail.com'
app.config['MAIL_PASSWORD'] = 'qhwzeymqquskvqho'

# Initialize MySQL and Mail instances
mysql = MySQL(app)
mail = Mail(app)

# Initialize Socrata client
client = Socrata("www.datos.gov.co", None)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/registro')
def registro():
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'logueado' in session and session['logueado']:
        results = client.get("gt2j-8ykr", limit=4000)
        results_df = pd.DataFrame.from_records(results)
        filtered_data = results_df[["departamento_nom", "ciudad_municipio_nom", "edad", "sexo", "fuente_tipo_contagio", "ubicacion", "estado", "pais_viajo_1_nom", "recuperado", "fecha_reporte_web"]]
        session['data'] = filtered_data.to_dict('records')
        return render_template('dashboard.html', data=session['data'])
    else:
        return render_template('index.html', mensaje="Por favor, inicie sesión.")

@app.route('/access_login', methods=["POST"])
def access_login():
    if request.method == 'POST':
        _email_ = request.form['email_address']
        _password_ = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute('SELECT passwd FROM `worley-schema-covid19`.users WHERE email = %s', (_email_,))
        hashed_password = cur.fetchone()
        cur.close()
        salt = bcrypt.gensalt()
        results = client.get("gt2j-8ykr", limit=4000)

        # Convert to pandas DataFrame
        results_df = pd.DataFrame.from_records(results)
        results_df2 = results_df[["departamento_nom", "ciudad_municipio_nom", "edad", "sexo", "fuente_tipo_contagio", "ubicacion", "estado", "pais_viajo_1_nom", "recuperado","fecha_reporte_web"]]
        
        # Convertir DataFrame a tabla HTML
        html_table = results_df2.to_html(classes='table table-striped')
        app.config['GLOBAL_VARIABLE'] = results_df2
        app.config['departamento_list'] = sorted(results_df2['departamento_nom'].astype(str).unique())
        app.config['ciudad_list'] = sorted(results_df2['ciudad_municipio_nom'].astype(str).unique())
        app.config['edad_list'] = sorted(results_df2['edad'].astype(str).unique())
        app.config['sexo_list'] = sorted(results_df2['sexo'].astype(str).unique())
        app.config['tipo_contagio_list'] = sorted(results_df2['fuente_tipo_contagio'].astype(str).unique())
        app.config['ubicacion_list'] = sorted(results_df2['ubicacion'].astype(str).unique())
        app.config['estado_list'] = sorted(results_df2['estado'].astype(str).unique())
        app.config['pais_viajo_list'] = sorted(results_df2['pais_viajo_1_nom'].astype(str).unique())
        app.config['recuperado_list'] = sorted(results_df2['recuperado'].astype(str).unique())
        app.config['fecha_report_list'] = sorted(results_df2['fecha_reporte_web'].astype(str).unique())
        
        if hashed_password:
            if hashed_password['passwd'] and bcrypt.checkpw(_password_.encode('utf-8'), hashed_password['passwd']):
                session['logueado'] = True
                return render_template('dashboard.html',html_table=html_table, departamento_list=app.config['departamento_list'], ciudad_list=app.config['ciudad_list'], edad_list=app.config['edad_list'], sexo_list=app.config['sexo_list'], tipo_contagio_list=app.config['tipo_contagio_list'], ubicacion_list=app.config['ubicacion_list'], estado_list=app.config['estado_list'], pais_viajo_list=app.config['pais_viajo_list'], recuperado_list=app.config['recuperado_list'], fecha_report_list=app.config['fecha_report_list'])
            else:
                return render_template('index.html', mensaje="Credenciales Incorrectas")
        else:
            return render_template('index.html', mensaje="Credenciales Incorrectas")
            
@app.route('/register_new', methods=["POST"])
def register_new():
    if request.method == 'POST':
        _correo_ = request.form['correo']
        _nombre_ = request.form['nombre']
        _apellidos_ = request.form['apellidos']
        _clave_ = request.form['clave']
        # Generar un salt aleatorio
        salt = bcrypt.gensalt()
        # Generar el hash de la contraseña utilizando el salt
        hashed_password = bcrypt.hashpw(_clave_.encode('utf-8'), salt)
        cur = mysql.connection.cursor()
        sql_query = 'INSERT INTO `worley-schema-covid19`.users (`email`,`passwd`,`name`,`last_name`) VALUES (%s,%s,%s,%s)'
        val_query = (_correo_, hashed_password, _nombre_, _apellidos_)
        cur.execute(sql_query, val_query)
        mysql.connection.commit()
        cur.close()
        return render_template('index.html', mensaje="Usuario Creado Exitosamente")
    else:
        return render_template('register.html', mensaje="Credenciales Incorrectas")

@app.route('/search_data', methods=["POST"])
def search_data():
    if request.method == "POST":
        selected_attributes = [request.form.get(attr) for attr in ['departamento', 'ciudad', 'edad', 'sexo', 'fuente_contagio', 'ubicacion', 'estado', 'pais_viaje', 'recuperado', 'fecha_report']]
        results = client.get("gt2j-8ykr", limit=4000)
        results_df = pd.DataFrame.from_records(results)

        filtered_data = results_df
        for attr, value in zip(['departamento_nom', 'ciudad_municipio_nom', 'edad', 'sexo', 'fuente_tipo_contagio', 'ubicacion', 'estado', 'pais_viajo_1_nom', 'recuperado', 'fecha_reporte_web'], selected_attributes):
            if value:
                filtered_data = filtered_data[filtered_data[attr] == value]

        # Convertir DataFrame a tabla HTML
        html_table2 = filtered_data.to_html(classes='table table-striped')
        app.config['GLOBAL_VARIABLE'] = filtered_data
        return render_template('dashboard.html', html_table=html_table2, mensaje="", data_df=filtered_data, departamento_list=app.config['departamento_list'], ciudad_list=app.config['ciudad_list'], edad_list=app.config['edad_list'], sexo_list=app.config['sexo_list'], tipo_contagio_list=app.config['tipo_contagio_list'], ubicacion_list=app.config['ubicacion_list'], estado_list=app.config['estado_list'], pais_viajo_list=app.config['pais_viajo_list'], recuperado_list=app.config['recuperado_list'], fecha_report_list=app.config['fecha_report_list'])

@app.route('/download_and_send_email', methods=['POST'])
def download_and_send_email():
    atributos_seleccionados = request.form.getlist('atributo')
    df = app.config['GLOBAL_VARIABLE']
    df_filtered = df[atributos_seleccionados]

    excel_file_path = 'datos_solicitados_covid19_filtrado.xlsx'
    excel_data = df_filtered.to_excel(excel_file_path, index=False)
    # Devuelve el archivo Excel como una respuesta de descarga
    send_file('./datos_solicitados_covid19_filtrado.xlsx', as_attachment=True)

    # Guarda los datos en un archivo Excel en memoria
    excel_data_bytes = BytesIO()
    df_filtered.to_excel(excel_data_bytes, index=False)
    excel_data_bytes.seek(0)  # Reinicia el cursor al principio del archivo

    username = app.config['MAIL_USERNAME']
    password = app.config['MAIL_PASSWORD']
    mail_from = app.config['MAIL_USERNAME']
    mail_to = "tecnoquark@gmail.com"
    mail_subject = "Adjunto: Informe Solicitado de Datos COVID-19"
    mail_body = "Estimado/a,\n\nAdjunto encontrará el informe de datos actualizado sobre COVID-19 solicitado.\n\nSaludos cordiales,\nOrlando Correa"

    mimemsg = MIMEMultipart()
    mimemsg['From']=mail_from
    mimemsg['To']=mail_to
    mimemsg['Subject']=mail_subject
    mimemsg.attach(MIMEText(mail_body, 'plain'))

    # Adjuntar el archivo Excel al correo
    part = MIMEBase('application', 'octet-stream')
    part.set_payload((excel_data_bytes).read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', "attachment; filename=datos_solicitados_covid19_filtrado.xlsx")
    mimemsg.attach(part)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(host='smtp.gmail.com', port=587) as connection:
            connection.starttls()
            connection.login(username, password)
            connection.send_message(mimemsg)
            return render_template('dashboard.html', html_table=app.config['GLOBAL_VARIABLE'].to_html(classes='table table-striped'), mensaje="El archivo fue Descargado, Correo electrónico enviado con éxito y archivo Excel adjunto.", departamento_list=app.config['departamento_list'], ciudad_list=app.config['ciudad_list'], edad_list=app.config['edad_list'], sexo_list=app.config['sexo_list'], tipo_contagio_list=app.config['tipo_contagio_list'], ubicacion_list=app.config['ubicacion_list'], estado_list=app.config['estado_list'], pais_viajo_list=app.config['pais_viajo_list'], recuperado_list=app.config['recuperado_list'], fecha_report_list=app.config['fecha_report_list'])
    except Exception as e:
            return render_template('dashboard.html', html_table=app.config['GLOBAL_VARIABLE'].to_html(classes='table table-striped'), mensaje="El archivo fue Descargado, pero hubo Error en el envío del Archivo Excel al Correo Electronico, revisa que hayas seleccionado algun atributo y dale generar neuvamente", departamento_list=app.config['departamento_list'], ciudad_list=app.config['ciudad_list'], edad_list=app.config['edad_list'], sexo_list=app.config['sexo_list'], tipo_contagio_list=app.config['tipo_contagio_list'], ubicacion_list=app.config['ubicacion_list'], estado_list=app.config['estado_list'], pais_viajo_list=app.config['pais_viajo_list'], recuperado_list=app.config['recuperado_list'], fecha_report_list=app.config['fecha_report_list'])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
