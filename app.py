from decimal import Decimal
from flask import Flask, jsonify, render_template, request
import boto3

app = Flask(__name__)

REGION = "us-east-1"   # <-- cámbiala si tus tablas están en otra región

ESQUEMA = {
    "clientes":    {"clienteId": "S", "nombre": "S", "ciudad": "S", "correo": "S"},
    "productos":   {"productoId": "S", "nombre": "S", "categoria": "S", "precio": "N"},
    "ventas":      {"ventaId": "S", "fecha": "S", "clienteId": "S", "productoId": "S", "cantidad": "N"},
    "proveedores": {"proveedorId": "S", "nombre": "S", "ciudad": "S", "telefono": "S", "correo": "S"},
    "inventario":  {"inventarioId": "S", "productoId": "S", "sucursalId": "S", "cantidad": "N", "stockMinimo": "N"},
    "sucursales":  {"sucursalId": "S", "nombre": "S", "ciudad": "S", "direccion": "S", "telefono": "S"},
    "compras":     {"compraId": "S", "proveedorId": "S", "productoId": "S", "fecha": "S", "cantidad": "N", "total": "N"},
}
TABLAS = list(ESQUEMA.keys())

dynamodb = boto3.resource("dynamodb", region_name=REGION)
CLAVES = {}


def limpiar(valor):
    if isinstance(valor, Decimal):
        return int(valor) if valor == valor.to_integral_value() else float(valor)
    if isinstance(valor, dict):
        return {k: limpiar(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [limpiar(v) for v in valor]
    return valor


def clave_de(nombre):
    if nombre not in CLAVES:
        try:
            desc = dynamodb.meta.client.describe_table(TableName=nombre)
            CLAVES[nombre] = desc["Table"]["KeySchema"][0]["AttributeName"]
        except Exception:
            CLAVES[nombre] = next(iter(ESQUEMA[nombre]))
    return CLAVES[nombre]


def leer_tabla(nombre):
    tabla = dynamodb.Table(nombre)
    resp = tabla.scan()
    items = resp["Items"]
    while "LastEvaluatedKey" in resp:
        resp = tabla.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
        items.extend(resp["Items"])
    return [limpiar(i) for i in items]


def preparar(tabla, datos):
    esquema = ESQUEMA[tabla]
    item = {}
    for k, v in datos.items():
        if v is None or v == "":
            continue
        if esquema.get(k) == "N":
            try:
                v = Decimal(str(v))
            except Exception:
                raise ValueError(f"'{k}' debe ser un número")
        item[k] = v
    return item


def error(e, codigo=500):
    return jsonify({"error": str(e)}), codigo


# ====================== PÁGINAS ======================
@app.route("/")
def index():
    return render_template("index.html", tablas=TABLAS)


@app.route("/consultas")
def pagina_consultas():
    return render_template("consultas.html")


# ====================== CONSULTAS ======================
def q_cliente(p):
    cid = p.get("id", "").strip().upper()
    it = dynamodb.Table("clientes").get_item(Key={"clienteId": cid}).get("Item")
    it = limpiar(it) if it else None
    filas = [[it.get("clienteId"), it.get("nombre"), it.get("ciudad"), it.get("correo")]] if it else []
    return {"columnas": ["ClienteId", "Nombre", "Ciudad", "Correo"], "filas": filas,
            "vacio": f"No existe un cliente con ID «{cid}»."}


def q_productos_precio(p):
    minimo = float(p.get("min", 1000))
    filas = [[x.get("productoId"), x.get("nombre"), x.get("categoria"), x.get("precio", 0)]
             for x in leer_tabla("productos") if x.get("precio", 0) > minimo]
    filas.sort(key=lambda f: -f[3])
    return {"columnas": ["ProductoId", "Nombre", "Categoría", "Precio"], "filas": filas,
            "dinero": [3], "vacio": "Ningún producto supera ese precio."}


def q_sucursales(p):
    ciudad = p.get("ciudad", "").strip().lower()
    filas = [[s.get("sucursalId"), s.get("nombre"), s.get("ciudad"), s.get("direccion"), s.get("telefono")]
             for s in leer_tabla("sucursales") if s.get("ciudad", "").lower() == ciudad]
    return {"columnas": ["SucursalId", "Nombre", "Ciudad", "Dirección", "Teléfono"], "filas": filas,
            "vacio": "No hay sucursales en esa ciudad."}


def q_reto3(p):
    ciudad = p.get("ciudad", "Medellín").strip().lower()
    clientes = {c["clienteId"]: c for c in leer_tabla("clientes")
                if c.get("ciudad", "").lower() == ciudad}
    productos = {x["productoId"]: x for x in leer_tabla("productos")}
    filas = []
    for v in leer_tabla("ventas"):
        c = clientes.get(v.get("clienteId"))
        pr = productos.get(v.get("productoId"))
        if c and pr:
            filas.append([pr.get("nombre"), pr.get("categoria"), c.get("nombre"), c.get("ciudad")])
    return {"columnas": ["Producto", "Categoría", "Cliente", "Ciudad"], "filas": filas,
            "vacio": "No se vendieron productos a clientes de esa ciudad."}


def q_reto4(p):
    precios = {x["productoId"]: x for x in leer_tabla("productos")}
    totales = {}
    for v in leer_tabla("ventas"):
        pr = precios.get(v.get("productoId"))
        if pr:
            cat = pr.get("categoria", "Sin categoría")
            totales[cat] = totales.get(cat, 0) + v.get("cantidad", 0) * pr.get("precio", 0)
    filas = sorted(([k, v] for k, v in totales.items()), key=lambda f: -f[1])
    filas.append(["TOTAL", sum(totales.values())])
    return {"columnas": ["Categoría", "Ingresos"], "filas": filas, "dinero": [1],
            "total": True, "vacio": "No hay ventas registradas."}


def q_reto5(p):
    categoria = p.get("categoria", "Almacenamiento").strip().lower()
    ids_prod = {x["productoId"] for x in leer_tabla("productos")
                if x.get("categoria", "").lower() == categoria}
    ids_cli = {v["clienteId"] for v in leer_tabla("ventas")
               if v.get("productoId") in ids_prod and v.get("clienteId")}
    filas = [[c.get("clienteId"), c.get("nombre"), c.get("ciudad"), c.get("correo")]
             for c in leer_tabla("clientes") if c.get("clienteId") in ids_cli]
    filas.sort(key=lambda f: f[0])
    return {"columnas": ["ClienteId", "Nombre", "Ciudad", "Correo"], "filas": filas,
            "vacio": "Ningún cliente compró productos de esa categoría "
                     "(puede que no existan productos con ella)."}


CONSULTAS = {"cliente": q_cliente, "productos_precio": q_productos_precio,
             "sucursales": q_sucursales, "reto3": q_reto3, "reto4": q_reto4, "reto5": q_reto5}


@app.route("/q/opciones")
def q_opciones():
    try:
        ciudades = sorted({c.get("ciudad") for c in leer_tabla("clientes") if c.get("ciudad")} |
                          {s.get("ciudad") for s in leer_tabla("sucursales") if s.get("ciudad")})
        categorias = sorted({x.get("categoria") for x in leer_tabla("productos") if x.get("categoria")})
        return jsonify({"ciudades": ciudades, "categorias": categorias})
    except Exception as e:
        return error(e)


@app.route("/q/<nombre>")
def ejecutar_consulta(nombre):
    if nombre not in CONSULTAS:
        return error("Consulta no encontrada", 404)
    try:
        return jsonify(CONSULTAS[nombre](request.args))
    except ValueError:
        return error("Valor no válido en el parámetro", 400)
    except Exception as e:
        return error(e)


# ====================== API CRUD ======================
@app.route("/api/resumen")
def resumen():
    try:
        clientes = leer_tabla("clientes")
        productos = leer_tabla("productos")
        ventas = leer_tabla("ventas")
        precios = {p["productoId"]: p.get("precio", 0) for p in productos}
        ingresos = sum(v.get("cantidad", 0) * precios.get(v.get("productoId"), 0) for v in ventas)
        return jsonify({"clientes": len(clientes), "productos": len(productos),
                        "ventas": len(ventas), "ingresos": ingresos})
    except Exception as e:
        return error(e)


@app.route("/api/<tabla>", methods=["GET"])
def listar(tabla):
    if tabla not in TABLAS:
        return error("Tabla no permitida", 404)
    try:
        items = leer_tabla(tabla)
        clave = clave_de(tabla)
        tipos = dict(ESQUEMA[tabla])
        columnas = list(tipos.keys())
        for i in items:
            for k, v in i.items():
                if k not in tipos:
                    tipos[k] = "N" if isinstance(v, (int, float)) else "S"
                    columnas.append(k)
        if clave in columnas:
            columnas.remove(clave)
        columnas.insert(0, clave)
        return jsonify({"clave": clave, "columnas": columnas, "tipos": tipos, "items": items})
    except Exception as e:
        return error(e)


@app.route("/api/<tabla>", methods=["POST"])
def crear(tabla):
    if tabla not in TABLAS:
        return error("Tabla no permitida", 404)
    try:
        clave = clave_de(tabla)
        item = preparar(tabla, request.get_json(force=True))
        if clave not in item:
            return error(f"El campo '{clave}' es obligatorio", 400)
        dynamodb.Table(tabla).put_item(
            Item=item, ConditionExpression=f"attribute_not_exists({clave})")
        return jsonify({"ok": True})
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return error("Ya existe un registro con ese ID", 409)
    except ValueError as e:
        return error(e, 400)
    except Exception as e:
        return error(e)


@app.route("/api/<tabla>/<valor>", methods=["PUT"])
def editar(tabla, valor):
    if tabla not in TABLAS:
        return error("Tabla no permitida", 404)
    try:
        clave = clave_de(tabla)
        item = preparar(tabla, request.get_json(force=True))
        item[clave] = valor
        dynamodb.Table(tabla).put_item(
            Item=item, ConditionExpression=f"attribute_exists({clave})")
        return jsonify({"ok": True})
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return error("El registro ya no existe", 404)
    except ValueError as e:
        return error(e, 400)
    except Exception as e:
        return error(e)


@app.route("/api/<tabla>/<valor>", methods=["DELETE"])
def eliminar(tabla, valor):
    if tabla not in TABLAS:
        return error("Tabla no permitida", 404)
    try:
        dynamodb.Table(tabla).delete_item(Key={clave_de(tabla): valor})
        return jsonify({"ok": True})
    except Exception as e:
        return error(e)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
