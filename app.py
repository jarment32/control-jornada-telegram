import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from telegram import Bot

# Configuración de la aplicación
app = Flask(__name__)
app.secret_key = 'Valencia01'  # Cambia la clave secreta aquí

# Token del bot de Telegram (reemplaza con tu token)
TELEGRAM_TOKEN = '7865008470:AAEEHlPkgjyvBcokSJaUhssA56_fheaDs2k'
bot = Bot(token=TELEGRAM_TOKEN)

# Conexión a la base de datos PostgreSQL
def get_db_connection():
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME', 'tu_nombre_de_base_de_datos'),  # Cambia esto
        user=os.getenv('DB_USER', 'tu_usuario_de_base_de_datos'),  # Cambia esto
        password=os.getenv('DB_PASSWORD', 'tu_contraseña'),  # Cambia esto
        host=os.getenv('DB_HOST', 'localhost'),
        sslmode='require'
    )
    return conn

# Crear la base de datos y las tablas si no existen
def init_db():
    conn = get_db_connection()
    conn.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        correo TEXT NOT NULL UNIQUE,
        contrasena TEXT NOT NULL
    )
    ''')
    conn.execute('''
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
    conn.close()

# Función para enviar mensaje al bot de Telegram
def enviar_mensaje_telegram(mensaje):
    try:
        # Enviar mensaje a tu canal o chat privado
        bot.send_message(chat_id="@jmptelecom_bot", text=mensaje)  # Reemplaza @tu_canaltarget por tu canal o ID
    except Exception as e:
        print(f"Error al enviar el mensaje de Telegram: {e}")

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
            conn.execute('INSERT INTO usuarios (nombre, correo, contrasena) VALUES (%s, %s, %s)', 
                         (nombre, correo, contrasena_hash))
            conn.commit()
            flash('Usuario registrado con éxito.', 'success')
            
            # Enviar mensaje al bot de Telegram cuando se registre un nuevo usuario
            mensaje = f"Nuevo registro: {nombre} con correo {correo}"
            enviar_mensaje_telegram(mensaje)
            
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
        user = conn.execute('SELECT * FROM usuarios WHERE correo = %s', (correo,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['contrasena'], contrasena):
            session['usuario_id'] = user['id']
            session['usuario_nombre'] = user['nombre']
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
    jornadas = conn.execute('SELECT * FROM jornadas WHERE usuario_id = %s ORDER BY fecha DESC', 
                            (session['usuario_id'],)).fetchall()
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
    conn.execute('INSERT INTO jornadas (usuario_id, fecha, hora_entrada) VALUES (%s, %s, %s)', 
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
    conn.execute('UPDATE jornadas SET hora_salida = %s WHERE id = %s AND usuario_id = %s', 
                 (hora_salida, jornada_id, session['usuario_id']))
    conn.commit()
    conn.close()
    
    flash('Hora de salida registrada.', 'success')
    return redirect(url_for('dashboard'))

# Inicialización de la base de datos
init_db()

if __name__ == '__main__':
    app.run(debug=True)
