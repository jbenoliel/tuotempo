"""
Helper para acceder y manejar logs en Railway.

Este script proporciona funciones para acceder a los logs de tuotempo
tanto en entorno local como en Railway.
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

def is_railway_environment():
    """Detecta si estamos ejecutando en Railway."""
    return os.getenv('RAILWAY_ENVIRONMENT') is not None

def get_tuotempo_logs_path():
    """Obtiene la ruta donde están los logs de tuotempo según el entorno."""
    if is_railway_environment():
        return Path("/tmp/tuotempo_api_calls.log")
    else:
        return Path("logs/tuotempo_api_calls.log")

def read_tuotempo_logs(max_lines=50):
    """
    Lee los logs de tuotempo.

    Args:
        max_lines (int): Número máximo de líneas a leer

    Returns:
        list: Lista de entradas de log parseadas
    """
    log_path = get_tuotempo_logs_path()

    if not log_path.exists():
        print(f"Archivo de log no encontrado: {log_path}")
        return []

    logs = []
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Tomar las últimas líneas
            for line in lines[-max_lines:]:
                try:
                    # El formato es: [TUOTEMPO_API] timestamp | json_data
                    if '|' in line and '[TUOTEMPO_API]' in line:
                        json_part = line.split('|', 1)[1].strip()
                        log_entry = json.loads(json_part)
                        logs.append(log_entry)
                except json.JSONDecodeError:
                    # Si no se puede parsear, añadir como texto plano
                    logs.append({"raw_line": line.strip()})
    except Exception as e:
        print(f"Error al leer logs: {e}")

    return logs

def filter_logs_by_time(logs, hours_ago=1):
    """
    Filtra logs por tiempo.

    Args:
        logs (list): Lista de logs
        hours_ago (int): Horas hacia atrás a filtrar

    Returns:
        list: Logs filtrados
    """
    cutoff_time = datetime.now() - timedelta(hours=hours_ago)
    filtered_logs = []

    for log in logs:
        if "timestamp" in log:
            try:
                log_time = datetime.fromisoformat(log["timestamp"].replace('Z', '+00:00'))
                if log_time.replace(tzinfo=None) >= cutoff_time:
                    filtered_logs.append(log)
            except:
                # Si no se puede parsear la fecha, incluir el log
                filtered_logs.append(log)
        else:
            # Si no tiene timestamp, incluir
            filtered_logs.append(log)

    return filtered_logs

def get_railway_service_logs():
    """
    Intenta obtener logs directamente de Railway usando CLI.
    Solo funciona si railway CLI está instalado y configurado.
    """
    if not is_railway_environment():
        print("Esta función solo funciona cuando se ejecuta desde Railway")
        return

    try:
        result = subprocess.run(
            ['railway', 'logs', '--json'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout
        else:
            print(f"Error al obtener logs de Railway: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("Timeout al obtener logs de Railway")
    except FileNotFoundError:
        print("Railway CLI no encontrado")
    except Exception as e:
        print(f"Error ejecutando railway logs: {e}")

    return None

def print_logs_summary(logs):
    """
    Imprime un resumen de los logs.

    Args:
        logs (list): Lista de logs a resumir
    """
    if not logs:
        print("No se encontraron logs")
        return

    print(f"\n=== Resumen de {len(logs)} entradas de log ===")

    successful_calls = 0
    failed_calls = 0
    functions_called = {}

    for log in logs:
        if "success" in log:
            if log["success"]:
                successful_calls += 1
            else:
                failed_calls += 1

        # Contar funciones/métodos llamados
        function_name = log.get("function", log.get("method", "unknown"))
        functions_called[function_name] = functions_called.get(function_name, 0) + 1

    print(f"Llamadas exitosas: {successful_calls}")
    print(f"Llamadas fallidas: {failed_calls}")
    print(f"Total: {successful_calls + failed_calls}")

    if functions_called:
        print("\nFunciones más llamadas:")
        for func, count in sorted(functions_called.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {func}: {count} veces")

def print_recent_logs(max_entries=10):
    """
    Imprime los logs más recientes de forma legible.

    Args:
        max_entries (int): Número máximo de entradas a mostrar
    """
    logs = read_tuotempo_logs(max_entries)

    print(f"\n=== Últimos {min(len(logs), max_entries)} logs de APIs de tuotempo ===")

    for i, log in enumerate(logs[-max_entries:], 1):
        if "raw_line" in log:
            print(f"{i}. {log['raw_line']}")
        else:
            timestamp = log.get("timestamp", "N/A")
            function = log.get("function", log.get("method", "N/A"))
            success = "✓" if log.get("success") else "✗"
            error = log.get("error", "")

            print(f"{i}. [{timestamp}] {function} {success}")
            if error:
                print(f"   Error: {error}")

def main():
    """Función principal para testing."""
    print("=== Railway Logs Helper ===")
    print(f"Entorno: {'Railway' if is_railway_environment() else 'Local'}")
    print(f"Ruta de logs: {get_tuotempo_logs_path()}")

    # Leer y mostrar logs
    logs = read_tuotempo_logs()
    print_logs_summary(logs)
    print_recent_logs()

    # Si estamos en Railway, también intentar obtener logs del servicio
    if is_railway_environment():
        print("\n=== Intentando obtener logs de Railway CLI ===")
        railway_logs = get_railway_service_logs()
        if railway_logs:
            print("Logs obtenidos de Railway CLI:")
            print(railway_logs[:1000] + "..." if len(railway_logs) > 1000 else railway_logs)

if __name__ == "__main__":
    main()