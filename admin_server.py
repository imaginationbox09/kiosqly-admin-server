import base64
import os
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Memoria temporal para guardar el último estado recibido del kiosco
device_status = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Panel de Control - Kiosqly</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f6f9; margin: 20px; text-align: center; }
        .card { background: white; border-radius: 10px; padding: 20px; max-width: 500px; margin: 0 auto; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        .status { font-weight: bold; color: green; }
        .btn { background: #007bff; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Kiosqly Control Panel 🚀</h1>
        <p>Estado del Servidor: <span class="status">En Línea (Render)</span></p>
        <hr>
        <h3>Último Kiosco Sincronizado</h3>
        {% if status %}
            <p><b>Dispositivo:</b> {{ status.get('device_id', 'Desconocido') }}</p>
            <p><b>Batería:</b> {{ status.get('battery', 'N/A') }}%</p>
            <p><b>URL Actual:</b> {{ status.get('current_url', 'N/A') }}</p>
        {% else %}
            <p>Esperando conexión del primer kiosco...</p>
        {% endif %}
        <a href="/" class="btn">Actualizar Panel</a>
    </div>
</body>
</html>
"""


@app.route('/')
def home():
  # Al entrar a la raíz, muestra el panel visual en lugar de 'Not Found'
  return render_template_string(HTML_TEMPLATE, status=device_status)


@app.route('/heartbeat', methods=['POST'])
def heartbeat():
  global device_status
  data = request.get_json(silent=True) or {}
  device_status = data
  print(f'Heartbeat recibido de: {data.get("device_id")}')

  # Respuestas con instrucciones para la app (si quieres cambiar la URL desde la nube)
  response_data = {
      'status': 'ok',
      # 'url': 'https://kiosqly.com', # Descomenta si quieres forzar cambio de URL remota
      # 'capture_image': True         # Descomenta si quieres solicitar una foto remota
  }
  return jsonify(response_data), 200


@app.route('/upload_image', methods=['POST'])
def upload_image():
  data = request.get_json(silent=True) or {}
  image_data = data.get('image_data')

  if image_data:
    # Guardar o procesar la foto recibida en base64
    print('¡Foto remota recibida con éxito!')
    return jsonify({'status': 'photo_received'}), 200

  return jsonify({'status': 'no_image'}), 400


if __name__ == '__main__':
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port)
