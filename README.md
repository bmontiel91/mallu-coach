# Mallu Coach

App de fitness + salud + nutrición con IA conectada a Google Sheets.

## Arquitectura

- **Frontend**: GitHub Pages (`https://bmontiel91.github.io/mallu-coach/`)
- **Backend**: Python + Google Sheets API + Visión IA
- **Hosting Backend**: Render

## Deploy

### 1. Backend (Render)

1. Conectá tu repo a https://render.com
2. Creá un **Web Service**
3. Apuntá a este repo, branch `main`
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `gunicorn server:app`
6. Listo

### 2. Frontend (GitHub Pages)

1. Settings → Pages → Source: GitHub Actions
2. O usá el action que ya viene configurado

La URL del backend se configura en `index.html` (variable `API_URL`).
