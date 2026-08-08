from dotenv import load_dotenv
from fastapi import FastAPI

import repository

load_dotenv()

app = FastAPI(title='Task API', version='1.0')

repository.init_db()


@app.get('/', summary='API metadata', description='Returns the API name, version, and top-level endpoints.')
def root() -> dict:
    return {'name': 'Task API', 'version': '1.0', 'endpoints': ['/tasks']}


@app.get('/health', summary='Health check', description='Returns an OK status so monitors can verify the server is running.')
def health() -> dict:
    return {'status': 'ok'}
