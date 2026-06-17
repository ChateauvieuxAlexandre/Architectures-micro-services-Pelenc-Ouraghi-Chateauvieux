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


# --- Modèles de la Boutique (G4) -----------------------------------------------
class Objet(Base):
    __tablename__ = "objets"
    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str]
    prix: Mapped[int]
    item: Mapped[str]  # Exemple : "default:pick_steel 1"
class Livraison(Base):
    __tablename__ = "livraisons"
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(default="livrer_objet")
    cible: Mapped[str]  # Le pseudo du joueur qui doit recevoir l'objet
    objet: Mapped[str]  # L'itemstring Luanti à livrer
    statut: Mapped[str] = mapped_column(default="en_attente") # "en_attente" ou "fait"

def init():
    """Crée les tables si elles n'existent pas. À APPELER au démarrage."""
    Base.metadata.create_all(engine)
    seed()

def seed():
    """Génère quelques données logiques au démarrage si le catalogue est vide."""
    with Session() as db:
        if db.query(Objet).count() == 0:
            objets_initiaux = [
                Objet(nom="Pioche en acier", prix=15, item="default:pick_steel 1"),
                Objet(nom="Épée en diamant", prix=50, item="default:sword_diamond 1"),
                Objet(nom="Pomme dorée", prix=10, item="default:apple_gold 1"),
                Objet(nom="Torche (x10)", prix=5, item="default:torch 10"),
                Objet(nom="Bloc de diamants", prix=100, item="default:diamondblock 1")
            ]
            db.add_all(objets_initiaux)
            
            # Optionnel : une livraison déjà en attente pour tester
            livraison_test = Livraison(
                cible="maxime", 
                objet="default:pick_steel 1", 
                statut="en_attente"
            )
            db.add(livraison_test)
            
            db.commit()
            print("Base de données boutique initialisée avec des données logiques.")