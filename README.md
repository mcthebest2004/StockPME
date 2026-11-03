# StockPME — application Django monolithique

Gestion de stock pour une entreprise de vente, construite à partir du fichier `stockpme.html`, conservé comme référence. Le design reprend les couleurs pastel, les cartes, les statistiques, les polices Fraunces/Nunito et les palettes personnalisables. Les données métier sont enregistrées dans SQLite côté serveur. Django sert les pages HTML, les formulaires et les fichiers statiques : aucun frontend séparé, aucune API externe nécessaire.

## Installer et lancer

Prérequis : **Python 3.10 à 3.14**, avec `pip` et le module `venv`. Une connexion internet est nécessaire pour télécharger les dépendances. Sur Debian/Ubuntu, installer `python3-venv` si nécessaire.

### Linux / macOS

Depuis le dossier du projet :

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

### Windows (PowerShell)

L’utilisation directe du Python de l’environnement évite de devoir modifier la politique d’exécution PowerShell :

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver
```

Ouvrir **http://127.0.0.1:8000/**.

Compte de démonstration : **`demo`** / **`StockPME-demo-2026!`**.

`seed_demo` est facultatif. Il crée six articles et leur stock initial. Il refuse de modifier un compte déjà existant. Pour une autre démonstration : `python manage.py seed_demo --username demo2 --password "UnAutreMotDePasse!"`.

Pour une utilisation avec vos propres données, cliquer sur **Créer mon entreprise** à l’écran de connexion. Choisir le nom de l’entreprise, sa devise et un identifiant avec un mot de passe. Chaque compte possède son entreprise et ses données privées. Cette version prévoit **un compte gestionnaire par entreprise** ; elle ne comprend pas encore d’invitations de collaborateurs, de gestion multi-entrepôts, de facturation, de TVA ou de comptabilité.

## Fonctionnalités

- Inscription, connexion et déconnexion avec mots de passe hachés par Django.
- Catalogue d’articles : photo, nom, catégorie, prix de vente, quantité initiale et seuil d’alerte.
- Tableau de bord : références, unités, valeur au prix de vente, stocks bas.
- Recherche par nom ou catégorie, filtres et pagination.
- Entrées/réapprovisionnements, ventes et sorties/pertes. Les quantités négatives et sorties supérieures au stock sont refusées.
- Écriture atomique du stock et de l’historique. Les prix sont conservés au moment de chaque mouvement.
- Historique daté, avec utilisateur, référence et stock après mouvement.
- Archivage des articles à stock nul, avec conservation de l’historique.
- Export CSV du stock correspondant aux filtres actifs, compatible avec Excel (UTF-8, séparateur `;`).
- Photos privées accessibles seulement au propriétaire de l’entreprise (JPEG, PNG, WebP, 5 Mo / 20 millions de pixels maximum).
- Cinq palettes, couleurs personnalisables et modes clair, sombre et automatique. Les préférences visuelles sont enregistrées dans le navigateur.
- Administration Django consultable par un superutilisateur ; articles et mouvements sont en lecture seule pour préserver les règles de stock.

La connexion Google et le code personnel à quatre chiffres de la maquette sont remplacés par une authentification Django réelle. Les éventuelles données de l’ancienne maquette stockées dans le navigateur ne sont pas importées automatiquement. Les polices Google sont facultatives : sans internet, le navigateur utilise les polices de remplacement et l’application reste fonctionnelle.

## Tester

Dans l’environnement virtuel activé :

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Sous Windows, remplacer `python` par `.\.venv\Scripts\python.exe` si l’environnement n’est pas activé. Versions validées : Python 3.14.7, Django 5.2.17 et Pillow 12.3.0. Les tests utilisent une base temporaire et ne modifient pas votre stock.

Parcours manuel :

1. Se connecter avec le compte de démonstration.
2. Ajouter un article avec 10 unités, un prix et une photo.
3. Enregistrer une vente de 3 unités : le stock doit passer à 7.
4. Tenter une sortie de 8 unités : une erreur doit apparaître, sans changement du stock.
5. Enregistrer une entrée de 5 unités : le stock doit passer à 12.
6. Vérifier les mouvements dans l’historique et télécharger l’export CSV.
7. Créer une autre entreprise : son catalogue doit être vide.
8. Vérifier les thèmes, puis l’affichage sur téléphone.

Pour accéder à l’administration :

```bash
python manage.py createsuperuser
```

Ouvrir `http://127.0.0.1:8000/admin/`. Un superutilisateur créé en ligne de commande n’a pas automatiquement d’entreprise : utiliser le compte créé par inscription pour le catalogue.

## Structure

```text
config/                 Configuration, routage, WSGI et ASGI
stock/                  Modèles, formulaires, vues, services et tests
stock/migrations/       Schéma versionné de la base
stock/management/       Commande de démonstration
templates/              Pages HTML rendues par Django
static/stock/           Style issu de la maquette et JavaScript des thèmes
stockpme.html           Maquette originale
requirements.txt        Dépendances d’installation
```

`db.sqlite3` et `media/` sont créés localement ; les sauvegarder ensemble. `.local-secret-key` est généré automatiquement en développement et doit rester privé. Ne pas versionner ces fichiers ni l’environnement virtuel.

## Configuration de déploiement

La configuration par défaut sert à installer et tester localement. Pour un serveur public, utiliser un serveur WSGI/ASGI adapté et HTTPS, puis définir :

- `DJANGO_DEBUG=0`
- `DJANGO_SECRET_KEY` : une longue valeur aléatoire privée.
- `DJANGO_ALLOWED_HOSTS` : les domaines autorisés, séparés par des virgules.

Ces variables doivent être exportées dans l’environnement du processus ; un fichier `.env` n’est pas chargé automatiquement. Exécuter `python manage.py collectstatic` et configurer le serveur pour servir `staticfiles/`. Ne pas exposer `media/` directement : les photos passent par une vue Django qui vérifie l’utilisateur. SQLite convient à l’essai et à un usage modeste ; évaluer une autre base pour de nombreux utilisateurs simultanés. La gestion commerciale complète et le durcissement d’une installation publique (dont limitation des tentatives de connexion) restent à adapter au déploiement.
"# StockPME" 
