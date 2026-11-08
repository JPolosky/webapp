"""Pruebas de humo: no requieren credenciales AWS ni tablas reales."""
import os
import sys

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as webapp  # noqa: E402


def cliente():
    webapp.app.testing = True
    return webapp.app.test_client()


def test_index_carga():
    r = cliente().get("/")
    assert r.status_code == 200


def test_consultas_carga():
    r = cliente().get("/consultas")
    assert r.status_code == 200


def test_tabla_no_permitida():
    r = cliente().get("/api/tabla_inexistente")
    assert r.status_code == 404


def test_consulta_no_encontrada():
    r = cliente().get("/q/no_existe")
    assert r.status_code == 404


def test_esquema_tiene_las_7_tablas():
    assert set(webapp.TABLAS) == {
        "clientes", "productos", "ventas", "proveedores",
        "inventario", "sucursales", "compras",
    }
