# 📊 Alpaca Tax Analyzer

> Analyseur fiscal & performance pour résidents fiscaux français utilisant **Alpaca Securities**

## 🌐 Déploiement
Hébergé sur Vercel — déployé automatiquement depuis GitHub.

## 💻 Lancement local
```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## 📁 Structure
```
├── main.py          ← Backend FastAPI (API /api/upload)
├── public/
│   └── index.html   ← Frontend complet (HTML/JS/CSS)
├── requirements.txt
├── vercel.json
└── .gitignore
```
