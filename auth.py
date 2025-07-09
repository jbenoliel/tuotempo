import os
import jwt
import datetime
from flask import current_app, url_for
from flask_mail import Mail, Message
from functools import wraps
from flask import request, redirect, url_for, flash, session
from db import get_connection

# Inicializar Flask-Mail
mail = Mail()

def init_mail(app):
    """Inicializa Flask-Mail con la aplicación Flask."""
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])
    
    mail.init_app(app)
    return mail

def login_required(f):
    """Decorador para requerir inicio de sesión en rutas protegidas."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'danger')
            return redirect(url_for('main.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorador para requerir permisos de administrador en rutas protegidas."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or 'is_admin' not in session or not session['is_admin']:
            flash('No tienes permisos para acceder a esta página', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def generate_reset_token(user_id):
    """Genera un token JWT para restablecimiento de contraseña."""
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    token = jwt.encode(
        payload,
        current_app.config.get('SECRET_KEY'),
        algorithm='HS256'
    )
    return token

def verify_reset_token(token):
    """Verifica un token JWT para restablecimiento de contraseña."""
    try:
        payload = jwt.decode(
            token,
            current_app.config.get('SECRET_KEY'),
            algorithms=['HS256']
        )
        return payload['user_id']
    except:
        return None

def send_password_reset_email(user_id, email, username, token):
    """Envía un email con el enlace para restablecer la contraseña."""
    reset_url = url_for('main.reset_password', token=token, _external=True)
    
    subject = "Restablecimiento de contraseña - Dashboard Tuotempo"
    body = f"""Hola {username},

Has solicitado restablecer tu contraseña. Por favor, haz clic en el siguiente enlace para establecer una nueva contraseña:

{reset_url}

Este enlace expirará en 24 horas.

Si no solicitaste restablecer tu contraseña, ignora este mensaje.

Saludos,
El equipo de Tuotempo
"""
    
    msg = Message(
        subject=subject,
        recipients=[email],
        body=body
    )
    
    mail.send(msg)

def send_welcome_email(user_id, email, username, token):
    """Envía un email de bienvenida con el enlace para establecer la contraseña."""
    reset_url = url_for('main.reset_password', token=token, _external=True)
    
    subject = "Bienvenido al Dashboard Tuotempo - Configura tu cuenta"
    body = f"""Hola {username},

Tu cuenta ha sido creada en el Dashboard de Tuotempo. Para comenzar, necesitas establecer tu contraseña:

{reset_url}

Este enlace expirará en 24 horas.

Saludos,
El equipo de Tuotempo
"""
    
    msg = Message(
        subject=subject,
        recipients=[email],
        body=body
    )
    
    mail.send(msg)

def create_user(username, email, is_admin=False):
    """Crea un nuevo usuario y envía un email de bienvenida."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Generar un hash aleatorio como contraseña temporal
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        temp_password = bcrypt.generate_password_hash('temp').decode('utf-8')
        
        # Insertar el usuario en la base de datos
        cursor.execute(
            "INSERT INTO usuarios (username, password_hash, email, is_admin) VALUES (%s, %s, %s, %s)",
            (username, temp_password, email, is_admin)
        )
        conn.commit()
        
        # Obtener el ID del usuario recién creado
        user_id = cursor.lastrowid
        
        # Generar token para establecer contraseña
        token = generate_reset_token(user_id)
        
        # Guardar el token en la base de datos
        expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        cursor.execute(
            "UPDATE usuarios SET reset_token = %s, reset_token_expiry = %s WHERE id = %s",
            (token, expiry, user_id)
        )
        conn.commit()
        
        # Enviar email de bienvenida
        send_welcome_email(user_id, email, username, token)
        
        return True, "Usuario creado exitosamente. Se ha enviado un email para establecer la contraseña."
    except Exception as e:
        conn.rollback()
        return False, f"Error al crear el usuario: {str(e)}"
    finally:
        cursor.close()
        conn.close()

def get_user_by_email(email):
    """Obtiene un usuario por su email."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
        user = cursor.fetchone()
        return user
    finally:
        cursor.close()
        conn.close()

def get_user_by_username(username):
    """Obtiene un usuario por su nombre de usuario."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM usuarios WHERE username = %s", (username,))
        user = cursor.fetchone()
        return user
    finally:
        cursor.close()
        conn.close()

def get_user_by_id(user_id):
    """Obtiene un usuario por su ID."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM usuarios WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        return user
    finally:
        cursor.close()
        conn.close()

def update_password(user_id, password):
    """Actualiza la contraseña de un usuario."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        
        cursor.execute(
            "UPDATE usuarios SET password_hash = %s, reset_token = NULL, reset_token_expiry = NULL, email_verified = TRUE WHERE id = %s",
            (password_hash, user_id)
        )
        conn.commit()
        return True, "Contraseña actualizada exitosamente."
    except Exception as e:
        conn.rollback()
        return False, f"Error al actualizar la contraseña: {str(e)}"
    finally:
        cursor.close()
        conn.close()

def request_password_reset(email):
    """Solicita un restablecimiento de contraseña."""
    user = get_user_by_email(email)
    
    if not user:
        # No revelar si el email existe o no por seguridad
        return True, "Si el email existe en nuestra base de datos, recibirás instrucciones para restablecer tu contraseña."
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Generar token para restablecer contraseña
        token = generate_reset_token(user['id'])
        
        # Guardar el token en la base de datos
        expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        cursor.execute(
            "UPDATE usuarios SET reset_token = %s, reset_token_expiry = %s WHERE id = %s",
            (token, expiry, user['id'])
        )
        conn.commit()
        
        # Enviar email con el enlace para restablecer la contraseña
        send_password_reset_email(user['id'], user['email'], user['username'], token)
        
        return True, "Se han enviado instrucciones para restablecer tu contraseña al email proporcionado."
    except Exception as e:
        conn.rollback()
        return False, f"Error al solicitar el restablecimiento de contraseña: {str(e)}"
    finally:
        cursor.close()
        conn.close()
