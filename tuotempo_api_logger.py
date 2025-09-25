import os
import json
import logging
from datetime import datetime
from functools import wraps
import requests
from pathlib import Path

class TuoTempoAPILogger:
    """
    Logger especializado para registrar todas las llamadas a las APIs de tuotempo
    con método, parámetros, resultado y timestamp.
    """

    def __init__(self, log_file_path=None):
        """
        Inicializa el logger de APIs de tuotempo.

        Args:
            log_file_path (str): Ruta del archivo de log. Si es None, usa un archivo por defecto.
        """
        # Detectar si estamos en Railway
        is_railway = os.getenv('RAILWAY_ENVIRONMENT') is not None

        if log_file_path is None:
            if is_railway:
                # En Railway, usar /tmp para archivos temporales
                log_dir = Path("/tmp")
                log_file_path = log_dir / "tuotempo_api_calls.log"
            else:
                # En local, usar directorio logs
                log_dir = Path("logs")
                log_dir.mkdir(exist_ok=True)
                log_file_path = log_dir / "tuotempo_api_calls.log"

        self.log_file_path = log_file_path
        self.is_railway = is_railway

        # Configurar logger específico para APIs de tuotempo
        self.logger = logging.getLogger('tuotempo_api_calls')
        self.logger.setLevel(logging.INFO)

        # Evitar duplicar handlers si ya existen
        if not self.logger.handlers:
            # Formato específico para APIs de tuotempo
            formatter = logging.Formatter(
                '[TUOTEMPO_API] %(asctime)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

            if is_railway:
                # En Railway, también loggear a stdout/stderr para que aparezca en los logs de Railway
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)

            # Handler para archivo (siempre, incluso en Railway)
            try:
                file_handler = logging.FileHandler(
                    self.log_file_path,
                    encoding='utf-8',
                    mode='a'
                )
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            except Exception as e:
                # Si no se puede crear el archivo, solo usar console en Railway
                if is_railway and not any(isinstance(h, logging.StreamHandler) for h in self.logger.handlers):
                    console_handler = logging.StreamHandler()
                    console_handler.setFormatter(formatter)
                    self.logger.addHandler(console_handler)

            # Prevenir propagación al logger raíz
            self.logger.propagate = False

    def log_api_call(self, method, endpoint, params=None, payload=None, response=None, error=None):
        """
        Registra una llamada a la API de tuotempo.

        Args:
            method (str): Método HTTP (GET, POST, DELETE, etc.)
            endpoint (str): Endpoint de la API
            params (dict): Parámetros de la llamada
            payload (dict): Payload enviado (para POST, PUT, etc.)
            response (dict): Respuesta recibida
            error (str): Error ocurrido si hay alguno
        """
        timestamp = datetime.now().isoformat()

        log_entry = {
            "timestamp": timestamp,
            "method": method,
            "endpoint": endpoint,
            "params": params or {},
            "payload": payload or {},
            "response": response or {},
            "error": error,
            "success": error is None
        }

        # Convertir a JSON para el log
        log_message = json.dumps(log_entry, ensure_ascii=False, separators=(',', ':'))
        self.logger.info(log_message)

    def log_tuotempo_call(self, function_name, args=None, kwargs=None, result=None, error=None):
        """
        Registra una llamada a cualquier función de la clase Tuotempo.

        Args:
            function_name (str): Nombre de la función llamada
            args (tuple): Argumentos posicionales
            kwargs (dict): Argumentos con nombre
            result (any): Resultado de la función
            error (str): Error ocurrido si hay alguno
        """
        timestamp = datetime.now().isoformat()

        log_entry = {
            "timestamp": timestamp,
            "function": function_name,
            "args": list(args) if args else [],
            "kwargs": kwargs or {},
            "result": result,
            "error": error,
            "success": error is None
        }

        # Convertir a JSON para el log
        log_message = json.dumps(log_entry, ensure_ascii=False, separators=(',', ':'))
        self.logger.info(log_message)


# Instancia global del logger
tuotempo_logger = TuoTempoAPILogger()


def log_tuotempo_api_call(func):
    """
    Decorador para loggear automáticamente las llamadas a APIs de tuotempo.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        function_name = func.__name__
        error = None
        result = None

        try:
            result = func(*args, **kwargs)
            tuotempo_logger.log_tuotempo_call(
                function_name=function_name,
                args=args[1:],  # Excluir 'self'
                kwargs=kwargs,
                result=result,
                error=None
            )
            return result
        except Exception as e:
            error = str(e)
            tuotempo_logger.log_tuotempo_call(
                function_name=function_name,
                args=args[1:],  # Excluir 'self'
                kwargs=kwargs,
                result=None,
                error=error
            )
            raise  # Re-lanzar la excepción

    return wrapper


def log_requests_call(method, url, **kwargs):
    """
    Función wrapper para requests que loggea automáticamente las llamadas HTTP.

    Args:
        method (str): Método HTTP
        url (str): URL de la llamada
        **kwargs: Argumentos adicionales para requests

    Returns:
        requests.Response: Respuesta HTTP
    """
    error = None
    response = None
    response_data = None

    try:
        # Realizar la llamada HTTP real
        if method.upper() == 'GET':
            response = requests.get(url, **kwargs)
        elif method.upper() == 'POST':
            response = requests.post(url, **kwargs)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, **kwargs)
        elif method.upper() == 'PUT':
            response = requests.put(url, **kwargs)
        else:
            response = requests.request(method, url, **kwargs)

        # Intentar obtener JSON de la respuesta
        try:
            response_data = response.json()
        except:
            response_data = response.text[:500] + "..." if len(response.text) > 500 else response.text

        # Loggear la llamada
        tuotempo_logger.log_api_call(
            method=method.upper(),
            endpoint=url,
            params=kwargs.get('params'),
            payload=kwargs.get('json'),
            response=response_data,
            error=None
        )

        return response

    except Exception as e:
        error = str(e)
        tuotempo_logger.log_api_call(
            method=method.upper(),
            endpoint=url,
            params=kwargs.get('params'),
            payload=kwargs.get('json'),
            response=None,
            error=error
        )
        raise  # Re-lanzar la excepción