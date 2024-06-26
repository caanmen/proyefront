from flask import Flask, request, jsonify
import psycopg2
import psycopg2.extras

app = Flask(__name__)
app.secret_key = 'tu_super_secreto'

class DatabaseConnection:
    connection = None

    @staticmethod
    def get_connection():
        if DatabaseConnection.connection is None:
            DatabaseConnection.connection = psycopg2.connect(
                dbname="Restaurante",
                user="postgres",
                password="admin",
                host="localhost"
            )
        return DatabaseConnection.connection

def get_db_connection():
    return DatabaseConnection.get_connection()

@app.route('/')
def home():
    return 'Bienvenido a la API de ReservaFacil!'

@app.route('/create_user', methods=['POST'])
def create_user():
    user_details = request.json
    nombre = user_details['nombre']
    apellido = user_details['apellido']
    correo = user_details['correo']
    telefono = user_details['telefono']
    tipo_usuario = user_details['tipo_usuario']
    contrasena = user_details['contrasena']

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO public.usuarios (nombre, apellido, correo, telefono, tipo_usuario, contrasena) VALUES (%s, %s, %s, %s, %s, %s)',
            (nombre, apellido, correo, telefono, tipo_usuario, contrasena)
        )
        conn.commit()
        return jsonify({'message': 'Usuario creado exitosamente'}), 201
    except psycopg2.DatabaseError as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/login', methods=['POST'])
def login():
    credentials = request.json
    correo = credentials['correo']
    contrasena = credentials['contrasena']

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute(
            'SELECT * FROM public.usuarios WHERE correo = %s AND contrasena = %s',
            (correo, contrasena)
        )
        user = cursor.fetchone()
        if user:
            additional_claims = {"tipo_usuario": user['tipo_usuario']}
            return jsonify(user=user['correo'], tipo_usuario=additional_claims), 200
        else:
            return jsonify({'error': 'Credenciales inválidas'}), 401
    except psycopg2.DatabaseError as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM public.usuarios WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        return jsonify(user), 200
    except psycopg2.DatabaseError as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/user/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user_details = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE public.usuarios SET nombre=%s, apellido=%s, correo=%s, telefono=%s, tipo_usuario=%s, contrasena=%s WHERE id=%s RETURNING id",
            (user_details['nombre'], user_details['apellido'], user_details['correo'], user_details['telefono'], user_details['tipo_usuario'], user_details['contrasena'], user_id)
        )
        updated_user = cursor.fetchone()
        if updated_user is None:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        conn.commit()
        return jsonify({'message': 'Usuario actualizado exitosamente'}), 200
    except psycopg2.DatabaseError as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM public.usuarios WHERE id = %s RETURNING id", (user_id,))
        deleted_user = cursor.fetchone()
        if deleted_user is None:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        conn.commit()
        return jsonify({'message': 'Usuario eliminado exitosamente'}), 200
    except psycopg2.DatabaseError as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=3200)
