# -*- coding: utf-8 -*-
"""
database/setup.py
Создаём единственный экземпляр SQLAlchemy.
Импортируется и в app.py и в models.py — не дублируется.
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    """Привязываем db к Flask приложению."""
    db.init_app(app)
    with app.app_context():
        from . import models  # noqa — регистрируем все модели
        db.create_all()
    return db