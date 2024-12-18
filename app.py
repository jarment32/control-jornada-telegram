import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Configuración de la aplicación
app = Flask(__name__)
app.secret_key = 'Valencia01'  # Cambia la clave secreta aquí

# Usa tu token de BotFather
bot = telegram.Bot(token='7865008470:AAEEHlPkgjyvBcokSJaUhssA56_fheaDs2k')

# Conexión a la base de datos PostgreSQL
def get_db_connection():
    # Leer la URL de la base de datos desde la variable de entorno
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise RuntimeError('La variable de entorno DATABASE_URL no está configurada.')
    
    # Conectar usando la URI
    conn = psycopg2.connect(database_url, sslmode='require')
    return conn

# Crear la base de datos y las tablas si no existen
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        correo TEXT NOT NULL UNIQUE,
        contrasena TEXT NOT NULL
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS jornadas (
        id SERIAL PRIMARY KEY,
        usuario_id INTEGER,
        fecha TEXT NOT NULL,
        hora_entrada TEXT,
        hora_salida TEXT,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

# Página de inicio
@app.route('/')
def index():
    if 'usuario_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

# Registro de usuario
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        contrasena = request.form['contrasena']
        contrasena_hash = generate_password_hash(contrasena)
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO usuarios (nombre, correo, contrasena) VALUES (%s, %s, %s)', 
                         (nombre, correo, contrasena_hash))
            conn.commit()
            flash('Usuario registrado con éxito.', 'success')
            return redirect(url_for('index'))
        except psycopg2.IntegrityError:
            flash('El correo ya está registrado.', 'danger')
        finally:
            conn.close()
    
    return render_template('registro.html')

# Inicio de sesión de usuario
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        contrasena = request.form['contrasena']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE correo = %s', (correo,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[3], contrasena):  # user[3] es la contraseña
            session['usuario_id'] = user[0]  # user[0] es el id del usuario
            session['usuario_nombre'] = user[1]  # user[1] es el nombre del usuario
            flash('Inicio de sesión exitoso.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Correo o contraseña incorrectos.', 'danger')
    
    return render_template('login.html')

# Cerrar sesión
@app.route('/logout')
def logout():
    session.pop('usuario_id', None)
    session.pop('usuario_nombre', None)
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('index'))

# Dashboard - Pantalla principal del usuario
@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM jornadas WHERE usuario_id = %s ORDER BY fecha DESC', 
                            (session['usuario_id'],))
    jornadas = cursor.fetchall()
    conn.close()
    return render_template('dashboard.html', jornadas=jornadas)

# Registrar entrada
@app.route('/entrada', methods=['POST'])
def entrada():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    hora_entrada = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    fecha = datetime.now().strftime('%Y-%m-%d')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO jornadas (usuario_id, fecha, hora_entrada) VALUES (%s, %s, %s)', 
                 (session['usuario_id'], fecha, hora_entrada))
    conn.commit()
    conn.close()
    
    flash('Hora de entrada registrada.', 'success')
    return redirect(url_for('dashboard'))

# Registrar salida
@app.route('/salida/<int:jornada_id>', methods=['POST'])
def salida(jornada_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    hora_salida = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE jornadas SET hora_salida = %s WHERE id = %s AND usuario_id = %s', 
                 (hora_salida, jornada_id, session['usuario_id']))
    conn.commit()
    conn.close()
    
    flash('Hora de salida registrada.', 'success')
    return redirect(url_for('dashboard'))

# Función para crear el teclado de inicio con botones
def create_start_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="Accede a la Web App", url="https://control-jornada-telegram-c9f613f713c3.herokuapp.com/")],
        [InlineKeyboardButton(text="Ver Tutorial", url="https://www.ejemplo.com/tutorial")],
        [InlineKeyboardButton(text="Ayuda", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Enviar mensaje con botón al iniciar bot
@app.route('/start', methods=['GET', 'POST'])
def start():
    # Enviar una imagen junto con el texto
    bot.send_photo(
        chat_id='@jmptelecom_bot',  # Cambia esto con tu chat_id
        photo='https://www.example.com/your_image.png',  # Reemplaza con la URL de tu imagen
        caption="¡Bienvenido a la Web App!"  # Puedes agregar un título aquí
    )

    # Enviar un mensaje con los botones
    bot.send_message(
        chat_id='@jmptelecom_bot',  # Cambia esto con tu chat_id
        text="<b>¡Bienvenido a la Web App!</b>\n\n"  # Usa HTML para formato en negrita
        "Haz clic en uno de los botones a continuación para comenzar:",
        parse_mode='HTML',  # Esto habilita el uso de HTML
        reply_markup=create_start_keyboard()
    )

    return 'Web App link sent!'

# Inicialización de la base de datos
init_db()

if __name__ == '__main__':
    app.run(debug=True)
