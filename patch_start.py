import re

# Read the file with UTF-8 encoding
with open('start.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Simple approach: find line number where to insert
lines = content.split('\n')
insert_after = -1
for i, line in enumerate(lines):
    if 'run_scheduler()' in line and i > 0 and 'actualizarllamadas' in lines[i-2]:
        insert_after = i
        break

if insert_after \!= -1:
    new_lines = [
        '',
        '    elif "api-centros" in service_name or "centros" in service_name:',
        '        logging.info("Iniciando el servicio API de centros...")',
        '        if use_gunicorn:',
        '            port = os.getenv("PORT", "5000")',
        '            gunicorn_command = [',
        '                "gunicorn", "--bind", f"0.0.0.0:{port}",',
        '                "--workers", "2", "--timeout", "120",',
        '                "--log-level", "info", "api_centros:app"',
        '            ]',
        '            logging.info(f"Lanzando Gunicorn para API Centros: {\' \'.join(gunicorn_command)}")',
        '            os.execvp("gunicorn", gunicorn_command)',
        '        else:',
        '            from api_centros import app',
        '            app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)'
    ]
    
    # Insert new lines
    lines[insert_after:insert_after] = new_lines
    
    # Write back
    with open('start.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print('Archivo modificado exitosamente')
else:
    print('No se encontró la sección para insertar')
EOF < /dev/null
