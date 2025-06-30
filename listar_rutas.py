#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para listar todas las rutas disponibles en la aplicación Flask.
"""

from app_dashboard import app

if __name__ == "__main__":
    print("=== RUTAS DISPONIBLES EN LA APLICACIÓN ===")
    for rule in app.url_map.iter_rules():
        print(f"Ruta: {rule.rule}")
        print(f"  Endpoint: {rule.endpoint}")
        print(f"  Métodos: {', '.join(rule.methods)}")
        print()
