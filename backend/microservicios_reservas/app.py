from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime
import psycopg2
import psycopg2.extras


app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'jwt_super_secreto'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False  

jwt = JWTManager(app)

def get_db_connection():
    return psycopg2.connect(
        dbname="Restaurante",
        user="postgres",
        password="admin",
        host="localhost"
    )

def serialize_reserva(reserva):
    return {
        'id': reserva['id'],
        'fecha': reserva['fecha'].isoformat() if reserva['fecha'] else None,
        'hora': reserva['hora'].strftime('%H:%M:%S') if reserva['hora'] else None,
        'estado': reserva['estado'],
        'detalle': reserva['detalle']
    }


@app.route('/')
def home():
    return 'Bienvenido a la API de ReservaFacil!'

@app.route('/login', methods=['POST'])
def login():
    correo = request.json.get('correo', None)
    contrasena = request.json.get('contrasena', None)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, tipo_usuario FROM usuarios WHERE correo = %s AND contrasena = %s", (correo, contrasena))
    user_info = cursor.fetchone()
    cursor.close()
    conn.close()

    if user_info:
        access_token = create_access_token(identity={'user_id': user_info[0], 'tipo_usuario': user_info[1]})
        return jsonify(access_token=access_token), 200
    else:
        return jsonify({"error": "Credenciales inválidas"}), 401


@app.route('/reservas', methods=['POST'])
@jwt_required()
def crear_reserva():
    claims = get_jwt_identity()
    if claims['tipo_usuario'] not in ['super_administrador', 'administrador', 'usuario']:
        return jsonify({'error': 'Acción no permitida'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No se recibieron datos'}), 400

    required_fields = ['fecha', 'hora', 'estado', 'detalle']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({"error": f"Faltan campos obligatorios: {', '.join(missing_fields)}"}), 400

    try:
        fecha = datetime.strptime(data['fecha'], "%Y-%m-%d").date()
        hora = datetime.strptime(data['hora'], "%H:%M").time()
    except ValueError as e:
        return jsonify({"error": f"Formato de fecha o hora incorrecto: {str(e)}"}), 400

    usuario_responsable = claims['user_id']  # Obtiene el ID del usuario desde el JWT

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cursor.execute("SELECT numero_mesa FROM mesas WHERE disponible = TRUE LIMIT 1;")
        mesa = cursor.fetchone()
        if not mesa:
            return jsonify({'error': 'No hay mesas disponibles'}), 409

        numero_mesa = mesa['numero_mesa']
        
        cursor.execute(
            "INSERT INTO reservas (fecha, hora, estado, detalle, usuario_responsable, numero_mesa) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id, fecha, hora, estado, detalle;",
            (fecha, hora, data['estado'], data['detalle'], usuario_responsable, numero_mesa)
        )
        reserva = cursor.fetchone()
        if not reserva:
            return jsonify({'error': 'Error al crear la reserva'}), 500

        cursor.execute(
            "UPDATE mesas SET disponible = FALSE, usuario_responsable = %s WHERE numero_mesa = %s;",
            (usuario_responsable, numero_mesa)
        )

        reserva_serializada = serialize_reserva(reserva)
        conn.commit()
        return jsonify({"mensaje": "Reserva creada con éxito", "reserva": reserva_serializada}), 201
    except psycopg2.DatabaseError as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()



@app.route('/delete_reserva/<int:reserva_id>', methods=['DELETE'])
@jwt_required()
def delete_reserva(reserva_id):
    claims = get_jwt_identity()
    if claims['tipo_usuario'] != 'super_administrador':
        return jsonify({'error': 'Solo el super administrador puede eliminar reservas'}), 403

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT numero_mesa FROM reservas WHERE id = %s", (reserva_id,))
        reserva = cursor.fetchone()
        if reserva:
            cursor.execute("DELETE FROM reservas WHERE id = %s RETURNING id;", (reserva_id,))
            deleted_id = cursor.fetchone()
            if deleted_id:
                cursor.execute(
                    "UPDATE mesas SET disponible = True WHERE numero_mesa = %s;",
                    (reserva['numero_mesa'],)
                )
            conn.commit()
            return jsonify({"mensaje": "Reserva eliminada con éxito"}), 200
        else:
            return jsonify({"error": "Reserva no encontrada"}), 404
    except psycopg2.DatabaseError as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=3100)
