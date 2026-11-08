# webapp

Panel Flask sobre DynamoDB (región `us-east-1`) pensado para correr en EC2.

## Estructura

```
webapp/
├── app.py              # aplicación Flask (CRUD + consultas)
├── templates/          # index.html, consultas.html
├── tests/              # pruebas de humo (sin AWS real)
├── requirements.txt
├── requirements-dev.txt
```

## Ejecutar local

```bash
pip install -r requirements.txt
export AWS_DEFAULT_REGION=us-east-1   # y credenciales AWS válidas
python app.py                         # escucha en 0.0.0.0:80
```

## Análisis automático (GitHub Actions)

| Workflow | Qué hace |
|----------|----------|
| `analisis.yml` | Todo en uno: flake8, pytest (Python 3.11 y 3.12), Bandit, pip-audit y CodeQL |
| `dependabot.yml` | Actualizaciones semanales de dependencias y Actions |
