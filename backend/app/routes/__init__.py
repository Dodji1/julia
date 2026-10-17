from backend.app.routes import answers, documents, feedback, health, search

ROUTERS = [answers.router, search.router, documents.router, feedback.router, health.router]
