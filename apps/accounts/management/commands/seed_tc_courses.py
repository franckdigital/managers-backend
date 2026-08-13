"""
Management command: seed_tc_courses
Creates 20 courses for Tech Innovation Center (training_center_admin as instructor).

Prerequisites: run `python manage.py seed_demo` first.

Usage:
    python manage.py seed_tc_courses
    python manage.py seed_tc_courses --reset
"""

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


def _yt(video_id):
    return f'https://www.youtube.com/embed/{video_id}'


def _past(n):
    return timezone.now() - timedelta(days=n)


TC_COURSES = [
    # ── Digital Skills ──────────────────────────────────────────────────────────
    {
        'title': 'Bureautique Avancée — Excel, Word & PowerPoint',
        'subtitle': 'Maîtrisez la suite Office pour gagner en productivité',
        'description': (
            'Formation complète sur Microsoft Office : tableaux croisés dynamiques Excel, '
            'macros VBA de base, publipostage Word et présentations impactantes PowerPoint. '
            'Idéal pour les collaborateurs souhaitant optimiser leur usage quotidien des outils bureautiques.'
        ),
        'category': 'Informatique & Technologie',
        'level': 'beginner',
        'price': 35000,
        'sections': [
            {'title': 'Excel Avancé', 'chapters': [
                {'title': 'Tableaux croisés dynamiques', 'lessons': [
                    {'title': 'Créer et configurer un TCD', 'content_type': 'video', 'duration_seconds': 900, 'is_preview_free': True},
                    {'title': 'Filtres, segments et chronologies', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Formules avancées : INDEX, EQUIV, RECHERCHEV', 'content_type': 'video', 'duration_seconds': 960},
                ]},
            ]},
            {'title': 'Word & PowerPoint Pro', 'chapters': [
                {'title': 'Documents et présentations professionnels', 'lessons': [
                    {'title': 'Styles et modèles Word', 'content_type': 'video', 'duration_seconds': 720},
                    {'title': 'Publipostage et fusion de courrier', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Slides PowerPoint à fort impact visuel', 'content_type': 'video', 'duration_seconds': 900},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Bureautique Avancée',
            'questions': [
                {
                    'text': 'Dans Excel, quelle fonction retourne la valeur d\'une cellule à l\'intersection d\'une ligne et d\'une colonne spécifiées ?',
                    'choices': [
                        {'text': 'INDEX', 'is_correct': True},
                        {'text': 'RECHERCHEV', 'is_correct': False},
                        {'text': 'SOMME.SI', 'is_correct': False},
                        {'text': 'NB.SI', 'is_correct': False},
                    ],
                    'explanation': 'INDEX retourne la valeur d\'une cellule en se basant sur les numéros de ligne et colonne.',
                },
            ],
        },
    },
    {
        'title': 'Outils Collaboratifs — Microsoft 365 & Google Workspace',
        'subtitle': 'Teams, SharePoint, Google Drive et travail en équipe à distance',
        'description': (
            'Optimisez le travail collaboratif avec les suites cloud : '
            'Microsoft Teams, SharePoint, OneDrive, Google Meet, Drive et Docs. '
            'Gestion de projets distants, réunions efficaces et co-édition en temps réel.'
        ),
        'category': 'Informatique & Technologie',
        'level': 'beginner',
        'price': 29000,
        'sections': [
            {'title': 'Microsoft 365', 'chapters': [
                {'title': 'Teams et SharePoint', 'lessons': [
                    {'title': 'Organiser ses équipes dans Teams', 'content_type': 'video', 'duration_seconds': 780, 'is_preview_free': True},
                    {'title': 'Partager et co-éditer avec SharePoint', 'content_type': 'video', 'duration_seconds': 720},
                    {'title': 'Automatiser avec Power Automate', 'content_type': 'video', 'duration_seconds': 900},
                ]},
            ]},
            {'title': 'Google Workspace', 'chapters': [
                {'title': 'Drive, Docs et Meet', 'lessons': [
                    {'title': 'Organisation de Drive et partage', 'content_type': 'video', 'duration_seconds': 660},
                    {'title': 'Collaboration en temps réel sur Docs', 'content_type': 'video', 'duration_seconds': 720},
                    {'title': 'Réunions efficaces avec Google Meet', 'content_type': 'video', 'duration_seconds': 600},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Outils Collaboratifs',
            'questions': [
                {
                    'text': 'Quel outil Microsoft permet d\'automatiser des flux de travail sans coder ?',
                    'choices': [
                        {'text': 'Power Automate', 'is_correct': True},
                        {'text': 'Power BI', 'is_correct': False},
                        {'text': 'SharePoint Designer', 'is_correct': False},
                        {'text': 'Teams Workflow', 'is_correct': False},
                    ],
                    'explanation': 'Power Automate (anciennement Flow) permet de créer des workflows automatisés sans programmation.',
                },
            ],
        },
    },
    {
        'title': 'Gestion de Données avec Excel & Power BI',
        'subtitle': 'Analyse de données, visualisation et tableaux de bord décisionnels',
        'description': (
            'Transformez vos données en insights actionnables : nettoyage et modélisation '
            'des données avec Excel, création de tableaux de bord interactifs avec Power BI, '
            'DAX de base et publication de rapports.'
        ),
        'category': 'Informatique & Technologie',
        'level': 'intermediate',
        'price': 55000,
        'sections': [
            {'title': 'Préparation des données', 'chapters': [
                {'title': 'Power Query et nettoyage', 'lessons': [
                    {'title': 'Importer et transformer les données', 'content_type': 'video', 'duration_seconds': 960, 'is_preview_free': True},
                    {'title': 'Nettoyage et standardisation', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Fusion et ajout de tables', 'content_type': 'video', 'duration_seconds': 900},
                ]},
            ]},
            {'title': 'Tableaux de bord Power BI', 'chapters': [
                {'title': 'Visualisations et DAX', 'lessons': [
                    {'title': 'Créer des visuels percutants', 'content_type': 'video', 'duration_seconds': 1020},
                    {'title': 'Mesures DAX essentielles', 'content_type': 'video', 'duration_seconds': 1080},
                    {'title': 'Publier et partager un rapport', 'content_type': 'video', 'duration_seconds': 720},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Power BI',
            'questions': [
                {
                    'text': 'Dans Power BI, DAX signifie :',
                    'choices': [
                        {'text': 'Data Analysis Expressions', 'is_correct': True},
                        {'text': 'Data Aggregation eXtension', 'is_correct': False},
                        {'text': 'Dynamic Analysis X-tool', 'is_correct': False},
                        {'text': 'Database Access eXchange', 'is_correct': False},
                    ],
                    'explanation': 'DAX (Data Analysis Expressions) est le langage de formule utilisé dans Power BI.',
                },
            ],
        },
    },

    # ── Business Communication ──────────────────────────────────────────────────
    {
        'title': 'Communication Professionnelle et Assertivité',
        'subtitle': 'Prendre la parole, convaincre et gérer les conflits au travail',
        'description': (
            'Développez vos compétences en communication professionnelle : assertivité, '
            'écoute active, gestion des conflits, feedback constructif et '
            'communication en situation de stress ou de crise.'
        ),
        'category': 'Management',
        'level': 'beginner',
        'price': 39000,
        'is_free': False,
        'sections': [
            {'title': 'Bases de la communication', 'chapters': [
                {'title': 'Assertivité et écoute', 'lessons': [
                    {'title': 'Les 4 styles de communication', 'content_type': 'video', 'duration_seconds': 840, 'is_preview_free': True},
                    {'title': 'Développer son assertivité', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Écoute active et empathie', 'content_type': 'video', 'duration_seconds': 720},
                ]},
            ]},
            {'title': 'Situations difficiles', 'chapters': [
                {'title': 'Conflits et feedback', 'lessons': [
                    {'title': 'Désamorcer les conflits professionnels', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Donner et recevoir un feedback', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Communiquer sous pression', 'content_type': 'video', 'duration_seconds': 720},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Communication Professionnelle',
            'questions': [
                {
                    'text': 'La communication assertive se caractérise par :',
                    'choices': [
                        {'text': 'Exprimer ses besoins clairement en respectant ceux des autres', 'is_correct': True},
                        {'text': 'Imposer ses idées sans tenir compte des autres', 'is_correct': False},
                        {'text': 'Éviter tout conflit en cédant systématiquement', 'is_correct': False},
                        {'text': 'Attaquer verbalement son interlocuteur', 'is_correct': False},
                    ],
                    'explanation': 'L\'assertivité est la capacité à s\'exprimer fermement tout en respectant l\'interlocuteur.',
                },
            ],
        },
    },
    {
        'title': 'Prise de Parole en Public et Présentation',
        'subtitle': 'Techniques d\'orateurs, storytelling et gestion du stress scénique',
        'description': (
            'Devenez un orateur confiant : structure de présentation, storytelling, '
            'gestion du trac, techniques de voix et de posture, '
            'animation d\'ateliers et soutenance devant jury.'
        ),
        'category': 'Leadership',
        'level': 'intermediate',
        'price': 45000,
        'sections': [
            {'title': 'Art de la présentation', 'chapters': [
                {'title': 'Structure et storytelling', 'lessons': [
                    {'title': 'Structurer un discours percutant', 'content_type': 'video', 'duration_seconds': 840, 'is_preview_free': True},
                    {'title': 'Le storytelling au service de la présentation', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Supports visuels et slides efficaces', 'content_type': 'video', 'duration_seconds': 780},
                ]},
            ]},
            {'title': 'Confiance et impact', 'chapters': [
                {'title': 'Voix, posture et gestion du trac', 'lessons': [
                    {'title': 'Maîtriser sa voix et son souffle', 'content_type': 'video', 'duration_seconds': 720},
                    {'title': 'Posture et langage corporel', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Techniques pour vaincre le trac', 'content_type': 'video', 'duration_seconds': 840},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Prise de Parole',
            'questions': [
                {
                    'text': 'La règle du "3×3" dans une présentation consiste à :',
                    'choices': [
                        {'text': 'Organiser le contenu en 3 parties avec 3 idées chacune', 'is_correct': True},
                        {'text': 'Parler 3 minutes maximum avec 3 slides', 'is_correct': False},
                        {'text': 'Répéter 3 fois chaque point clé', 'is_correct': False},
                        {'text': 'Utiliser 3 couleurs et 3 polices différentes', 'is_correct': False},
                    ],
                    'explanation': 'La règle "3×3" aide à structurer clairement : 3 parties principales avec 3 arguments chacune.',
                },
            ],
        },
    },

    # ── Project Management ──────────────────────────────────────────────────────
    {
        'title': 'Méthodes Agiles — Scrum et Kanban',
        'subtitle': 'Sprints, backlogs, daily stand-ups et livraison continue',
        'description': (
            'Adoptez les méthodes agiles pour vos projets : rôles Scrum (Product Owner, '
            'Scrum Master, Équipe), ceremonies, backlog produit, gestion du Kanban, '
            'vélocité et amélioration continue.'
        ),
        'category': 'Management',
        'level': 'intermediate',
        'price': 49000,
        'sections': [
            {'title': 'Scrum en pratique', 'chapters': [
                {'title': 'Rôles et ceremonies', 'lessons': [
                    {'title': 'Les 3 rôles du framework Scrum', 'content_type': 'video', 'duration_seconds': 840, 'is_preview_free': True},
                    {'title': 'Sprint Planning et Daily Stand-up', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Sprint Review et Rétrospective', 'content_type': 'video', 'duration_seconds': 720},
                ]},
            ]},
            {'title': 'Kanban et outils', 'chapters': [
                {'title': 'Flux et tableaux visuels', 'lessons': [
                    {'title': 'Principes du Kanban et WIP limits', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Jira, Trello et Azure DevOps', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Métriques agiles : vélocité et burn-down', 'content_type': 'video', 'duration_seconds': 780},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Méthodes Agiles',
            'questions': [
                {
                    'text': 'Dans Scrum, qui est responsable de maximiser la valeur du produit ?',
                    'choices': [
                        {'text': 'Le Product Owner', 'is_correct': True},
                        {'text': 'Le Scrum Master', 'is_correct': False},
                        {'text': 'L\'équipe de développement', 'is_correct': False},
                        {'text': 'Le chef de projet', 'is_correct': False},
                    ],
                    'explanation': 'Le Product Owner est responsable du backlog produit et maximise la valeur livrée.',
                },
            ],
        },
    },
    {
        'title': 'Gestion du Temps et Productivité Personnelle',
        'subtitle': 'GTD, Pomodoro, Deep Work et organisation optimale',
        'description': (
            'Reprenez le contrôle de votre temps : méthode GTD (Getting Things Done), '
            'Pomodoro, Time Blocking, Deep Work, gestion des priorités avec la matrice d\'Eisenhower '
            'et outils numériques de productivité (Notion, Todoist, Obsidian).'
        ),
        'category': 'Management',
        'level': 'beginner',
        'price': 0,
        'is_free': True,
        'sections': [
            {'title': 'Méthodes de productivité', 'chapters': [
                {'title': 'Priorisation et organisation', 'lessons': [
                    {'title': 'Matrice d\'Eisenhower — urgent vs important', 'content_type': 'video', 'duration_seconds': 720, 'is_preview_free': True},
                    {'title': 'La méthode GTD en 5 étapes', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Time Blocking et Deep Work', 'content_type': 'video', 'duration_seconds': 780},
                ]},
            ]},
            {'title': 'Outils numériques', 'chapters': [
                {'title': 'Systèmes et apps', 'lessons': [
                    {'title': 'Notion pour la gestion de projets personnels', 'content_type': 'video', 'duration_seconds': 960},
                    {'title': 'La technique Pomodoro avec un timer', 'content_type': 'video', 'duration_seconds': 600},
                    {'title': 'Inbox Zero — gérer ses emails efficacement', 'content_type': 'video', 'duration_seconds': 720},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Productivité',
            'questions': [
                {
                    'text': 'Dans la matrice d\'Eisenhower, les tâches "importantes mais non urgentes" doivent être :',
                    'choices': [
                        {'text': 'Planifiées (en les faisant soi-même)', 'is_correct': True},
                        {'text': 'Faites immédiatement', 'is_correct': False},
                        {'text': 'Déléguées', 'is_correct': False},
                        {'text': 'Éliminées', 'is_correct': False},
                    ],
                    'explanation': 'Les tâches importantes non urgentes sont à planifier soigneusement pour éviter qu\'elles deviennent urgentes.',
                },
            ],
        },
    },

    # ── Leadership & Management ──────────────────────────────────────────────────
    {
        'title': 'Management Situationnel — Adapter son Style',
        'subtitle': 'Modèle Hersey-Blanchard et leadership adaptatif',
        'description': (
            'Adoptez le management situationnel : identifier le niveau de maturité de vos '
            'collaborateurs, adapter votre style (directif, persuasif, participatif, délégatif), '
            'développer l\'autonomie et accompagner la montée en compétences.'
        ),
        'category': 'Management',
        'level': 'intermediate',
        'price': 55000,
        'sections': [
            {'title': 'Le modèle situationnel', 'chapters': [
                {'title': 'Diagnostic et adaptation', 'lessons': [
                    {'title': 'Les 4 niveaux de maturité des collaborateurs', 'content_type': 'video', 'duration_seconds': 840, 'is_preview_free': True},
                    {'title': 'Style directif : quand et comment l\'utiliser', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Style délégatif et autonomisation', 'content_type': 'video', 'duration_seconds': 720},
                ]},
            ]},
            {'title': 'Application pratique', 'chapters': [
                {'title': 'Entretiens et suivi', 'lessons': [
                    {'title': 'Diagnostiquer le niveau de maturité', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Entretien de développement des compétences', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Pièges et erreurs du management situationnel', 'content_type': 'video', 'duration_seconds': 720},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Management Situationnel',
            'questions': [
                {
                    'text': 'Selon Hersey et Blanchard, combien de styles de leadership le modèle situationnel identifie-t-il ?',
                    'choices': [
                        {'text': '4', 'is_correct': True},
                        {'text': '2', 'is_correct': False},
                        {'text': '6', 'is_correct': False},
                        {'text': '3', 'is_correct': False},
                    ],
                    'explanation': 'Le modèle définit 4 styles : Directif, Persuasif, Participatif et Délégatif.',
                },
            ],
        },
    },
    {
        'title': 'Coaching et Développement des Talents',
        'subtitle': 'Techniques de coaching pour managers et RH',
        'description': (
            'Intégrez le coaching dans votre pratique managériale : modèle GROW, '
            'questions puissantes, feedback de développement, accompagnement des hauts potentiels '
            'et mise en place de plans de développement individuels (PDI).'
        ),
        'category': 'Ressources Humaines',
        'level': 'advanced',
        'price': 69000,
        'sections': [
            {'title': 'Posture du coach-manager', 'chapters': [
                {'title': 'Principes et modèles', 'lessons': [
                    {'title': 'Différence coaching / mentoring / formation', 'content_type': 'video', 'duration_seconds': 780, 'is_preview_free': True},
                    {'title': 'Le modèle GROW en pratique', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'L\'art des questions puissantes', 'content_type': 'video', 'duration_seconds': 840},
                ]},
            ]},
            {'title': 'Plans de développement', 'chapters': [
                {'title': 'Identifier et développer les talents', 'lessons': [
                    {'title': 'Cartographie des compétences', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Créer un Plan de Développement Individuel', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Suivi et mesure des progrès', 'content_type': 'video', 'duration_seconds': 720},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Coaching',
            'questions': [
                {
                    'text': 'Dans le modèle GROW, que signifie la lettre "O" ?',
                    'choices': [
                        {'text': 'Options (solutions possibles)', 'is_correct': True},
                        {'text': 'Objectif (goal)', 'is_correct': False},
                        {'text': 'Obstacles à surmonter', 'is_correct': False},
                        {'text': 'Organisation de la démarche', 'is_correct': False},
                    ],
                    'explanation': 'GROW = Goal (objectif), Reality (réalité), Options (possibilités), Will/Way Forward (engagement).',
                },
            ],
        },
    },
    {
        'title': 'Intelligence Émotionnelle et Bien-être au Travail',
        'subtitle': 'Gérer ses émotions, prévenir le burn-out et créer un environnement positif',
        'description': (
            'Développez votre intelligence émotionnelle (IE) : conscience de soi, '
            'régulation émotionnelle, empathie, gestion du stress, prévention du burn-out '
            'et promotion du bien-être dans son équipe.'
        ),
        'category': 'Leadership',
        'level': 'beginner',
        'price': 35000,
        'sections': [
            {'title': 'Conscience émotionnelle', 'chapters': [
                {'title': 'Comprendre et réguler ses émotions', 'lessons': [
                    {'title': 'Les 4 piliers de l\'IE selon Goleman', 'content_type': 'video', 'duration_seconds': 840, 'is_preview_free': True},
                    {'title': 'Identifier et nommer ses émotions', 'content_type': 'video', 'duration_seconds': 720},
                    {'title': 'Techniques de régulation émotionnelle', 'content_type': 'video', 'duration_seconds': 780},
                ]},
            ]},
            {'title': 'Bien-être au travail', 'chapters': [
                {'title': 'Stress et burn-out', 'lessons': [
                    {'title': 'Reconnaître les signaux d\'alerte du burn-out', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Stratégies de gestion du stress professionnel', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Créer un environnement de travail positif', 'content_type': 'video', 'duration_seconds': 720},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Intelligence Émotionnelle',
            'questions': [
                {
                    'text': 'Quel composant de l\'IE implique la capacité à reconnaître ses propres émotions ?',
                    'choices': [
                        {'text': 'La conscience de soi (self-awareness)', 'is_correct': True},
                        {'text': 'L\'empathie', 'is_correct': False},
                        {'text': 'La maîtrise de soi', 'is_correct': False},
                        {'text': 'Les compétences sociales', 'is_correct': False},
                    ],
                    'explanation': 'La conscience de soi est la capacité à identifier et comprendre ses propres émotions.',
                },
            ],
        },
    },

    # ── Finance & Accounting ────────────────────────────────────────────────────
    {
        'title': 'Finance pour Non-Financiers',
        'subtitle': 'Comprendre les états financiers et raisonner en termes financiers',
        'description': (
            'Cours conçu pour les managers et responsables opérationnels : '
            'lecture d\'un bilan, d\'un compte de résultat, compréhension du budget, '
            'indicateurs financiers essentiels et dialogue avec la direction financière.'
        ),
        'category': 'Finance',
        'level': 'beginner',
        'price': 45000,
        'sections': [
            {'title': 'Lire les chiffres', 'chapters': [
                {'title': 'États financiers simplifiés', 'lessons': [
                    {'title': 'Décrypter un bilan en 30 minutes', 'content_type': 'video', 'duration_seconds': 900, 'is_preview_free': True},
                    {'title': 'Lire un compte de résultat', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'KPIs financiers essentiels pour managers', 'content_type': 'video', 'duration_seconds': 780},
                ]},
            ]},
            {'title': 'Budget et pilotage', 'chapters': [
                {'title': 'Participer au processus budgétaire', 'lessons': [
                    {'title': 'Comprendre le budget de son département', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Analyser les écarts et expliquer les résultats', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Préparer un business case simple', 'content_type': 'video', 'duration_seconds': 780},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Finance pour Managers',
            'questions': [
                {
                    'text': 'La marge brute est calculée comme :',
                    'choices': [
                        {'text': 'Chiffre d\'affaires - Coût des ventes', 'is_correct': True},
                        {'text': 'Chiffre d\'affaires - Charges totales', 'is_correct': False},
                        {'text': 'Bénéfice net + Amortissements', 'is_correct': False},
                        {'text': 'Actif courant - Passif courant', 'is_correct': False},
                    ],
                    'explanation': 'La marge brute mesure la rentabilité avant les frais généraux et opérationnels.',
                },
            ],
        },
    },
    {
        'title': 'Élaboration et Suivi du Budget d\'Entreprise',
        'subtitle': 'Processus budgétaire, prévisions et gestion des écarts',
        'description': (
            'Maîtrisez le cycle budgétaire complet : construction du budget annuel, '
            'prévisions glissantes, analyse des écarts mensuels, reforecast '
            'et reporting financier pour la direction.'
        ),
        'category': 'Finance',
        'level': 'intermediate',
        'price': 59000,
        'sections': [
            {'title': 'Construction budgétaire', 'chapters': [
                {'title': 'Du budget au forecast', 'lessons': [
                    {'title': 'Calendrier et processus budgétaire', 'content_type': 'video', 'duration_seconds': 840, 'is_preview_free': True},
                    {'title': 'Méthodes de budgétisation (base zéro, incrémental)', 'content_type': 'video', 'duration_seconds': 960},
                    {'title': 'Construire le budget des ventes', 'content_type': 'video', 'duration_seconds': 900},
                ]},
            ]},
            {'title': 'Suivi et reporting', 'chapters': [
                {'title': 'Contrôle budgétaire', 'lessons': [
                    {'title': 'Tableaux de bord budget vs réel', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Analyser et expliquer les écarts significatifs', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Reforecast trimestriel et ajustements', 'content_type': 'video', 'duration_seconds': 780},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Budget d\'Entreprise',
            'questions': [
                {
                    'text': 'Le "budget base zéro" (BBZ) consiste à :',
                    'choices': [
                        {'text': 'Repartir de zéro et justifier chaque dépense', 'is_correct': True},
                        {'text': 'Réduire le budget à zéro sur certains postes', 'is_correct': False},
                        {'text': 'Utiliser l\'année précédente comme base sans ajustement', 'is_correct': False},
                        {'text': 'Fixer le budget à zéro pour les frais fixes', 'is_correct': False},
                    ],
                    'explanation': 'Le BBZ repart de zéro et oblige chaque service à justifier chaque dépense, sans tenir compte du passé.',
                },
            ],
        },
    },

    # ── Data & Analytics ────────────────────────────────────────────────────────
    {
        'title': 'Introduction à la Data Science',
        'subtitle': 'Python, pandas et premiers modèles de machine learning',
        'description': (
            'Découvrez la data science avec Python : manipulation de données avec pandas, '
            'visualisation avec matplotlib et seaborn, statistiques descriptives '
            'et votre premier modèle prédictif avec scikit-learn.'
        ),
        'category': 'IA & Intelligence Artificielle',
        'level': 'intermediate',
        'price': 65000,
        'sections': [
            {'title': 'Python pour la Data', 'chapters': [
                {'title': 'Pandas et numpy', 'lessons': [
                    {'title': 'Charger et explorer un jeu de données', 'content_type': 'video', 'duration_seconds': 960, 'is_preview_free': True},
                    {'title': 'Nettoyage et transformation avec pandas', 'content_type': 'video', 'duration_seconds': 1020},
                    {'title': 'Visualisation avec matplotlib et seaborn', 'content_type': 'video', 'duration_seconds': 900},
                ]},
            ]},
            {'title': 'Premier modèle ML', 'chapters': [
                {'title': 'Régression et classification', 'lessons': [
                    {'title': 'Régression linéaire avec scikit-learn', 'content_type': 'video', 'duration_seconds': 1080},
                    {'title': 'Évaluer son modèle : métriques et overfitting', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Présenter ses résultats à des non-techniciens', 'content_type': 'video', 'duration_seconds': 720},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Data Science',
            'questions': [
                {
                    'text': 'En Python, quelle bibliothèque est principalement utilisée pour la manipulation de données tabulaires ?',
                    'choices': [
                        {'text': 'pandas', 'is_correct': True},
                        {'text': 'numpy', 'is_correct': False},
                        {'text': 'matplotlib', 'is_correct': False},
                        {'text': 'scipy', 'is_correct': False},
                    ],
                    'explanation': 'pandas est la bibliothèque standard pour les DataFrames et la manipulation de données tabulaires.',
                },
            ],
        },
    },
    {
        'title': 'Analyse des Données RH — People Analytics',
        'subtitle': 'Tableaux de bord RH, prédiction du turnover et mesure de l\'engagement',
        'description': (
            'Exploitez les données RH pour prendre de meilleures décisions : '
            'KPIs RH (absentéisme, turnover, performance), construction de tableaux de bord '
            'sous Excel et Power BI, modèles prédictifs d\'attrition et mesure de l\'engagement.'
        ),
        'category': 'Ressources Humaines',
        'level': 'intermediate',
        'price': 55000,
        'sections': [
            {'title': 'Métriques RH essentielles', 'chapters': [
                {'title': 'KPIs et dashboards', 'lessons': [
                    {'title': 'Les 10 indicateurs RH incontournables', 'content_type': 'video', 'duration_seconds': 900, 'is_preview_free': True},
                    {'title': 'Construire un dashboard RH sous Excel', 'content_type': 'video', 'duration_seconds': 1020},
                    {'title': 'Analyser le turnover et ses causes', 'content_type': 'video', 'duration_seconds': 840},
                ]},
            ]},
            {'title': 'Analytique avancée', 'chapters': [
                {'title': 'Prédire et prévenir', 'lessons': [
                    {'title': 'Modèle de prédiction du départ volontaire', 'content_type': 'video', 'duration_seconds': 960},
                    {'title': 'Mesurer et améliorer l\'engagement', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Présenter les insights RH à la direction', 'content_type': 'video', 'duration_seconds': 780},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — People Analytics',
            'questions': [
                {
                    'text': 'Le taux de turnover annuel se calcule comme :',
                    'choices': [
                        {'text': '(Départs / Effectif moyen) × 100', 'is_correct': True},
                        {'text': '(Recrutements / Effectif total) × 100', 'is_correct': False},
                        {'text': '(Absences / Jours travaillés) × 100', 'is_correct': False},
                        {'text': '(Promotions / Effectif) × 100', 'is_correct': False},
                    ],
                    'explanation': 'Le turnover mesure le taux de rotation du personnel sur une période donnée.',
                },
            ],
        },
    },

    # ── Entrepreneurship ────────────────────────────────────────────────────────
    {
        'title': 'Entrepreneuriat et Création d\'Entreprise en Afrique',
        'subtitle': 'Business plan, financement, formalités et développement commercial',
        'description': (
            'Lancez votre entreprise en Afrique de l\'Ouest : étude de marché, '
            'business model canvas, business plan financier, formalités RCCM/OHADA, '
            'sources de financement (BCEAO, fonds d\'investissement, microfinance) '
            'et premières ventes.'
        ),
        'category': 'Management',
        'level': 'beginner',
        'price': 49000,
        'sections': [
            {'title': 'Construire son projet', 'chapters': [
                {'title': 'Idée et validation', 'lessons': [
                    {'title': 'Identifier une opportunité de marché', 'content_type': 'video', 'duration_seconds': 840, 'is_preview_free': True},
                    {'title': 'Business Model Canvas en pratique', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Valider son idée à moindre coût (MVP)', 'content_type': 'video', 'duration_seconds': 780},
                ]},
            ]},
            {'title': 'Lancer et financer', 'chapters': [
                {'title': 'Financement et formalités', 'lessons': [
                    {'title': 'Formalités RCCM et statuts juridiques OHADA', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Sources de financement en Afrique de l\'Ouest', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Construire ses premières ventes', 'content_type': 'video', 'duration_seconds': 840},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Entrepreneuriat',
            'questions': [
                {
                    'text': 'Le Business Model Canvas est un outil permettant de :',
                    'choices': [
                        {'text': 'Visualiser et décrire le modèle économique d\'une entreprise en 9 blocs', 'is_correct': True},
                        {'text': 'Calculer la rentabilité d\'un projet', 'is_correct': False},
                        {'text': 'Établir un organigramme d\'entreprise', 'is_correct': False},
                        {'text': 'Créer un plan marketing détaillé', 'is_correct': False},
                    ],
                    'explanation': 'Le BMC (Osterwalder) décrit le modèle en 9 blocs : segments, proposition de valeur, canaux, etc.',
                },
            ],
        },
    },
    {
        'title': 'Commerce et Négociation B2B',
        'subtitle': 'Prospection, qualification des leads et closing commercial',
        'description': (
            'Développez vos compétences commerciales B2B : prospection téléphonique et LinkedIn, '
            'qualification BANT, technique de présentation SPIN Selling, '
            'gestion des objections, négociation et closing. '
            'Applicable au secteur de la formation professionnelle.'
        ),
        'category': 'Marketing',
        'level': 'intermediate',
        'price': 55000,
        'sections': [
            {'title': 'Prospection et qualification', 'chapters': [
                {'title': 'Trouver et qualifier les prospects', 'lessons': [
                    {'title': 'Définir son ICP (Ideal Customer Profile)', 'content_type': 'video', 'duration_seconds': 780, 'is_preview_free': True},
                    {'title': 'Prospection LinkedIn et cold outreach', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Qualifier avec la méthode BANT', 'content_type': 'video', 'duration_seconds': 720},
                ]},
            ]},
            {'title': 'Vente et négociation', 'chapters': [
                {'title': 'Convaincre et closer', 'lessons': [
                    {'title': 'SPIN Selling — les 4 types de questions', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Traiter les objections avec confiance', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Techniques de closing et suivi post-vente', 'content_type': 'video', 'duration_seconds': 840},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Commerce B2B',
            'questions': [
                {
                    'text': 'Dans la méthode BANT, que signifie le "A" ?',
                    'choices': [
                        {'text': 'Authority (pouvoir de décision)', 'is_correct': True},
                        {'text': 'Amount (montant du budget)', 'is_correct': False},
                        {'text': 'Awareness (sensibilisation)', 'is_correct': False},
                        {'text': 'Acquisition (acquisition client)', 'is_correct': False},
                    ],
                    'explanation': 'BANT = Budget, Authority (décideur), Need (besoin), Timeline (calendrier).',
                },
            ],
        },
    },

    # ── Soft Skills ─────────────────────────────────────────────────────────────
    {
        'title': 'Pensée Critique et Résolution de Problèmes',
        'subtitle': 'Méthodes structurées d\'analyse et de prise de décision',
        'description': (
            'Renforcez votre capacité à analyser et résoudre les problèmes complexes : '
            'méthode des 5 Pourquoi, diagramme d\'Ishikawa, arbre des causes, '
            'Design Thinking, Six Sigma DMAIC et décision en situation d\'incertitude.'
        ),
        'category': 'Leadership',
        'level': 'intermediate',
        'price': 39000,
        'sections': [
            {'title': 'Outils d\'analyse', 'chapters': [
                {'title': 'Identifier les causes racines', 'lessons': [
                    {'title': 'Les 5 Pourquoi — trouver la cause profonde', 'content_type': 'video', 'duration_seconds': 720, 'is_preview_free': True},
                    {'title': 'Diagramme d\'Ishikawa (arête de poisson)', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Analyse SWOT et PESTEL', 'content_type': 'video', 'duration_seconds': 840},
                ]},
            ]},
            {'title': 'Décision et créativité', 'chapters': [
                {'title': 'Solutions et choix', 'lessons': [
                    {'title': 'Brainstorming structuré et mind mapping', 'content_type': 'video', 'duration_seconds': 720},
                    {'title': 'Matrice de décision multicritères', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Décision sous contrainte de temps', 'content_type': 'video', 'duration_seconds': 660},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Pensée Critique',
            'questions': [
                {
                    'text': 'La méthode des "5 Pourquoi" est utilisée pour :',
                    'choices': [
                        {'text': 'Identifier la cause racine d\'un problème', 'is_correct': True},
                        {'text': 'Lister 5 solutions possibles', 'is_correct': False},
                        {'text': 'Évaluer 5 critères de décision', 'is_correct': False},
                        {'text': 'Structurer une présentation en 5 parties', 'is_correct': False},
                    ],
                    'explanation': 'Les "5 Pourquoi" permettent de remonter aux causes profondes en questionnant chaque réponse.',
                },
            ],
        },
    },
    {
        'title': 'Travail en Équipe et Dynamiques de Groupe',
        'subtitle': 'Cohésion, rôles, réunions efficaces et prise de décision collective',
        'description': (
            'Optimisez la performance collective : modèle de Tuckman '
            '(forming, storming, norming, performing), rôles de Belbin, '
            'facilitation de réunions, intelligence collective '
            'et gestion des personnalités difficiles en équipe.'
        ),
        'category': 'Management',
        'level': 'beginner',
        'price': 35000,
        'sections': [
            {'title': 'Dynamiques d\'équipe', 'chapters': [
                {'title': 'Formation et cohésion', 'lessons': [
                    {'title': 'Les 4 stades de Tuckman', 'content_type': 'video', 'duration_seconds': 780, 'is_preview_free': True},
                    {'title': 'Les rôles de Belbin dans une équipe', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Créer la cohésion et la confiance', 'content_type': 'video', 'duration_seconds': 720},
                ]},
            ]},
            {'title': 'Réunions et décisions', 'chapters': [
                {'title': 'Efficacité collective', 'lessons': [
                    {'title': 'Préparer et animer une réunion efficace', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Prise de décision en groupe', 'content_type': 'video', 'duration_seconds': 720},
                    {'title': 'Gérer les personnalités difficiles', 'content_type': 'video', 'duration_seconds': 780},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Travail en Équipe',
            'questions': [
                {
                    'text': 'Dans le modèle de Tuckman, quelle est la phase où l\'équipe est la plus productive ?',
                    'choices': [
                        {'text': 'Performing (performance)', 'is_correct': True},
                        {'text': 'Storming (confrontation)', 'is_correct': False},
                        {'text': 'Norming (normalisation)', 'is_correct': False},
                        {'text': 'Forming (formation)', 'is_correct': False},
                    ],
                    'explanation': 'La phase "Performing" est celle où l\'équipe est cohérente, autonome et productive.',
                },
            ],
        },
    },
    {
        'title': 'Ingénierie Pédagogique et Conception de Formations',
        'subtitle': 'Concevoir des formations efficaces : ADDIE, objectifs et évaluation',
        'description': (
            'Maîtrisez l\'ingénierie pédagogique pour créer des formations impactantes : '
            'analyse des besoins, objectifs pédagogiques (Bloom), modèle ADDIE, '
            'techniques d\'animation, e-learning et évaluation de l\'impact formation (Kirkpatrick).'
        ),
        'category': 'Ressources Humaines',
        'level': 'intermediate',
        'price': 59000,
        'sections': [
            {'title': 'Conception pédagogique', 'chapters': [
                {'title': 'Analyse et objectifs', 'lessons': [
                    {'title': 'Analyser les besoins en formation (AFEST)', 'content_type': 'video', 'duration_seconds': 900, 'is_preview_free': True},
                    {'title': 'Rédiger des objectifs pédagogiques (Bloom)', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Le modèle ADDIE étape par étape', 'content_type': 'video', 'duration_seconds': 960},
                ]},
            ]},
            {'title': 'Animation et évaluation', 'chapters': [
                {'title': 'Délivrer et mesurer', 'lessons': [
                    {'title': 'Techniques d\'animation participative', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Concevoir des évaluations formatives et sommatives', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Modèle Kirkpatrick — mesurer l\'impact formation', 'content_type': 'video', 'duration_seconds': 900},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Ingénierie Pédagogique',
            'questions': [
                {
                    'text': 'Le modèle ADDIE en ingénierie pédagogique correspond à :',
                    'choices': [
                        {'text': 'Analysis, Design, Development, Implementation, Evaluation', 'is_correct': True},
                        {'text': 'Assessment, Delivery, Design, Implementation, Evaluation', 'is_correct': False},
                        {'text': 'Analysis, Development, Delivery, Integration, Evaluation', 'is_correct': False},
                        {'text': 'Alignment, Design, Development, Instruction, Execution', 'is_correct': False},
                    ],
                    'explanation': 'ADDIE est le modèle classique de conception pédagogique en 5 phases.',
                },
            ],
        },
    },
    {
        'title': 'Cybersécurité pour les Centres de Formation',
        'subtitle': 'Protéger les données des apprenants et sécuriser la plateforme LMS',
        'description': (
            'Formation spécialisée pour les gestionnaires de centres de formation : '
            'conformité RGPD pour les données des apprenants, sécurisation de la plateforme e-learning, '
            'bonnes pratiques pour le personnel administratif et procédures en cas d\'incident.'
        ),
        'category': 'Cybersécurité',
        'level': 'beginner',
        'price': 39000,
        'sections': [
            {'title': 'RGPD et données apprenants', 'chapters': [
                {'title': 'Conformité et protection', 'lessons': [
                    {'title': 'RGPD et données personnelles des apprenants', 'content_type': 'video', 'duration_seconds': 840, 'is_preview_free': True},
                    {'title': 'Droits des apprenants et obligations du centre', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Registre des traitements et DPO', 'content_type': 'video', 'duration_seconds': 720},
                ]},
            ]},
            {'title': 'Sécurité opérationnelle', 'chapters': [
                {'title': 'Pratiques et incidents', 'lessons': [
                    {'title': 'Sécuriser l\'accès à la plateforme LMS', 'content_type': 'video', 'duration_seconds': 720},
                    {'title': 'Sauvegardes et plan de reprise d\'activité', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Procédure en cas de violation de données', 'content_type': 'video', 'duration_seconds': 720},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Cybersécurité Formation',
            'questions': [
                {
                    'text': 'Sous le RGPD, un centre de formation est généralement considéré comme :',
                    'choices': [
                        {'text': 'Responsable de traitement des données personnelles', 'is_correct': True},
                        {'text': 'Sous-traitant des données', 'is_correct': False},
                        {'text': 'Simple hébergeur de données', 'is_correct': False},
                        {'text': 'Exempt des obligations RGPD', 'is_correct': False},
                    ],
                    'explanation': 'Le centre de formation détermine les finalités du traitement des données des apprenants, donc il est responsable de traitement.',
                },
            ],
        },
    },
]


class Command(BaseCommand):
    help = 'Seed 20 courses for Tech Innovation Center (training center admin as instructor)'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete TC courses then re-create')

    def log(self, msg):
        self.stdout.write(msg)

    def ok(self, msg):
        self.stdout.write(self.style.SUCCESS(f'  [+] {msg}'))

    def skip(self, msg):
        self.stdout.write(f'  [=] {msg}')

    def warn(self, msg):
        self.stdout.write(self.style.WARNING(f'  [!] {msg}'))

    def handle(self, *args, **options):
        from apps.accounts.models import User
        from apps.catalog.models import Category
        from apps.courses.models import Course, CourseSection, Chapter, Lesson
        from apps.tenants.models import Company
        from apps.assessments.models import (
            QuestionBank, Question, QuestionChoice, Assessment, AssessmentQuestion,
        )

        reset = options['reset']

        # ── Resolve training center and its admin ─────────────────────────────
        tc = Company.objects.filter(slug='tech-innovation-center').first()
        if not tc:
            self.warn('Tech Innovation Center not found — run seed_demo first!')
            return

        tc_admin = User.objects.filter(email='training_center_admin@lmspro.com').first()
        if not tc_admin:
            self.warn('training_center_admin not found — run seed_demo first!')
            return

        if reset:
            count, _ = Course.objects.filter(company=tc).delete()
            if count:
                self.warn(f'Deleted {count} TC courses')

        with transaction.atomic():
            # ── Categories (shared with B2C or created if missing) ────────────
            self.log('\n[1] Categories...')
            tc_cat_names = {cd['category'] for cd in TC_COURSES}
            cat_objects = {}
            CAT_ICONS = {
                'Informatique & Technologie': 'Monitor',
                'Management': 'Briefcase',
                'Leadership': 'Zap',
                'Finance': 'BarChart2',
                'IA & Intelligence Artificielle': 'Brain',
                'Cybersécurité': 'Shield',
                'Ressources Humaines': 'UserCheck',
                'Marketing': 'Megaphone',
                'Langues Étrangères': 'Globe',
            }
            for cat_name in tc_cat_names:
                obj, created = Category.objects.get_or_create(
                    name=cat_name,
                    defaults={'icon': CAT_ICONS.get(cat_name, 'BookOpen'), 'is_active': True},
                )
                cat_objects[cat_name] = obj
                action = 'Created' if created else 'Exists'
                self.log(f'  [{action}] {obj.name}')

            # ── Courses ───────────────────────────────────────────────────────
            self.log('\n[2] Courses (Tech Innovation Center)...')
            course_count = 0

            for cd in TC_COURSES:
                cat = cat_objects.get(cd['category'])
                course, created = Course.objects.get_or_create(
                    title=cd['title'],
                    company=tc,
                    defaults={
                        'is_company_internal': True,
                        'category': cat,
                        'instructor': tc_admin,
                        'subtitle': cd.get('subtitle', ''),
                        'description': cd.get('description', ''),
                        'level': cd.get('level', 'all_levels'),
                        'price': cd.get('price', 0),
                        'is_free': cd.get('is_free', cd.get('price', 1) == 0),
                        'status': 'published',
                        'certificate_enabled': True,
                        'published_at': _past(random.randint(5, 45)),
                    },
                )
                if created:
                    self.ok(f'Course: {course.title}')
                    course_count += 1
                else:
                    self.skip(f'Course: {course.title}')

                # Sections → Chapters → Lessons
                for s_idx, section_data in enumerate(cd.get('sections', [])):
                    section, _ = CourseSection.objects.get_or_create(
                        course=course, title=section_data['title'],
                        defaults={'order': s_idx},
                    )
                    for c_idx, chapter_data in enumerate(section_data.get('chapters', [])):
                        chapter, _ = Chapter.objects.get_or_create(
                            section=section, title=chapter_data['title'],
                            defaults={'order': c_idx},
                        )
                        for l_idx, lesson_data in enumerate(chapter_data.get('lessons', [])):
                            content_type = lesson_data.get('content_type', 'video')
                            embed_url = _yt('dQw4w9WgXcQ') if content_type == 'video' else ''
                            lesson, l_created = Lesson.objects.get_or_create(
                                chapter=chapter, title=lesson_data['title'],
                                defaults={
                                    'order': l_idx,
                                    'content_type': content_type,
                                    'duration_seconds': lesson_data.get('duration_seconds', 600),
                                    'is_preview_free': lesson_data.get('is_preview_free', False),
                                    'text_content': (
                                        f'Contenu de la leçon : {lesson_data["title"]}.\n\n'
                                        'Ce contenu pédagogique couvre les concepts essentiels '
                                        'abordés dans cette leçon avec des exemples pratiques.'
                                    ) if content_type == 'text' else '',
                                    'external_embed_url': embed_url,
                                },
                            )

                # Question Bank + Quiz
                quiz_data = cd.get('quiz')
                if quiz_data:
                    bank, _ = QuestionBank.objects.get_or_create(
                        title=quiz_data['title'],
                        defaults={'company': tc, 'created_by': tc_admin},
                    )
                    for q_idx, qd in enumerate(quiz_data.get('questions', [])):
                        question, _ = Question.objects.get_or_create(
                            bank=bank, text=qd['text'],
                            defaults={
                                'question_type': 'mcq',
                                'points': 1,
                                'explanation': qd.get('explanation', ''),
                                'difficulty': 'medium',
                            },
                        )
                        for ch_idx, choice in enumerate(qd.get('choices', [])):
                            QuestionChoice.objects.get_or_create(
                                question=question, text=choice['text'],
                                defaults={'is_correct': choice['is_correct'], 'order': ch_idx},
                            )

                    assessment, _ = Assessment.objects.get_or_create(
                        course=course, title=quiz_data['title'],
                        defaults={
                            'assessment_type': 'quiz',
                            'instructions': 'Répondez à chaque question avec soin.',
                            'time_limit_minutes': 20,
                            'max_attempts': 3,
                            'passing_score': 70,
                            'is_randomized': False,
                            'question_bank': bank,
                            'is_published': True,
                        },
                    )
                    for q_idx, q in enumerate(bank.questions.all()):
                        AssessmentQuestion.objects.get_or_create(
                            assessment=assessment, question=q,
                            defaults={'order': q_idx},
                        )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('  seed_tc_courses completed!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'  New TC courses created : {course_count}')
        self.stdout.write(f'  Total TC courses       : {Course.objects.filter(company=tc).count()}')
        self.stdout.write(self.style.SUCCESS('=' * 60))
