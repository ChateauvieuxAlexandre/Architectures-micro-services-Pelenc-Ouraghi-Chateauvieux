"""Base de données du service, via un ORM : SQLAlchemy.

Auteur : Philippe ROUSSILLE <roussille@3il.fr>

Un ORM (Object-Relational Mapper) fait le pont entre des OBJETS Python et des
LIGNES de table : vous manipulez des objets, l'ORM écrit le SQL à votre place.
Principe micro-services : ce service possède SA base, un simple fichier SQLite
(inclus dans Python, aucun serveur à installer). Le chemin passe par une variable
d'environnement pour pouvoir le mettre dans un volume Docker (voir
docker-compose.yml). Vous avez découvert ce pattern au TP 12.
"""
import os
from datetime import datetime, timezone

from sqlalchemy import DateTime, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DB_PATH = os.environ.get("DB_PATH", "data.db")

# Le moteur : il sait parler à CETTE base (ici un fichier SQLite).
engine = create_engine(f"sqlite:///{DB_PATH}")

# Session : la "poignée" par laquelle on lit/écrit. On en ouvre une par requête.
Session = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    """Classe de base commune à tous vos modèles."""


# --- Vos modèles : À ÉCRIRE -----------------------------------------------
# Une table = une classe, une colonne = un attribut. Squelette type :
#
#   class Truc(Base):
#       __tablename__ = "trucs"
#       id: Mapped[int] = mapped_column(primary_key=True)
#       nom: Mapped[str]
#
# Définissez ici les tables de VOTRE domaine (comptes, objets, scores...).
class Score(Base):
    __tablename__ = "scores"
    id: Mapped[int] = mapped_column(primary_key=True)
    pseudo: Mapped[str] = mapped_column(unique=True)
    points: Mapped[int] = mapped_column(default=0)


class Gain(Base):
    """Historique horodaté des gains de points (bonus : classements par période)."""

    __tablename__ = "gains"
    id: Mapped[int] = mapped_column(primary_key=True)
    pseudo: Mapped[str]
    points: Mapped[int]
    horodatage: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


def init():
    """Crée les tables si elles n'existent pas. À APPELER au démarrage."""
    Base.metadata.create_all(engine)
