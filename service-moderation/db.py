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

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DB_PATH = os.environ.get("DB_PATH", "data.db")

# Le moteur : il sait parler à CETTE base (ici un fichier SQLite).
engine = create_engine(f"sqlite:///{DB_PATH}")

# Session : la "poignée" par laquelle on lit/écrit. On en ouvre une par requête.
Session = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    """Classe de base commune à tous les modèles."""


# --- Modèles : Modération ---------------------------------------------

class Signalement(Base):
    """Table stockant les signalements faits par les joueurs."""
    __tablename__ = "signalements"
    id: Mapped[int] = mapped_column(primary_key=True)
    pseudo_vise: Mapped[str] = mapped_column()
    raison: Mapped[str] = mapped_column()

class Banni(Base):
    """Table stockant la liste des joueurs actuellement bannis."""
    __tablename__ = "bannis"
    # On utilise le pseudo comme clé primaire car un joueur ne peut être banni qu'une seule fois
    pseudo: Mapped[str] = mapped_column(primary_key=True)
    motif: Mapped[str] = mapped_column()
    duree: Mapped[str] = mapped_column()

class Action(Base):
    """File d'actions exécutées en jeu par le mod"""
    __tablename__ = "actions"
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column()
    cible: Mapped[str] = mapped_column()
    
    objet: Mapped[str] = mapped_column(nullable=True) 
    statut: Mapped[str] = mapped_column(default="en_attente")


def init():
    """Crée les tables si elles n'existent pas. À APPELER au démarrage."""
    Base.metadata.create_all(engine)