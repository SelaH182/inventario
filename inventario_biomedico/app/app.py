import os
import sys
import secrets
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, Usuario, Equipo
from sqlalchemy import or_
from datetime import date
from datetime import datetime, timedelta
from flask_migrate import Migrate
from flask import flash, request
from models import Usuario, Trazabilidad
from flask_mail import Mail, Message


# Inicializar la aplicación Flask
app = Flask(__name__)

# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # o tu servidor SMTP
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'inventariobiomedicounab@gmail.com'   # aquí tu correo
app.config['MAIL_PASSWORD'] = 'ccel gody phnr tqkn'  # aquí la contraseña de app

mail = Mail(app)

# Carpeta de subida de archivos
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'clave_secreta_segura'
# Inicializar la base de datos
db.init_app(app)


# Clave secreta para manejar sesiones
app.secret_key = 'clave_secreta_segura'

# Configuración de la base de datos SQLite
BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # Ruta de la carpeta actual
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Crear la base de datos si no existe
with app.app_context():
    db.create_all()

# Ruta de inicio (Login)
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        usuario = Usuario.query.filter_by(username=username).first()

        if usuario and check_password_hash(usuario.password, password):
            session['user_id'] = usuario.id
            session['role'] = usuario.role

            # <<< Aquí registras la trazabilidad del inicio de sesión >>>
            nueva_traza = Trazabilidad(
                user_id=usuario.id,
                accion='Inicio de sesión',
                descripcion=f'El usuario {usuario.username} inició sesión.'
            )
            db.session.add(nueva_traza)
            db.session.commit()

            return redirect(url_for('dashboard'))
        else:
            flash('Nombre de usuario o contraseña incorrectos')

    return render_template('login.html')

# Ruta de registro de usuarios
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'role' not in session or session['role'] != 'administrador':
        return "Acceso denegado. No tienes permisos para ver esta página.", 403

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        role = request.form['role']
        correo = request.form.get('correo')

        # Validar si el username o correo ya existen
        existing_user = Usuario.query.filter_by(username=username).first()
        existing_email = Usuario.query.filter_by(correo=correo).first()

        if existing_user:
            flash('El nombre de usuario ya está en uso. Por favor elige otro.', 'error')
            return redirect(url_for('register'))

        if existing_email:
            flash('El correo electrónico ya está registrado. Por favor usa otro.', 'error')
            return redirect(url_for('register'))

        # Si no existen, crear el usuario
        new_user = Usuario(
            username=username,
            password=hashed_password,
            role=role,
            correo=correo
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Usuario registrado exitosamente.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# Ruta para recuperar contraseña
@app.route('/recuperar', methods=['GET', 'POST'])
def recuperar():
    if request.method == 'POST':
        correo = request.form['correo']
        usuario = Usuario.query.filter_by(correo=correo).first()

        if usuario:
            token = secrets.token_urlsafe(16)
            usuario.reset_token = token
            usuario.reset_token_expiration = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()

            # Crear el mensaje
            msg = Message('Recuperación de Contraseña',
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[correo])
            link_reset = url_for('resetear_contraseña', _external=True) + f"?token={token}"
            msg.body = f"""
Hola,

Para resetear tu contraseña, haz clic en el siguiente enlace:

{link_reset}

También puedes usar el siguiente token si se te solicita:

Token: {token}

Este enlace y token expirarán en 1 hora.

Saludos,
El equipo de soporte
"""

            # Enviar el correo
            mail.send(msg)

            flash('Se ha enviado un correo con instrucciones para resetear tu contraseña.', 'info')
            return redirect(url_for('login'))
        else:
            flash('No se encontró una cuenta con ese correo.', 'error')
            return redirect(url_for('recuperar'))

    return render_template('recuperar.html')

# Ruta para resetear la contraseña usando el token
@app.route('/resetear_contraseña', methods=['GET', 'POST'])
def resetear_contraseña():
    if request.method == 'POST':
        token = request.form['token']
        nueva_contraseña = request.form['password']

        usuario = Usuario.query.filter_by(reset_token=token).first()

        if usuario and usuario.reset_token_expiration > datetime.utcnow():
            usuario.password = generate_password_hash(nueva_contraseña)
            usuario.reset_token = None
            usuario.reset_token_expiration = None
            db.session.commit()

            flash('Tu contraseña ha sido restablecida correctamente. Ya puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
        else:
            flash('El token es inválido o ha expirado. Por favor, solicita uno nuevo.', 'error')
            return redirect(url_for('recuperar'))

    return render_template('resetear_contraseña.html')

# Ruta para el (panel de control) dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    return redirect(url_for('login'))

# Ruta para trazabilidad
@app.route('/trazabilidad')
def ver_trazabilidad():
    if 'role' not in session or session['role'] != 'administrador':
        return "Acceso denegado. No tienes permisos para ver esta página.", 403

    trazas = Trazabilidad.query.filter_by(accion='Inicio de sesión').order_by(Trazabilidad.fecha_hora.desc()).all()

    return render_template('trazabilidad.html', trazas=trazas)

# Ruta para agregar equipos
@app.route('/agregar_equipo', methods=['GET', 'POST'])
def agregar_equipo():
    if request.method == 'POST':
        numero_equipo = request.form['numero_equipo']
        nombre_equipo = request.form['nombre_equipo']
        serie = request.form['serie']
        marca = request.form['marca']
        modelo = request.form['modelo']
        ubicacion = request.form['ubicacion']
        mantenimiento_preventivo = request.form['mantenimiento_preventivo']
        mantenimiento_preventivo = float(mantenimiento_preventivo) if mantenimiento_preventivo else None
        fecha_mantenimiento_preventivo = request.form['fecha_mantenimiento_preventivo']
        responsable_mantenimiento_preventivo = request.form['responsable_mantenimiento_preventivo']
        fecha_proximo_mantenimiento_preventivo = request.form['fecha_proximo_mantenimiento_preventivo']
        mantenimiento_correctivo = request.form['mantenimiento_correctivo']
        mantenimiento_correctivo = float(mantenimiento_correctivo) if mantenimiento_correctivo else None
        fecha_mantenimiento_correctivo = request.form['fecha_mantenimiento_correctivo']
        responsable_mantenimiento_correctivo = request.form['responsable_mantenimiento_correctivo']
        fecha_nuevo_mantenimiento_correctivo = request.form['fecha_nuevo_mantenimiento_correctivo']
        registro_invima = request.form['registro_invima']
        calibracion = request.form['calibracion']
        observaciones = request.form['observaciones']
        insumos = request.form.get('insumos')
        responsable_compra_insumos = request.form.get('responsable_compra_insumos')
        costo_insumo = request.form.get('costo_insumo')
        fecha_compra_insumos = request.form.get('fecha_compra_insumos')


        # Archivos PDF
        hoja_vida_file = request.files['hoja_vida']
        manuales_file = request.files['manuales']
        factura_file = request.files['factura']

        hoja_vida_filename = None
        manuales_filename = None
        factura_filename = None

        if hoja_vida_file and allowed_file(hoja_vida_file.filename):
            hoja_vida_filename = secure_filename(hoja_vida_file.filename)
            hoja_vida_file.save(os.path.join(app.config['UPLOAD_FOLDER'], hoja_vida_filename))

        if manuales_file and allowed_file(manuales_file.filename):
            manuales_filename = secure_filename(manuales_file.filename)
            manuales_file.save(os.path.join(app.config['UPLOAD_FOLDER'], manuales_filename))

        if factura_file and allowed_file(factura_file.filename):
            factura_filename = secure_filename(factura_file.filename)
            factura_file.save(os.path.join(app.config['UPLOAD_FOLDER'], factura_filename))

        nuevo_equipo = Equipo(
            numero_equipo=numero_equipo,
            nombre_equipo=nombre_equipo,
            serie=serie,
            marca=marca,
            modelo=modelo,
            ubicacion=ubicacion,
            mantenimiento_preventivo=mantenimiento_preventivo,
            fecha_mantenimiento_preventivo=fecha_mantenimiento_preventivo,
            responsable_mantenimiento_preventivo=responsable_mantenimiento_preventivo,
            fecha_proximo_mantenimiento_preventivo=fecha_proximo_mantenimiento_preventivo,
            mantenimiento_correctivo=mantenimiento_correctivo,
            fecha_mantenimiento_correctivo=fecha_mantenimiento_correctivo,
            responsable_mantenimiento_correctivo=responsable_mantenimiento_correctivo,
            fecha_nuevo_mantenimiento_correctivo=fecha_nuevo_mantenimiento_correctivo,
            registro_invima=registro_invima,
            calibracion=calibracion,
            observaciones=observaciones,
            hoja_vida=hoja_vida_filename,
            manuales=manuales_filename,
            factura=factura_filename,
            insumos=insumos,
            responsable_compra_insumos = responsable_compra_insumos,
            costo_insumo = costo_insumo,
            fecha_compra_insumos = fecha_compra_insumos
        )

        db.session.add(nuevo_equipo)
        db.session.commit()
        return redirect(url_for('listar_equipos'))

    return render_template('agregar_equipo.html')




# Ruta para listar equipos
@app.route('/listar_equipos')
def listar_equipos():
    termino = request.args.get('buscar', '').strip()
    color = request.args.get('color')  # Captura el color de semaforización si lo hay
    vista = request.args.get('vista')  # capturamos si pidieron "resumen"
    
    if color:
        equipos = Equipo.query.filter(
            (Equipo.color_preventivo.ilike(f'%{color}%')) |
            (Equipo.color_correctivo.ilike(f'%{color}%'))
        ).all()
    else:
        equipos = Equipo.query.all()
    
     # Si hay búsqueda, filtra por término
    if termino:
        equipos = Equipo.query.filter(
            or_(
                Equipo.id.like(f"%{termino}%"),
                Equipo.nombre_equipo.ilike(f"%{termino}%"),
                Equipo.serie.ilike(f"%{termino}%"),
                Equipo.marca.ilike(f"%{termino}%"),
                Equipo.ubicacion.ilike(f"%{termino}%")
            )
        ).all()
    else:
        equipos = Equipo.query.all()

    # Si hay color, filtra los equipos por color_mantenimiento
    if color:
        equipos = [eq for eq in equipos if eq.color_mantenimiento == color]

    return render_template('listar_equipos.html', equipos=equipos, vista=vista)

   

@app.route('/semaforizacion')
def semaforizacion():
    equipos = Equipo.query.all()
    hoy = datetime.today().date()
    for equipo in equipos:
        fecha_prox = equipo.fecha_proximo_mantenimiento_preventivo

        if fecha_prox:
            diferencia = (fecha_prox - hoy).days
            if diferencia > 30:
                equipo.color_mantenimiento = 'verde'
                equipo.dias_mora = None
            elif 0 <= diferencia <= 21:
                equipo.color_mantenimiento = 'amarillo'
                equipo.dias_mora = None
            elif diferencia < 0:
                equipo.color_mantenimiento = 'rojo'
                equipo.dias_mora = abs(diferencia)
            else:
                equipo.color_mantenimiento = 'gris'
                equipo.dias_mora = None
        else:
            equipo.color_mantenimiento = 'gris'
            equipo.dias_mora = None

    return render_template('semaforizacion.html', equipos=equipos)

# Ruta para listar usuarios
@app.route('/listar_usuarios')
def listar_usuarios():
    if 'role' not in session or session['role'] != 'administrador':
        return "Acceso denegado. No tienes permisos para ver esta página.", 403
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    usuarios = Usuario.query.all()
    return render_template('listar_usuarios.html', usuarios=usuarios)

# Ruta para editar y eliminar equipos
@app.route('/editar_equipo/<int:id>', methods=['GET', 'POST'])
def editar_equipo(id):
    equipo = Equipo.query.get_or_404(id)

    if request.method == 'POST':
        equipo.numero_equipo = request.form['numero_equipo']
        equipo.nombre_equipo = request.form['nombre_equipo']
        equipo.serie = request.form['serie']
        equipo.marca = request.form['marca']
        equipo.modelo = request.form['modelo']
        equipo.ubicacion = request.form['ubicacion']
        
        mantenimiento_preventivo = request.form['mantenimiento_preventivo']
        mantenimiento_preventivo = float(mantenimiento_preventivo) if mantenimiento_preventivo else None
        equipo.mantenimiento_preventivo = mantenimiento_preventivo
        
        equipo.fecha_mantenimiento_preventivo = request.form['fecha_mantenimiento_preventivo']
        equipo.responsable_mantenimiento_preventivo = request.form['responsable_mantenimiento_preventivo']
        equipo.fecha_proximo_mantenimiento_preventivo = request.form['fecha_proximo_mantenimiento_preventivo']
        
        mantenimiento_correctivo = request.form['mantenimiento_correctivo']
        mantenimiento_correctivo = float(mantenimiento_correctivo) if mantenimiento_correctivo else None
        equipo.mantenimiento_correctivo = mantenimiento_correctivo
        
        equipo.fecha_mantenimiento_correctivo = request.form['fecha_mantenimiento_correctivo']
        equipo.responsable_mantenimiento_correctivo = request.form['responsable_mantenimiento_correctivo']
        equipo.fecha_nuevo_mantenimiento_correctivo = request.form['fecha_nuevo_mantenimiento_correctivo']
        equipo.registro_invima = request.form['registro_invima']
        equipo.calibracion = request.form['calibracion']
        equipo.observaciones = request.form['observaciones']
        equipo.insumos = request.form.get('insumos')
        equipo.responsable_compra_insumos = request.form.get('responsable_compra_insumos')
        equipo.costo_insumo = request.form.get('costo_insumo')
        equipo.fecha_compra_insumos = request.form.get('fecha_compra_insumos')

        db.session.commit()
        return redirect(url_for('listar_equipos'))

    return render_template('editar_equipo.html', equipo=equipo)

@app.route('/eliminar_equipo/<int:id>', methods=['POST'])
def eliminar_equipo(id):
    if 'role' not in session or session['role'] != 'administrador':
        return "Acceso denegado. No tienes permisos para ver esta página.", 403
    equipo = Equipo.query.get_or_404(id)
    db.session.delete(equipo)
    db.session.commit()
    return redirect(url_for('listar_equipos'))

# Ruta para editar usuarios
@app.route('/editar_usuario/<int:id>', methods=['GET', 'POST'])
def editar_usuario(id):
    if 'role' not in session or session['role'] != 'administrador':
        return "Acceso denegado. No tienes permisos para ver esta página.", 403

    usuario = Usuario.query.get_or_404(id)

    if request.method == 'POST':
        username = request.form['username']
        correo = request.form['correo']
        role = request.form['role']
        password = request.form['password']

        # Validar campos vacíos (opcional pero recomendado)
        if not username or not correo or not role:
            flash('Todos los campos son obligatorios.', 'danger')
            return redirect(url_for('editar_usuario', id=id))

        try:
            # Actualizar datos
            usuario.username = username
            usuario.role = role
            usuario.correo = correo
            if password:
                usuario.password = generate_password_hash(password)

            db.session.commit()
            flash('Usuario actualizado exitosamente.', 'success')
            return redirect(url_for('listar_usuarios'))
        except Exception as e:
            db.session.rollback()
            flash('Error al actualizar usuario: ' + str(e), 'danger')
            return redirect(url_for('editar_usuario', id=id))

    return render_template('editar_usuario.html', usuario=usuario)

# Ruta para eliminar usuario
@app.route('/eliminar_usuario/<int:id>', methods=['POST'])
def eliminar_usuario(id):
    if 'role' not in session or session['role'] != 'administrador':
        return "Acceso denegado. No tienes permisos para ver esta página.", 403
    usuario = Usuario.query.get_or_404(id)
    db.session.delete(usuario)
    db.session.commit()
    return redirect(url_for('listar_usuarios'))

# Ruta para visualizar los archivos
@app.route('/uploads/<nombre_archivo>')
def ver_archivo(nombre_archivo):
    return send_from_directory(app.config['UPLOAD_FOLDER'], nombre_archivo)





# Ejecutar la aplicación
if __name__ == '__main__':
    app.run(debug=True)
