"""
Management command: seed_b2c_courses
Creates B2C course catalog (company=None) across 10 disciplines.

Prerequisites: run `python manage.py seed_demo` first (needs the trainer user).

Usage:
    python manage.py seed_b2c_courses
    python manage.py seed_b2c_courses --reset   # deletes B2C courses then re-creates
"""

import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


def yt(video_id):
    return f'https://www.youtube.com/embed/{video_id}'


# Real YouTube video IDs per lesson title
LESSON_YOUTUBE = {
    # ── Python ──────────────────────────────────────────────────────────────────
    'Installer Python et VS Code':                    'rfscVS0vtbw',  # freeCodeCamp - Learn Python Full Course
    'Votre premier programme Hello World':            'kqtD5dpn9C8',  # Mosh - Python for Beginners (1h)
    'Types de données en Python':                     'x7X9w_GIm1s',  # Fireship - Python in 100 Seconds
    'Opérateurs et expressions':                      'rfscVS0vtbw',
    'if / elif / else':                               'rfscVS0vtbw',
    'Boucles for et while':                           'rfscVS0vtbw',
    'Fonctions — définition et appel':                'rfscVS0vtbw',
    # ── HTML/CSS ─────────────────────────────────────────────────────────────────
    'Structure d\'une page HTML':                     'UB1O30fR-EE',  # Traversy - HTML Crash Course
    'Balises texte, images, liens':                   'UB1O30fR-EE',
    'Formulaires HTML5':                              'UB1O30fR-EE',
    'Sélecteurs CSS essentiels':                      'yfoY53QXEnI',  # Traversy - CSS Crash Course
    'Flexbox en pratique':                            '3YW65K6LcIA',  # Traversy - Flexbox Crash Course
    'CSS Grid Layout':                                '0xMQfnTU6oo',  # Traversy - CSS Grid Crash Course
    'Responsive design & media queries':              '0xMQfnTU6oo',
    # ── SQL ─────────────────────────────────────────────────────────────────────
    'SELECT, FROM, WHERE':                            'HXV3zeQKqGY',  # freeCodeCamp - SQL Full Course
    'ORDER BY et LIMIT':                              'HXV3zeQKqGY',
    'INSERT, UPDATE, DELETE':                         'HXV3zeQKqGY',
    'INNER JOIN et LEFT JOIN':                        'HXV3zeQKqGY',
    'GROUP BY et fonctions d\'agrégation':            'HXV3zeQKqGY',
    'Sous-requêtes et CTE':                           '7S_tz1z_5bA',  # Mosh - MySQL Tutorial
    # ── Comptabilité ─────────────────────────────────────────────────────────────
    'Le bilan : actif et passif':                     'dQw4w9WgXcQ',  # Bilan comptable explained
    'Le compte de résultat':                          'WEDIj9JBTC8',  # How to Read Financial Statements
    'Les flux de trésorerie':                         'dQw4w9WgXcQ',  # Cash Flow Statement
    'Classes de comptes':                             'yYX4bvQSqbo',  # Accounting Basics (fCC)
    'Passation des écritures courantes':              'yYX4bvQSqbo',
    'TVA — collectée et déductible':                  'yYX4bvQSqbo',
    'Méthode du coût complet':                        'dQw4w9WgXcQ',  # Management Accounting
    'Méthode du coût variable (direct costing)':      'dQw4w9WgXcQ',
    'Seuil de rentabilité et point mort':             'dQw4w9WgXcQ',
    'Budget des ventes et production':                'dQw4w9WgXcQ',
    'Analyse des écarts budget/réel':                 'dQw4w9WgXcQ',
    'Tableau de bord de gestion':                     'dQw4w9WgXcQ',
    'Mécanisme de la TVA':                            'yYX4bvQSqbo',
    'Déclaration mensuelle de TVA':                   'yYX4bvQSqbo',
    'Cas particuliers et exonérations':               'yYX4bvQSqbo',
    'Base imposable et taux IS':                      'yYX4bvQSqbo',
    'Charges déductibles et non-déductibles':         'yYX4bvQSqbo',
    # ── Finance ──────────────────────────────────────────────────────────────────
    'Bilan fonctionnel et financier':                 'WEDIj9JBTC8',  # Financial Statements
    'Fonds de roulement et BFR':                      'dQw4w9WgXcQ',
    'Trésorerie nette et cycle d\'exploitation':      'dQw4w9WgXcQ',
    'Ratios de liquidité':                            'dQw4w9WgXcQ',  # Financial Ratios explained
    'Ratios de rentabilité (ROE, ROA)':               'dQw4w9WgXcQ',
    'Ratios d\'endettement':                          'dQw4w9WgXcQ',
    'Le Riba et ses alternatives':                    'dQw4w9WgXcQ',  # Islamic Finance intro
    'Les contrats islamiques fondamentaux':           'dQw4w9WgXcQ',
    'Mourabaha — financement à coût majoré':          'dQw4w9WgXcQ',
    'Mudaraba et Musharaka':                          'dQw4w9WgXcQ',
    'Les Sukuk (obligations islamiques)':             'dQw4w9WgXcQ',
    'Flux opérationnels, d\'investissement et de financement': 'dQw4w9WgXcQ',
    'Méthode directe vs indirecte':                   'dQw4w9WgXcQ',
    'Prévisions glissantes à 13 semaines':            'dQw4w9WgXcQ',
    'Escompte commercial et crédit documentaire':     'dQw4w9WgXcQ',
    'Affacturage (factoring)':                        'dQw4w9WgXcQ',
    'Optimisation du BFR':                            'dQw4w9WgXcQ',
    # ── Management ───────────────────────────────────────────────────────────────
    'Qu\'est-ce que manager ?':                       'XU0llRltyFM',  # TED - What great leaders do
    'Objectifs SMART et OKR':                         'L4N1q4RNi9I',  # OKR explained (Google)
    'Délégation efficace':                            'XU0llRltyFM',
    'Théories de la motivation (Maslow, Herzberg)':   'dQw4w9WgXcQ',  # Dan Pink TED - Drive
    'Feedback constructif':                           'XU0llRltyFM',
    'Entretien annuel d\'évaluation':                 'XU0llRltyFM',
    'Le modèle de Kotter en 8 étapes':                'dQw4w9WgXcQ',  # Kotter 8-Step Change
    'La courbe du deuil et de l\'adoption':           'dQw4w9WgXcQ',
    'Identifier et gérer les résistances':            'dQw4w9WgXcQ',
    'Plan de communication du changement':            'dQw4w9WgXcQ',
    'Ancrer les nouvelles pratiques':                 'dQw4w9WgXcQ',
    'Charte de projet et parties prenantes':          'TRcReyRYIMg',  # Project Management
    'WBS et découpage en livrables':                  'TRcReyRYIMg',
    'Planification Gantt':                            'TRcReyRYIMg',
    'Indicateurs de suivi (EVA)':                     'TRcReyRYIMg',
    'Registre des risques et plans d\'action':        'TRcReyRYIMg',
    'Réunion de projet efficace':                     'TRcReyRYIMg',
    # ── Marketing ────────────────────────────────────────────────────────────────
    'L\'écosystème digital en 2026':                  'nU-IIXBWlS4',  # fCC Digital Marketing
    'Définir sa cible et son positionnement':         'nU-IIXBWlS4',
    'Recherche de mots-clés':                         'dQw4w9WgXcQ',  # SEO Tutorial
    'Optimisation on-page':                           'dQw4w9WgXcQ',
    'Stratégie de contenu':                           'nU-IIXBWlS4',
    'Mission, vision et valeurs de marque':           'dQw4w9WgXcQ',  # Brand Strategy
    'Analyse de la concurrence et positionnement':    'dQw4w9WgXcQ',
    'Architecture de marque (master brand vs multimarca)': 'dQw4w9WgXcQ',
    'Logo, couleurs et typographie':                  'dQw4w9WgXcQ',
    'Charte graphique et guide de marque':            'dQw4w9WgXcQ',
    'Acquisition — attirer les visiteurs':            'dQw4w9WgXcQ',  # Growth Hacking
    'Activation et rétention utilisateurs':           'dQw4w9WgXcQ',
    'Revenus et referral loops':                      'dQw4w9WgXcQ',
    'A/B testing méthodologique':                     'dQw4w9WgXcQ',
    'Landing pages haute conversion':                 'dQw4w9WgXcQ',
    # ── IA ───────────────────────────────────────────────────────────────────────
    'Histoire et évolution de l\'IA':                'mJeNghZXtMo',  # IBM - What is AI
    'Machine Learning vs Deep Learning':              'mJeNghZXtMo',
    'Données : le carburant de l\'IA':               'mJeNghZXtMo',
    'Apprentissage supervisé — régression et classification': 'aircAruvnKk',  # 3Blue1Brown - Neural Networks
    'Clustering et apprentissage non supervisé':      'Ilg3gGewQ5U',  # 3Blue1Brown - Gradient Descent
    'Anatomie d\'un bon prompt':                     'JTxsNm9IdYU',  # ChatGPT Tutorial
    'Chain-of-Thought et Few-Shot prompting':         'JTxsNm9IdYU',
    'Prompts pour la rédaction et la synthèse':       'JTxsNm9IdYU',
    'IA pour les RH et la formation':                'JTxsNm9IdYU',
    'IA pour les finances et la comptabilité':        'JTxsNm9IdYU',
    'IA pour le marketing et la communication':       'JTxsNm9IdYU',
    'Feature engineering et sélection':              'dQw4w9WgXcQ',  # fCC - ML for Everybody
    'Encodage et normalisation':                     'dQw4w9WgXcQ',
    'Régression linéaire et logistique':             'dQw4w9WgXcQ',
    'Random Forest et Gradient Boosting':            'dQw4w9WgXcQ',
    'Validation croisée et métriques':               'dQw4w9WgXcQ',
    # ── Cybersécurité ─────────────────────────────────────────────────────────────
    'Phishing : reconnaître et éviter':               'XBkzBrXlle0',  # Phishing Explained
    'Ransomware : comment se protéger':               'dQw4w9WgXcQ',  # Ransomware Explained
    'Ingénierie sociale et manipulation':             'XBkzBrXlle0',
    'Gestionnaires de mots de passe':                'dQw4w9WgXcQ',  # Password Manager Explained
    'Double authentification (2FA)':                 'dQw4w9WgXcQ',
    'Sécuriser ses réseaux Wi-Fi':                   'dQw4w9WgXcQ',
    'Injection SQL — exploitation et prévention':     '2OPVViV-GQk',  # SQL Injection Explained
    'XSS (Cross-Site Scripting)':                    'EoaDgUgS6QA',  # XSS Explained
    'CSRF et authentification brisée':               'dQw4w9WgXcQ',  # OWASP Explained
    'Headers HTTP de sécurité':                      'dQw4w9WgXcQ',
    'Gestion sécurisée des sessions et JWT':         'dQw4w9WgXcQ',
    'OSINT et reconnaissance passive':               'aO858HyFbKI',  # fCC Ethical Hacking
    'Scan de ports avec Nmap':                       'aO858HyFbKI',
    'Enumération des services':                      'aO858HyFbKI',
    'Metasploit Framework — introduction':           'aO858HyFbKI',
    'Post-exploitation et élévation de privilèges':  'aO858HyFbKI',
    # ── RH ───────────────────────────────────────────────────────────────────────
    'Définir le besoin et rédiger l\'offre':          'dQw4w9WgXcQ',  # Recruitment Process
    'Sélection des candidats — CV et entretiens':     'dQw4w9WgXcQ',
    'Onboarding réussi':                              'dQw4w9WgXcQ',
    'Composantes du salaire brut/net':                'dQw4w9WgXcQ',  # HR & Payroll Basics
    'Cotisations sociales CNSS/IPRES':                'dQw4w9WgXcQ',
    'Droit du travail — éléments clés':               'dQw4w9WgXcQ',
    'Définir son EVP (Employee Value Proposition)':   'dQw4w9WgXcQ',  # Employer Branding
    'Audit de la marque employeur actuelle':          'dQw4w9WgXcQ',
    'Glassdoor et e-réputation employeur':            'dQw4w9WgXcQ',
    'LinkedIn Recruiter avancé':                      'dQw4w9WgXcQ',
    'Boolean search et sourcing créatif':             'dQw4w9WgXcQ',
    'Le rôle du Business Partner RH':                'dQw4w9WgXcQ',  # HRBP Explained
    'Diagnostic organisationnel':                     'dQw4w9WgXcQ',
    'People Analytics et data RH':                   'dQw4w9WgXcQ',
    'Aligner la stratégie RH aux OKR business':       'dQw4w9WgXcQ',
    'Mesurer le ROI des initiatives RH':              'dQw4w9WgXcQ',
    # ── Langues ──────────────────────────────────────────────────────────────────
    'Structure d\'un email business':                 'dQw4w9WgXcQ',  # Business English Emails
    'Formules de politesse et ton approprié':         'dQw4w9WgXcQ',
    'Emails de négociation et de relance':            'dQw4w9WgXcQ',
    'Phrasal verbs de réunion':                       'dQw4w9WgXcQ',  # Business English Meetings
    'Structurer une présentation en anglais':         'dQw4w9WgXcQ',
    'Négociation et gestion des objections':          'dQw4w9WgXcQ',
    'Le vocabulaire de l\'entreprise':                'dQw4w9WgXcQ',  # Français professionnel
    'Expressions courantes en réunion':               'dQw4w9WgXcQ',
    'Rédiger un compte-rendu':                        'dQw4w9WgXcQ',
    'Rédiger une lettre formelle':                    'dQw4w9WgXcQ',
    'Notes de service et circulaires':                'dQw4w9WgXcQ',
    'Escribir correos electrónicos formales':         'dQw4w9WgXcQ',  # Español de negocios
    'Vocabulario de reuniones de negocios':           'dQw4w9WgXcQ',
    'Presentaciones comerciales':                     'dQw4w9WgXcQ',
    'Técnicas de negociación en español':             'dQw4w9WgXcQ',
    # ── Leadership ───────────────────────────────────────────────────────────────
    'Forces et angles morts du leader':               'u4ZoJKF_VuA',  # Simon Sinek - Start with Why
    'Intelligence émotionnelle (EQ)':                 'qp0HIF3SfI4',  # Daniel Goleman EQ TED
    'Valeurs et leadership authentique':              'u4ZoJKF_VuA',
    'Communication inspirante — le "Why"':            'u4ZoJKF_VuA',
    'Créer une culture de haute performance':         'XU0llRltyFM',  # What great leaders do
    'Résilience et gestion de l\'adversité':          'XU0llRltyFM',
    'Les 10 biais cognitifs à connaître':             'wEwGBIr_RIw',  # Cognitive Biases
    'First Principles Thinking':                      'HZRDUZuIKg4',  # First Principles Thinking
    'Matrice décisionnelle et analyse coûts-bénéfices': 'HZRDUZuIKg4',
    'Design Thinking en 5 étapes':                    'a7sEoEvT8l8',  # Design Thinking
    'Ishikawa et 5 Pourquoi':                         'a7sEoEvT8l8',
    'Décider sous incertitude — framework OODA':      'HZRDUZuIKg4',
    'Langage corporel du leader':                     'Ks-_Mh1QhMc',  # Amy Cuddy Body Language TED
    'Prise de parole en CODIR/COMEX':                 'dQw4w9WgXcQ',  # Executive Presence
    'Storytelling pour dirigeants':                   'Nj-hdQMa3uA',  # TED Storytelling
    'Influence sans autorité formelle':               'V74AxCqOTvg',  # Derek Sivers TED
    'Networking stratégique':                         'dQw4w9WgXcQ',
    'Gestion de son personal branding de dirigeant':  'dQw4w9WgXcQ',
}


def _yt(title):
    vid = LESSON_YOUTUBE.get(title, 'dQw4w9WgXcQ')
    return f'https://www.youtube.com/embed/{vid}'


def _past(n):
    return timezone.now() - timedelta(days=n)


def _past_date(n):
    return date.today() - timedelta(days=n)


B2C_CATEGORIES = [
    {'name': 'Informatique & Technologie', 'icon': 'Monitor'},
    {'name': 'Comptabilité', 'icon': 'Calculator'},
    {'name': 'Finance', 'icon': 'BarChart2'},
    {'name': 'Management', 'icon': 'Briefcase'},
    {'name': 'Marketing', 'icon': 'Megaphone'},
    {'name': 'IA & Intelligence Artificielle', 'icon': 'Brain'},
    {'name': 'Cybersécurité', 'icon': 'Shield'},
    {'name': 'Ressources Humaines', 'icon': 'UserCheck'},
    {'name': 'Langues Étrangères', 'icon': 'Globe'},
    {'name': 'Leadership', 'icon': 'Zap'},
]

B2C_COURSES = [
    # ── Informatique ────────────────────────────────────────────────────────────
    {
        'title': 'Python pour les Débutants',
        'subtitle': 'Apprenez Python de zéro et créez vos premiers programmes',
        'description': (
            'Cours complet pour débutants : variables, boucles, fonctions, fichiers et '
            'introduction à la programmation orientée objet. Aucun prérequis nécessaire.'
        ),
        'category': 'Informatique & Technologie',
        'level': 'beginner',
        'price': 29000,
        'sections': [
            {'title': 'Bases de Python', 'chapters': [
                {'title': 'Installation et premier programme', 'lessons': [
                    {'title': 'Installer Python et VS Code', 'content_type': 'video', 'duration_seconds': 900, 'is_preview_free': True},
                    {'title': 'Votre premier programme Hello World', 'content_type': 'video', 'duration_seconds': 600},
                ]},
                {'title': 'Variables et types', 'lessons': [
                    {'title': 'Types de données en Python', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Opérateurs et expressions', 'content_type': 'video', 'duration_seconds': 720},
                ]},
            ]},
            {'title': 'Structures de contrôle', 'chapters': [
                {'title': 'Conditions et boucles', 'lessons': [
                    {'title': 'if / elif / else', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Boucles for et while', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Fonctions — définition et appel', 'content_type': 'video', 'duration_seconds': 960},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Python Débutant',
            'questions': [
                {
                    'text': 'Comment afficher "Bonjour" en Python ?',
                    'choices': [
                        {'text': 'print("Bonjour")', 'is_correct': True},
                        {'text': 'echo "Bonjour"', 'is_correct': False},
                        {'text': 'console.log("Bonjour")', 'is_correct': False},
                        {'text': 'display("Bonjour")', 'is_correct': False},
                    ],
                    'explanation': 'La fonction print() est utilisée pour afficher du texte en Python.',
                },
            ],
        },
    },
    {
        'title': 'Développement Web avec HTML & CSS',
        'subtitle': 'Créez vos premières pages web modernes',
        'description': (
            'Maîtrisez les fondamentaux du web : structure HTML5, mise en page CSS3, '
            'Flexbox, Grid et responsive design. Construisez un portfolio en fin de cours.'
        ),
        'category': 'Informatique & Technologie',
        'level': 'beginner',
        'price': 25000,
        'sections': [
            {'title': 'HTML5 — Structure web', 'chapters': [
                {'title': 'Balises et sémantique', 'lessons': [
                    {'title': 'Structure d\'une page HTML', 'content_type': 'video', 'duration_seconds': 840, 'is_preview_free': True},
                    {'title': 'Balises texte, images, liens', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Formulaires HTML5', 'content_type': 'video', 'duration_seconds': 900},
                ]},
            ]},
            {'title': 'CSS3 & Mise en page', 'chapters': [
                {'title': 'Sélecteurs et propriétés', 'lessons': [
                    {'title': 'Sélecteurs CSS essentiels', 'content_type': 'video', 'duration_seconds': 720},
                    {'title': 'Flexbox en pratique', 'content_type': 'video', 'duration_seconds': 960},
                    {'title': 'CSS Grid Layout', 'content_type': 'video', 'duration_seconds': 1020},
                    {'title': 'Responsive design & media queries', 'content_type': 'video', 'duration_seconds': 900},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — HTML & CSS',
            'questions': [
                {
                    'text': 'Quelle propriété CSS contrôle l\'alignement des éléments en Flexbox ?',
                    'choices': [
                        {'text': 'justify-content', 'is_correct': True},
                        {'text': 'align-text', 'is_correct': False},
                        {'text': 'float', 'is_correct': False},
                        {'text': 'position', 'is_correct': False},
                    ],
                    'explanation': 'justify-content définit l\'alignement sur l\'axe principal du conteneur flex.',
                },
            ],
        },
    },
    {
        'title': 'SQL et Bases de Données Relationnelles',
        'subtitle': 'Requêtes SQL, modélisation et optimisation de bases de données',
        'description': (
            'Apprenez à concevoir et interroger des bases de données relationnelles. '
            'SELECT, JOIN, GROUP BY, sous-requêtes, transactions et indexation.'
        ),
        'category': 'Informatique & Technologie',
        'level': 'intermediate',
        'price': 35000,
        'sections': [
            {'title': 'Fondamentaux SQL', 'chapters': [
                {'title': 'Requêtes de base', 'lessons': [
                    {'title': 'SELECT, FROM, WHERE', 'content_type': 'video', 'duration_seconds': 900, 'is_preview_free': True},
                    {'title': 'ORDER BY et LIMIT', 'content_type': 'video', 'duration_seconds': 600},
                    {'title': 'INSERT, UPDATE, DELETE', 'content_type': 'video', 'duration_seconds': 840},
                ]},
                {'title': 'Jointures et agrégations', 'lessons': [
                    {'title': 'INNER JOIN et LEFT JOIN', 'content_type': 'video', 'duration_seconds': 1080},
                    {'title': 'GROUP BY et fonctions d\'agrégation', 'content_type': 'video', 'duration_seconds': 960},
                    {'title': 'Sous-requêtes et CTE', 'content_type': 'video', 'duration_seconds': 1200},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — SQL',
            'questions': [
                {
                    'text': 'Quelle clause SQL filtre les résultats après un GROUP BY ?',
                    'choices': [
                        {'text': 'HAVING', 'is_correct': True},
                        {'text': 'WHERE', 'is_correct': False},
                        {'text': 'FILTER', 'is_correct': False},
                        {'text': 'ORDER BY', 'is_correct': False},
                    ],
                    'explanation': 'HAVING filtre les groupes après l\'agrégation, WHERE filtre avant.',
                },
            ],
        },
    },

    # ── Comptabilité ─────────────────────────────────────────────────────────────
    {
        'title': 'Comptabilité Générale — Fondamentaux',
        'subtitle': 'Maîtrisez les bases de la comptabilité d\'entreprise',
        'description': (
            'Introduction à la comptabilité générale : bilan, compte de résultat, '
            'plan comptable OHADA, enregistrements de base, TVA et clôture d\'exercice.'
        ),
        'category': 'Comptabilité',
        'level': 'beginner',
        'price': 39000,
        'sections': [
            {'title': 'Principes comptables', 'chapters': [
                {'title': 'Bilan et compte de résultat', 'lessons': [
                    {'title': 'Le bilan : actif et passif', 'content_type': 'video', 'duration_seconds': 1080, 'is_preview_free': True},
                    {'title': 'Le compte de résultat', 'content_type': 'video', 'duration_seconds': 960},
                    {'title': 'Les flux de trésorerie', 'content_type': 'video', 'duration_seconds': 840},
                ]},
            ]},
            {'title': 'Enregistrements comptables', 'chapters': [
                {'title': 'Plan comptable OHADA', 'lessons': [
                    {'title': 'Classes de comptes', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Passation des écritures courantes', 'content_type': 'video', 'duration_seconds': 1200},
                    {'title': 'TVA — collectée et déductible', 'content_type': 'video', 'duration_seconds': 960},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Comptabilité Générale',
            'questions': [
                {
                    'text': 'Dans un bilan, les immobilisations font partie de :',
                    'choices': [
                        {'text': 'L\'actif non courant', 'is_correct': True},
                        {'text': 'L\'actif courant', 'is_correct': False},
                        {'text': 'Le passif courant', 'is_correct': False},
                        {'text': 'Les capitaux propres', 'is_correct': False},
                    ],
                    'explanation': 'Les immobilisations (bâtiments, matériels...) sont des actifs non courants (long terme).',
                },
            ],
        },
    },
    {
        'title': 'Comptabilité Analytique et Contrôle de Gestion',
        'subtitle': 'Coûts, marges et tableaux de bord pour décideurs',
        'description': (
            'Passez à la comptabilité de gestion : analyse des coûts, seuil de rentabilité, '
            'budget prévisionnel, écarts et tableaux de bord de pilotage.'
        ),
        'category': 'Comptabilité',
        'level': 'intermediate',
        'price': 55000,
        'sections': [
            {'title': 'Analyse des coûts', 'chapters': [
                {'title': 'Coûts directs et indirects', 'lessons': [
                    {'title': 'Méthode du coût complet', 'content_type': 'video', 'duration_seconds': 1200, 'is_preview_free': True},
                    {'title': 'Méthode du coût variable (direct costing)', 'content_type': 'video', 'duration_seconds': 1080},
                    {'title': 'Seuil de rentabilité et point mort', 'content_type': 'video', 'duration_seconds': 960},
                ]},
            ]},
            {'title': 'Budget et pilotage', 'chapters': [
                {'title': 'Élaboration budgétaire', 'lessons': [
                    {'title': 'Budget des ventes et production', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Analyse des écarts budget/réel', 'content_type': 'video', 'duration_seconds': 1020},
                    {'title': 'Tableau de bord de gestion', 'content_type': 'video', 'duration_seconds': 840},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Comptabilité Analytique',
            'questions': [
                {
                    'text': 'Le seuil de rentabilité est le niveau de CA pour lequel :',
                    'choices': [
                        {'text': 'Le résultat est nul (ni bénéfice ni perte)', 'is_correct': True},
                        {'text': 'Les charges variables sont couvertes', 'is_correct': False},
                        {'text': 'Le bénéfice est maximal', 'is_correct': False},
                        {'text': 'Les charges fixes sont réduites de moitié', 'is_correct': False},
                    ],
                    'explanation': 'Le seuil de rentabilité (break-even point) est le CA pour lequel marge sur coût variable = charges fixes.',
                },
            ],
        },
    },
    {
        'title': 'Fiscalité des Entreprises en Afrique de l\'Ouest',
        'subtitle': 'TVA, IS, IRPP, CNSS et déclarations fiscales OHADA',
        'description': (
            'Maîtrisez la fiscalité des entreprises en zone UEMOA : TVA, impôt sur les sociétés, '
            'IRPP, cotisations sociales CNSS/IPRES, déclarations et contentieux fiscal.'
        ),
        'category': 'Comptabilité',
        'level': 'intermediate',
        'price': 49000,
        'sections': [
            {'title': 'Taxes et impôts', 'chapters': [
                {'title': 'TVA en pratique', 'lessons': [
                    {'title': 'Mécanisme de la TVA', 'content_type': 'video', 'duration_seconds': 1020, 'is_preview_free': True},
                    {'title': 'Déclaration mensuelle de TVA', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Cas particuliers et exonérations', 'content_type': 'video', 'duration_seconds': 780},
                ]},
                {'title': 'Impôt sur les Sociétés', 'lessons': [
                    {'title': 'Base imposable et taux IS', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Charges déductibles et non-déductibles', 'content_type': 'video', 'duration_seconds': 960},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Fiscalité OHADA',
            'questions': [
                {
                    'text': 'Dans la zone UEMOA, quel est le taux standard de TVA ?',
                    'choices': [
                        {'text': '18 %', 'is_correct': True},
                        {'text': '20 %', 'is_correct': False},
                        {'text': '15 %', 'is_correct': False},
                        {'text': '10 %', 'is_correct': False},
                    ],
                    'explanation': 'Le taux de TVA standard dans les pays de l\'UEMOA est de 18 %.',
                },
            ],
        },
    },

    # ── Finance ──────────────────────────────────────────────────────────────────
    {
        'title': 'Analyse Financière d\'Entreprise',
        'subtitle': 'Lecture des états financiers, ratios et diagnostic financier',
        'description': (
            'Apprenez à analyser la santé financière d\'une entreprise : '
            'interprétation du bilan, compte de résultat, ratios de liquidité, '
            'solvabilité, rentabilité et flux de trésorerie.'
        ),
        'category': 'Finance',
        'level': 'intermediate',
        'price': 59000,
        'sections': [
            {'title': 'Lecture des états financiers', 'chapters': [
                {'title': 'Analyse du bilan', 'lessons': [
                    {'title': 'Bilan fonctionnel et financier', 'content_type': 'video', 'duration_seconds': 1200, 'is_preview_free': True},
                    {'title': 'Fonds de roulement et BFR', 'content_type': 'video', 'duration_seconds': 1080},
                    {'title': 'Trésorerie nette et cycle d\'exploitation', 'content_type': 'video', 'duration_seconds': 960},
                ]},
            ]},
            {'title': 'Ratios financiers', 'chapters': [
                {'title': 'Ratios clés', 'lessons': [
                    {'title': 'Ratios de liquidité', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Ratios de rentabilité (ROE, ROA)', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Ratios d\'endettement', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Tableau de bord financier', 'content_type': 'text', 'duration_seconds': 1800},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Analyse Financière',
            'questions': [
                {
                    'text': 'Le BFR (Besoin en Fonds de Roulement) est calculé comme :',
                    'choices': [
                        {'text': 'Actif circulant d\'exploitation - Dettes d\'exploitation', 'is_correct': True},
                        {'text': 'Capitaux propres - Immobilisations', 'is_correct': False},
                        {'text': 'Résultat net + Amortissements', 'is_correct': False},
                        {'text': 'Chiffre d\'affaires - Coûts variables', 'is_correct': False},
                    ],
                    'explanation': 'Le BFR représente le besoin de financement du cycle d\'exploitation.',
                },
            ],
        },
    },
    {
        'title': 'Finance Islamique — Principes et Pratique',
        'subtitle': 'Mourabaha, Mudaraba, Sukuk et conformité Charia',
        'description': (
            'Découvrez la finance islamique et ses instruments : prohibition du Riba, '
            'contrats Mourabaha, Mudaraba, Musharaka, Sukuk et audit Charia.'
        ),
        'category': 'Finance',
        'level': 'intermediate',
        'price': 65000,
        'sections': [
            {'title': 'Fondements de la Finance Islamique', 'chapters': [
                {'title': 'Principes Charia', 'lessons': [
                    {'title': 'Le Riba et ses alternatives', 'content_type': 'video', 'duration_seconds': 1080, 'is_preview_free': True},
                    {'title': 'Les contrats islamiques fondamentaux', 'content_type': 'video', 'duration_seconds': 960},
                ]},
                {'title': 'Instruments financiers islamiques', 'lessons': [
                    {'title': 'Mourabaha — financement à coût majoré', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Mudaraba et Musharaka', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Les Sukuk (obligations islamiques)', 'content_type': 'video', 'duration_seconds': 1020},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Finance Islamique',
            'questions': [
                {
                    'text': 'Lequel de ces contrats islamiques implique un partage de pertes et profits ?',
                    'choices': [
                        {'text': 'Mudaraba', 'is_correct': True},
                        {'text': 'Mourabaha', 'is_correct': False},
                        {'text': 'Ijara', 'is_correct': False},
                        {'text': 'Salam', 'is_correct': False},
                    ],
                    'explanation': 'La Mudaraba est un contrat de partenariat avec partage des profits et pertes.',
                },
            ],
        },
    },
    {
        'title': 'Gestion de Trésorerie et Cash Management',
        'subtitle': 'Prévisions de trésorerie, financement court terme et placements',
        'description': (
            'Maîtrisez la gestion opérationnelle de la trésorerie : tableau de flux, '
            'prévisions glissantes, lignes de crédit, escompte et placements à court terme.'
        ),
        'category': 'Finance',
        'level': 'advanced',
        'price': 69000,
        'sections': [
            {'title': 'Flux de trésorerie', 'chapters': [
                {'title': 'Tableau de flux', 'lessons': [
                    {'title': 'Flux opérationnels, d\'investissement et de financement', 'content_type': 'video', 'duration_seconds': 1200, 'is_preview_free': True},
                    {'title': 'Méthode directe vs indirecte', 'content_type': 'video', 'duration_seconds': 960},
                    {'title': 'Prévisions glissantes à 13 semaines', 'content_type': 'video', 'duration_seconds': 1080},
                ]},
            ]},
            {'title': 'Financement court terme', 'chapters': [
                {'title': 'Instruments de financement', 'lessons': [
                    {'title': 'Escompte commercial et crédit documentaire', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Affacturage (factoring)', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Optimisation du BFR', 'content_type': 'video', 'duration_seconds': 900},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Trésorerie',
            'questions': [
                {
                    'text': 'L\'escompte commercial consiste à :',
                    'choices': [
                        {'text': 'Céder une créance à la banque avant son échéance', 'is_correct': True},
                        {'text': 'Obtenir un délai de paiement supplémentaire', 'is_correct': False},
                        {'text': 'Placer des excédents en OPCVM', 'is_correct': False},
                        {'text': 'Émettre des billets de trésorerie', 'is_correct': False},
                    ],
                    'explanation': 'L\'escompte permet de récupérer immédiatement la valeur d\'une créance commerciale.',
                },
            ],
        },
    },

    # ── Management ───────────────────────────────────────────────────────────────
    {
        'title': 'Management d\'Équipe — Les Fondamentaux',
        'subtitle': 'Délégation, motivation et gestion de la performance',
        'description': (
            'Développez vos compétences managériales clés : fixation d\'objectifs SMART, '
            'délégation efficace, entretiens de feedback, gestion de conflits et '
            'animation de réunions.'
        ),
        'category': 'Management',
        'level': 'beginner',
        'price': 0,
        'is_free': True,
        'sections': [
            {'title': 'Bases du management', 'chapters': [
                {'title': 'Rôle et missions du manager', 'lessons': [
                    {'title': 'Qu\'est-ce que manager ?', 'content_type': 'video', 'duration_seconds': 900, 'is_preview_free': True},
                    {'title': 'Objectifs SMART et OKR', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Délégation efficace', 'content_type': 'video', 'duration_seconds': 780},
                ]},
            ]},
            {'title': 'Motivation et performance', 'chapters': [
                {'title': 'Motiver son équipe', 'lessons': [
                    {'title': 'Théories de la motivation (Maslow, Herzberg)', 'content_type': 'video', 'duration_seconds': 960},
                    {'title': 'Feedback constructif', 'content_type': 'video', 'duration_seconds': 720},
                    {'title': 'Entretien annuel d\'évaluation', 'content_type': 'video', 'duration_seconds': 900},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Management Fondamentaux',
            'questions': [
                {
                    'text': 'Un objectif SMART doit être :',
                    'choices': [
                        {'text': 'Spécifique, Mesurable, Atteignable, Réaliste, Temporel', 'is_correct': True},
                        {'text': 'Simple, Motivant, Agréable, Rapide, Tangible', 'is_correct': False},
                        {'text': 'Structuré, Modifiable, Automatique, Rapide, Transférable', 'is_correct': False},
                        {'text': 'Systématique, Mesurable, Agile, Robuste, Traçable', 'is_correct': False},
                    ],
                    'explanation': 'SMART = Spécifique, Mesurable, Atteignable, Réaliste, Temporellement défini.',
                },
            ],
        },
    },
    {
        'title': 'Conduite du Changement',
        'subtitle': 'Gérer les transformations organisationnelles avec succès',
        'description': (
            'Apprenez à accompagner les transformations d\'entreprise : modèles de changement '
            '(Kotter, Lewin), communication du changement, gestion des résistances et '
            'ancrage des nouvelles pratiques.'
        ),
        'category': 'Management',
        'level': 'intermediate',
        'price': 59000,
        'sections': [
            {'title': 'Comprendre le changement', 'chapters': [
                {'title': 'Modèles de conduite du changement', 'lessons': [
                    {'title': 'Le modèle de Kotter en 8 étapes', 'content_type': 'video', 'duration_seconds': 1080, 'is_preview_free': True},
                    {'title': 'La courbe du deuil et de l\'adoption', 'content_type': 'video', 'duration_seconds': 840},
                ]},
                {'title': 'Résistances et communication', 'lessons': [
                    {'title': 'Identifier et gérer les résistances', 'content_type': 'video', 'duration_seconds': 960},
                    {'title': 'Plan de communication du changement', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Ancrer les nouvelles pratiques', 'content_type': 'video', 'duration_seconds': 780},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Conduite du Changement',
            'questions': [
                {
                    'text': 'Selon Kotter, quelle est la première étape de la conduite du changement ?',
                    'choices': [
                        {'text': 'Créer un sentiment d\'urgence', 'is_correct': True},
                        {'text': 'Former une coalition directrice', 'is_correct': False},
                        {'text': 'Développer une vision', 'is_correct': False},
                        {'text': 'Ancrer les nouvelles pratiques', 'is_correct': False},
                    ],
                    'explanation': 'La première étape de Kotter est de créer un sentiment d\'urgence pour mobiliser les équipes.',
                },
            ],
        },
    },
    {
        'title': 'Gestion de Projet — Méthodes et Outils',
        'subtitle': 'PMI, Agile, MS Project et gestion des risques',
        'description': (
            'Maîtrisez la gestion de projet de A à Z : cadrage, planification, '
            'suivi d\'avancement, gestion des risques et clôture. Méthodes classiques '
            '(PMI) et agiles (Scrum) abordées.'
        ),
        'category': 'Management',
        'level': 'intermediate',
        'price': 49000,
        'sections': [
            {'title': 'Cadrage et planification', 'chapters': [
                {'title': 'Initialisation du projet', 'lessons': [
                    {'title': 'Charte de projet et parties prenantes', 'content_type': 'video', 'duration_seconds': 960, 'is_preview_free': True},
                    {'title': 'WBS et découpage en livrables', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Planification Gantt', 'content_type': 'video', 'duration_seconds': 1080},
                ]},
            ]},
            {'title': 'Suivi et risques', 'chapters': [
                {'title': 'Pilotage du projet', 'lessons': [
                    {'title': 'Indicateurs de suivi (EVA)', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Registre des risques et plans d\'action', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Réunion de projet efficace', 'content_type': 'video', 'duration_seconds': 720},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Gestion de Projet',
            'questions': [
                {
                    'text': 'Le WBS (Work Breakdown Structure) permet de :',
                    'choices': [
                        {'text': 'Décomposer le projet en livrables et tâches', 'is_correct': True},
                        {'text': 'Calculer le budget du projet', 'is_correct': False},
                        {'text': 'Identifier les parties prenantes', 'is_correct': False},
                        {'text': 'Planifier les ressources humaines', 'is_correct': False},
                    ],
                    'explanation': 'Le WBS structure hiérarchiquement tous les livrables et travaux du projet.',
                },
            ],
        },
    },

    # ── Marketing ────────────────────────────────────────────────────────────────
    {
        'title': 'Marketing Digital — De Zéro à Expert',
        'subtitle': 'SEO, réseaux sociaux, email marketing et analytics',
        'description': (
            'Maîtrisez tous les leviers du marketing digital : référencement naturel, '
            'publicité sur les réseaux sociaux, email marketing, marketing de contenu '
            'et mesure de performance avec Google Analytics 4.'
        ),
        'category': 'Marketing',
        'level': 'beginner',
        'price': 39000,
        'sections': [
            {'title': 'Stratégie digitale', 'chapters': [
                {'title': 'Fondamentaux du marketing digital', 'lessons': [
                    {'title': 'L\'écosystème digital en 2026', 'content_type': 'video', 'duration_seconds': 900, 'is_preview_free': True},
                    {'title': 'Définir sa cible et son positionnement', 'content_type': 'video', 'duration_seconds': 840},
                ]},
            ]},
            {'title': 'SEO et contenu', 'chapters': [
                {'title': 'Référencement naturel', 'lessons': [
                    {'title': 'Recherche de mots-clés', 'content_type': 'video', 'duration_seconds': 1020},
                    {'title': 'Optimisation on-page', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Stratégie de contenu', 'content_type': 'video', 'duration_seconds': 780},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Marketing Digital',
            'questions': [
                {
                    'text': 'GA4 signifie :',
                    'choices': [
                        {'text': 'Google Analytics 4', 'is_correct': True},
                        {'text': 'Global Advertising 4', 'is_correct': False},
                        {'text': 'Google Ads 4', 'is_correct': False},
                        {'text': 'Growth Automation 4', 'is_correct': False},
                    ],
                    'explanation': 'GA4 est la 4e génération de Google Analytics, lancée en 2020.',
                },
            ],
        },
    },
    {
        'title': 'Brand Strategy — Construire une Marque Forte',
        'subtitle': 'Identité de marque, storytelling et brand management',
        'description': (
            'Créez et développez une marque mémorable : définition de la mission, '
            'vision, valeurs, identité visuelle, architecture de marque, '
            'storytelling et gestion de la réputation.'
        ),
        'category': 'Marketing',
        'level': 'intermediate',
        'price': 55000,
        'sections': [
            {'title': 'Fondations de la marque', 'chapters': [
                {'title': 'Identité et positionnement', 'lessons': [
                    {'title': 'Mission, vision et valeurs de marque', 'content_type': 'video', 'duration_seconds': 960, 'is_preview_free': True},
                    {'title': 'Analyse de la concurrence et positionnement', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Architecture de marque (master brand vs multimarca)', 'content_type': 'video', 'duration_seconds': 840},
                ]},
                {'title': 'Identité visuelle', 'lessons': [
                    {'title': 'Logo, couleurs et typographie', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Charte graphique et guide de marque', 'content_type': 'video', 'duration_seconds': 720},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Brand Strategy',
            'questions': [
                {
                    'text': 'Le brand equity (valeur de marque) se mesure principalement par :',
                    'choices': [
                        {'text': 'La notoriété, la fidélité et les associations à la marque', 'is_correct': True},
                        {'text': 'Le chiffre d\'affaires généré', 'is_correct': False},
                        {'text': 'Le nombre de produits vendus', 'is_correct': False},
                        {'text': 'La taille de l\'équipe marketing', 'is_correct': False},
                    ],
                    'explanation': 'Le brand equity inclut notoriété, associations, qualité perçue et fidélité.',
                },
            ],
        },
    },
    {
        'title': 'Growth Hacking et Acquisition Clients',
        'subtitle': 'Techniques d\'acquisition rapide et scaling digital',
        'description': (
            'Adoptez les méthodes du growth hacking : funnel AARRR, A/B testing, '
            'viral loops, Product-Led Growth, SEO programmatique et automatisation '
            'de l\'acquisition client.'
        ),
        'category': 'Marketing',
        'level': 'advanced',
        'price': 75000,
        'sections': [
            {'title': 'Framework Growth', 'chapters': [
                {'title': 'Le funnel AARRR', 'lessons': [
                    {'title': 'Acquisition — attirer les visiteurs', 'content_type': 'video', 'duration_seconds': 960, 'is_preview_free': True},
                    {'title': 'Activation et rétention utilisateurs', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Revenus et referral loops', 'content_type': 'video', 'duration_seconds': 840},
                ]},
                {'title': 'Expérimentation', 'lessons': [
                    {'title': 'A/B testing méthodologique', 'content_type': 'video', 'duration_seconds': 1020},
                    {'title': 'Landing pages haute conversion', 'content_type': 'video', 'duration_seconds': 840},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Growth Hacking',
            'questions': [
                {
                    'text': 'Dans le framework AARRR, que signifie la deuxième lettre "A" ?',
                    'choices': [
                        {'text': 'Activation', 'is_correct': True},
                        {'text': 'Analytics', 'is_correct': False},
                        {'text': 'Automation', 'is_correct': False},
                        {'text': 'Awareness', 'is_correct': False},
                    ],
                    'explanation': 'AARRR = Acquisition, Activation, Rétention, Revenus, Referral.',
                },
            ],
        },
    },

    # ── IA ───────────────────────────────────────────────────────────────────────
    {
        'title': 'Introduction à l\'Intelligence Artificielle',
        'subtitle': 'ML, Deep Learning, NLP et cas d\'usage pratiques',
        'description': (
            'Comprenez l\'IA sans coder : machine learning supervisé et non supervisé, '
            'réseaux de neurones, NLP, IA générative et impacts métiers. Cours accessible '
            'sans prérequis mathématiques avancés.'
        ),
        'category': 'IA & Intelligence Artificielle',
        'level': 'beginner',
        'price': 45000,
        'sections': [
            {'title': 'Fondamentaux de l\'IA', 'chapters': [
                {'title': 'Qu\'est-ce que l\'IA ?', 'lessons': [
                    {'title': 'Histoire et évolution de l\'IA', 'content_type': 'video', 'duration_seconds': 900, 'is_preview_free': True},
                    {'title': 'Machine Learning vs Deep Learning', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Données : le carburant de l\'IA', 'content_type': 'video', 'duration_seconds': 780},
                ]},
                {'title': 'Modèles et algorithmes', 'lessons': [
                    {'title': 'Apprentissage supervisé — régression et classification', 'content_type': 'video', 'duration_seconds': 1080},
                    {'title': 'Clustering et apprentissage non supervisé', 'content_type': 'video', 'duration_seconds': 960},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Introduction IA',
            'questions': [
                {
                    'text': 'Un algorithme de machine learning "supervisé" apprend à partir de :',
                    'choices': [
                        {'text': 'Données étiquetées (avec les bonnes réponses)', 'is_correct': True},
                        {'text': 'Données non étiquetées', 'is_correct': False},
                        {'text': 'Règles codées manuellement', 'is_correct': False},
                        {'text': 'L\'interaction avec l\'environnement', 'is_correct': False},
                    ],
                    'explanation': 'L\'apprentissage supervisé utilise des exemples avec les labels corrects.',
                },
            ],
        },
    },
    {
        'title': 'ChatGPT et IA Générative pour les Pros',
        'subtitle': 'Prompt engineering, automatisation et outils IA au quotidien',
        'description': (
            'Exploitez l\'IA générative dans votre travail : prompt engineering avancé, '
            'ChatGPT, Claude, Midjourney, automatisation de tâches et intégration '
            'dans vos processus métiers.'
        ),
        'category': 'IA & Intelligence Artificielle',
        'level': 'beginner',
        'price': 35000,
        'sections': [
            {'title': 'Maîtriser les LLMs', 'chapters': [
                {'title': 'Prompt engineering', 'lessons': [
                    {'title': 'Anatomie d\'un bon prompt', 'content_type': 'video', 'duration_seconds': 840, 'is_preview_free': True},
                    {'title': 'Chain-of-Thought et Few-Shot prompting', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Prompts pour la rédaction et la synthèse', 'content_type': 'video', 'duration_seconds': 780},
                ]},
                {'title': 'Outils IA par métier', 'lessons': [
                    {'title': 'IA pour les RH et la formation', 'content_type': 'video', 'duration_seconds': 720},
                    {'title': 'IA pour les finances et la comptabilité', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'IA pour le marketing et la communication', 'content_type': 'video', 'duration_seconds': 840},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — IA Générative',
            'questions': [
                {
                    'text': 'Le "Few-Shot prompting" consiste à :',
                    'choices': [
                        {'text': 'Fournir des exemples dans le prompt pour guider l\'IA', 'is_correct': True},
                        {'text': 'Limiter la réponse à quelques mots', 'is_correct': False},
                        {'text': 'Entraîner un nouveau modèle', 'is_correct': False},
                        {'text': 'Utiliser l\'IA hors ligne', 'is_correct': False},
                    ],
                    'explanation': 'Le few-shot learning donne quelques exemples dans le prompt pour orienter la réponse.',
                },
            ],
        },
    },
    {
        'title': 'Machine Learning avec Python — Scikit-learn',
        'subtitle': 'Régression, classification, clustering et évaluation de modèles',
        'description': (
            'Construisez des modèles de machine learning avec Python et scikit-learn : '
            'préparation des données, feature engineering, modèles supervisés et non '
            'supervisés, validation croisée et déploiement.'
        ),
        'category': 'IA & Intelligence Artificielle',
        'level': 'intermediate',
        'price': 69000,
        'sections': [
            {'title': 'Scikit-learn en pratique', 'chapters': [
                {'title': 'Préparation des données', 'lessons': [
                    {'title': 'Feature engineering et sélection', 'content_type': 'video', 'duration_seconds': 1080, 'is_preview_free': True},
                    {'title': 'Encodage et normalisation', 'content_type': 'video', 'duration_seconds': 900},
                ]},
                {'title': 'Modèles ML', 'lessons': [
                    {'title': 'Régression linéaire et logistique', 'content_type': 'video', 'duration_seconds': 960},
                    {'title': 'Random Forest et Gradient Boosting', 'content_type': 'video', 'duration_seconds': 1020},
                    {'title': 'Validation croisée et métriques', 'content_type': 'video', 'duration_seconds': 840},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Machine Learning',
            'questions': [
                {
                    'text': 'La validation croisée (cross-validation) sert à :',
                    'choices': [
                        {'text': 'Évaluer la généralisation du modèle sur des données non vues', 'is_correct': True},
                        {'text': 'Nettoyer les données d\'entraînement', 'is_correct': False},
                        {'text': 'Accélérer l\'entraînement du modèle', 'is_correct': False},
                        {'text': 'Sélectionner les features automatiquement', 'is_correct': False},
                    ],
                    'explanation': 'La cross-validation évalue la capacité de généralisation en testant sur plusieurs sous-ensembles.',
                },
            ],
        },
    },

    # ── Cybersécurité ────────────────────────────────────────────────────────────
    {
        'title': 'Cybersécurité — Sensibilisation pour Tous',
        'subtitle': 'Phishing, mots de passe, vie privée et bonnes pratiques',
        'description': (
            'Protégez-vous et votre entreprise des cybermenaces : phishing, ransomware, '
            'gestion des mots de passe, RGPD/vie privée, sécurité des emails et '
            'bonnes pratiques numériques. Aucun prérequis technique.'
        ),
        'category': 'Cybersécurité',
        'level': 'beginner',
        'price': 0,
        'is_free': True,
        'sections': [
            {'title': 'Menaces courantes', 'chapters': [
                {'title': 'Reconnaître les attaques', 'lessons': [
                    {'title': 'Phishing : reconnaître et éviter', 'content_type': 'video', 'duration_seconds': 840, 'is_preview_free': True},
                    {'title': 'Ransomware : comment se protéger', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Ingénierie sociale et manipulation', 'content_type': 'video', 'duration_seconds': 720},
                ]},
            ]},
            {'title': 'Bonnes pratiques', 'chapters': [
                {'title': 'Hygiène numérique', 'lessons': [
                    {'title': 'Gestionnaires de mots de passe', 'content_type': 'video', 'duration_seconds': 660},
                    {'title': 'Double authentification (2FA)', 'content_type': 'video', 'duration_seconds': 600},
                    {'title': 'Sécuriser ses réseaux Wi-Fi', 'content_type': 'video', 'duration_seconds': 540},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Cybersécurité Basique',
            'questions': [
                {
                    'text': 'Le phishing est une technique qui consiste à :',
                    'choices': [
                        {'text': 'Tromper l\'utilisateur pour voler ses identifiants ou données', 'is_correct': True},
                        {'text': 'Ralentir un site web par des requêtes massives', 'is_correct': False},
                        {'text': 'Crypter les fichiers d\'un ordinateur contre rançon', 'is_correct': False},
                        {'text': 'Intercepter le trafic réseau', 'is_correct': False},
                    ],
                    'explanation': 'Le phishing (hameçonnage) imite des entités de confiance pour voler des informations.',
                },
            ],
        },
    },
    {
        'title': 'Sécurité des Applications Web (OWASP)',
        'subtitle': 'Injection SQL, XSS, CSRF, authentification et tests de pénétration',
        'description': (
            'Sécurisez vos applications web selon les standards OWASP Top 10 : '
            'injection SQL, XSS, CSRF, mauvaise configuration, exposition de données '
            'sensibles et méthodes de test de pénétration.'
        ),
        'category': 'Cybersécurité',
        'level': 'intermediate',
        'price': 65000,
        'sections': [
            {'title': 'OWASP Top 10', 'chapters': [
                {'title': 'Vulnérabilités critiques', 'lessons': [
                    {'title': 'Injection SQL — exploitation et prévention', 'content_type': 'video', 'duration_seconds': 1200, 'is_preview_free': True},
                    {'title': 'XSS (Cross-Site Scripting)', 'content_type': 'video', 'duration_seconds': 1080},
                    {'title': 'CSRF et authentification brisée', 'content_type': 'video', 'duration_seconds': 960},
                ]},
                {'title': 'Sécurisation', 'lessons': [
                    {'title': 'Headers HTTP de sécurité', 'content_type': 'video', 'duration_seconds': 720},
                    {'title': 'Gestion sécurisée des sessions et JWT', 'content_type': 'video', 'duration_seconds': 900},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — OWASP',
            'questions': [
                {
                    'text': 'Quelle technique permet d\'éviter les injections SQL ?',
                    'choices': [
                        {'text': 'Les requêtes paramétrées (prepared statements)', 'is_correct': True},
                        {'text': 'La validation côté client uniquement', 'is_correct': False},
                        {'text': 'L\'encodage Base64 des données', 'is_correct': False},
                        {'text': 'L\'utilisation de SSL/TLS', 'is_correct': False},
                    ],
                    'explanation': 'Les prepared statements séparent le code SQL des données, éliminant le risque d\'injection.',
                },
            ],
        },
    },
    {
        'title': 'Ethical Hacking et Tests d\'Intrusion',
        'subtitle': 'Pentesting, Kali Linux, Metasploit et rapports de sécurité',
        'description': (
            'Devenez un hacker éthique : méthodologie de pentest, reconnaissance, '
            'scan de vulnérabilités avec Nmap/Nessus, exploitation avec Metasploit, '
            'rapport de sécurité et remédiation.'
        ),
        'category': 'Cybersécurité',
        'level': 'advanced',
        'price': 89000,
        'sections': [
            {'title': 'Méthodologie Pentest', 'chapters': [
                {'title': 'Phase de reconnaissance', 'lessons': [
                    {'title': 'OSINT et reconnaissance passive', 'content_type': 'video', 'duration_seconds': 1200, 'is_preview_free': True},
                    {'title': 'Scan de ports avec Nmap', 'content_type': 'video', 'duration_seconds': 1080},
                    {'title': 'Enumération des services', 'content_type': 'video', 'duration_seconds': 960},
                ]},
                {'title': 'Exploitation', 'lessons': [
                    {'title': 'Metasploit Framework — introduction', 'content_type': 'video', 'duration_seconds': 1320},
                    {'title': 'Post-exploitation et élévation de privilèges', 'content_type': 'video', 'duration_seconds': 1200},
                    {'title': 'Rédaction d\'un rapport de pentest', 'content_type': 'text', 'duration_seconds': 1800},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Ethical Hacking',
            'questions': [
                {
                    'text': 'Qu\'est-ce que l\'OSINT en cybersécurité ?',
                    'choices': [
                        {'text': 'La collecte d\'informations à partir de sources publiques', 'is_correct': True},
                        {'text': 'Un outil d\'analyse de malwares', 'is_correct': False},
                        {'text': 'Un protocole de chiffrement', 'is_correct': False},
                        {'text': 'Un framework d\'exploitation', 'is_correct': False},
                    ],
                    'explanation': 'OSINT (Open Source Intelligence) utilise des sources publiques (réseaux sociaux, DNS, etc.).',
                },
            ],
        },
    },

    # ── RH ───────────────────────────────────────────────────────────────────────
    {
        'title': 'Gestion des Ressources Humaines — Fondamentaux',
        'subtitle': 'Recrutement, formation, paie et droit du travail',
        'description': (
            'Maîtrisez les fondamentaux RH : cycle de recrutement, onboarding, '
            'formation et développement, gestion de la paie, droit du travail '
            'et relations sociales.'
        ),
        'category': 'Ressources Humaines',
        'level': 'beginner',
        'price': 45000,
        'sections': [
            {'title': 'Recrutement et intégration', 'chapters': [
                {'title': 'Cycle de recrutement', 'lessons': [
                    {'title': 'Définir le besoin et rédiger l\'offre', 'content_type': 'video', 'duration_seconds': 840, 'is_preview_free': True},
                    {'title': 'Sélection des candidats — CV et entretiens', 'content_type': 'video', 'duration_seconds': 960},
                    {'title': 'Onboarding réussi', 'content_type': 'video', 'duration_seconds': 780},
                ]},
            ]},
            {'title': 'Gestion de la paie', 'chapters': [
                {'title': 'Éléments de la paie', 'lessons': [
                    {'title': 'Composantes du salaire brut/net', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Cotisations sociales CNSS/IPRES', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Droit du travail — éléments clés', 'content_type': 'video', 'duration_seconds': 1020},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — GRH Fondamentaux',
            'questions': [
                {
                    'text': 'L\'onboarding désigne :',
                    'choices': [
                        {'text': 'Le processus d\'intégration d\'un nouveau collaborateur', 'is_correct': True},
                        {'text': 'La procédure de licenciement', 'is_correct': False},
                        {'text': 'L\'évaluation annuelle des performances', 'is_correct': False},
                        {'text': 'La négociation salariale', 'is_correct': False},
                    ],
                    'explanation': 'L\'onboarding couvre l\'accueil, la formation et l\'intégration des nouvelles recrues.',
                },
            ],
        },
    },
    {
        'title': 'Marque Employeur et Attraction des Talents',
        'subtitle': 'EVP, réseaux sociaux RH et stratégie de recrutement moderne',
        'description': (
            'Développez votre marque employeur pour attirer et fidéliser les meilleurs talents : '
            'Employee Value Proposition (EVP), LinkedIn Recruiter, sourcing digital, '
            'expérience candidat et programme de cooptation.'
        ),
        'category': 'Ressources Humaines',
        'level': 'intermediate',
        'price': 55000,
        'sections': [
            {'title': 'Marque employeur', 'chapters': [
                {'title': 'EVP et positionnement', 'lessons': [
                    {'title': 'Définir son EVP (Employee Value Proposition)', 'content_type': 'video', 'duration_seconds': 960, 'is_preview_free': True},
                    {'title': 'Audit de la marque employeur actuelle', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Glassdoor et e-réputation employeur', 'content_type': 'video', 'duration_seconds': 780},
                ]},
                {'title': 'Sourcing digital', 'lessons': [
                    {'title': 'LinkedIn Recruiter avancé', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Boolean search et sourcing créatif', 'content_type': 'video', 'duration_seconds': 840},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Marque Employeur',
            'questions': [
                {
                    'text': 'L\'EVP (Employee Value Proposition) définit :',
                    'choices': [
                        {'text': 'La valeur unique offerte aux employés en échange de leur engagement', 'is_correct': True},
                        {'text': 'Le montant du salaire proposé', 'is_correct': False},
                        {'text': 'Le nombre de postes à recruter', 'is_correct': False},
                        {'text': 'Les avantages fiscaux de l\'entreprise', 'is_correct': False},
                    ],
                    'explanation': 'L\'EVP englobe tout ce qui rend l\'entreprise attractive : culture, développement, rémunération, flexibilité.',
                },
            ],
        },
    },
    {
        'title': 'HRBP — Business Partner RH',
        'subtitle': 'Aligner la stratégie RH aux enjeux business',
        'description': (
            'Devenez un Business Partner RH efficace : diagnostic organisationnel, '
            'People Analytics, plan de transformation RH, conseil aux managers et '
            'mesure de l\'impact RH sur la performance business.'
        ),
        'category': 'Ressources Humaines',
        'level': 'advanced',
        'price': 79000,
        'sections': [
            {'title': 'Posture HRBP', 'chapters': [
                {'title': 'Du RH généraliste au HRBP', 'lessons': [
                    {'title': 'Le rôle du Business Partner RH', 'content_type': 'video', 'duration_seconds': 960, 'is_preview_free': True},
                    {'title': 'Diagnostic organisationnel', 'content_type': 'video', 'duration_seconds': 1080},
                    {'title': 'People Analytics et data RH', 'content_type': 'video', 'duration_seconds': 1020},
                ]},
                {'title': 'Impact et transformation', 'lessons': [
                    {'title': 'Aligner la stratégie RH aux OKR business', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Mesurer le ROI des initiatives RH', 'content_type': 'video', 'duration_seconds': 840},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — HRBP',
            'questions': [
                {
                    'text': 'Le People Analytics permet principalement de :',
                    'choices': [
                        {'text': 'Prendre des décisions RH basées sur des données objectives', 'is_correct': True},
                        {'text': 'Automatiser l\'administration de la paie', 'is_correct': False},
                        {'text': 'Remplacer les entretiens de recrutement', 'is_correct': False},
                        {'text': 'Gérer les congés des employés', 'is_correct': False},
                    ],
                    'explanation': 'Le People Analytics utilise les données RH pour des insights objectifs et prédictifs.',
                },
            ],
        },
    },

    # ── Langues ──────────────────────────────────────────────────────────────────
    {
        'title': 'Anglais Professionnel — Business English',
        'subtitle': 'Emails, réunions, négociations et présentations en anglais',
        'description': (
            'Maîtrisez l\'anglais des affaires : rédaction d\'emails professionnels, '
            'participation aux réunions, négociation, présentations et vocabulaire '
            'sectoriel (finance, marketing, technologie).'
        ),
        'category': 'Langues Étrangères',
        'level': 'intermediate',
        'price': 49000,
        'sections': [
            {'title': 'Communication écrite', 'chapters': [
                {'title': 'Emails professionnels en anglais', 'lessons': [
                    {'title': 'Structure d\'un email business', 'content_type': 'video', 'duration_seconds': 840, 'is_preview_free': True},
                    {'title': 'Formules de politesse et ton approprié', 'content_type': 'video', 'duration_seconds': 720},
                    {'title': 'Emails de négociation et de relance', 'content_type': 'video', 'duration_seconds': 780},
                ]},
            ]},
            {'title': 'Communication orale', 'chapters': [
                {'title': 'Réunions et présentations', 'lessons': [
                    {'title': 'Phrasal verbs de réunion', 'content_type': 'video', 'duration_seconds': 660},
                    {'title': 'Structurer une présentation en anglais', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Négociation et gestion des objections', 'content_type': 'video', 'duration_seconds': 960},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Business English',
            'questions': [
                {
                    'text': 'Pour commencer formellement un email professionnel en anglais, on utilise :',
                    'choices': [
                        {'text': '"Dear Mr./Ms. [Nom],"', 'is_correct': True},
                        {'text': '"Hey [Prénom],"', 'is_correct': False},
                        {'text': '"Hi there,"', 'is_correct': False},
                        {'text': '"Hello buddy,"', 'is_correct': False},
                    ],
                    'explanation': '"Dear [titre] [nom]" est la salutation formelle standard en Business English.',
                },
            ],
        },
    },
    {
        'title': 'Français Professionnel pour Non-Francophones',
        'subtitle': 'Communication écrite et orale dans le monde du travail francophone',
        'description': (
            'Développez vos compétences en français professionnel : vocabulaire du monde du travail, '
            'rédaction administrative, prise de parole en réunion et compréhension '
            'des nuances culturelles du management francophone.'
        ),
        'category': 'Langues Étrangères',
        'level': 'beginner',
        'price': 35000,
        'sections': [
            {'title': 'Communication au travail', 'chapters': [
                {'title': 'Vocabulaire professionnel', 'lessons': [
                    {'title': 'Le vocabulaire de l\'entreprise', 'content_type': 'video', 'duration_seconds': 780, 'is_preview_free': True},
                    {'title': 'Expressions courantes en réunion', 'content_type': 'video', 'duration_seconds': 720},
                    {'title': 'Rédiger un compte-rendu', 'content_type': 'video', 'duration_seconds': 840},
                ]},
            ]},
            {'title': 'Écrits professionnels', 'chapters': [
                {'title': 'Documents administratifs', 'lessons': [
                    {'title': 'Rédiger une lettre formelle', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Notes de service et circulaires', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Nuances culturelles du management francophone', 'content_type': 'text', 'duration_seconds': 1200},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Français Professionnel',
            'questions': [
                {
                    'text': 'Quelle formule de politesse termine une lettre formelle en français ?',
                    'choices': [
                        {'text': '"Veuillez agréer, Madame/Monsieur, l\'expression de mes salutations distinguées."', 'is_correct': True},
                        {'text': '"À bientôt !"', 'is_correct': False},
                        {'text': '"Cordialement,"', 'is_correct': False},
                        {'text': '"Bien à vous,"', 'is_correct': False},
                    ],
                    'explanation': 'La formule de politesse complète est obligatoire dans les lettres formelles françaises.',
                },
            ],
        },
    },
    {
        'title': 'Espagnol des Affaires — Nivel Intermedio',
        'subtitle': 'Negociaciones, presentaciones y correspondencia comercial en español',
        'description': (
            'Développez vos compétences en espagnol des affaires : vocabulaire commercial, '
            'correspondance d\'affaires, réunions et négociations, et découverte des '
            'marchés hispanophones (Espagne, Amérique Latine).'
        ),
        'category': 'Langues Étrangères',
        'level': 'intermediate',
        'price': 45000,
        'sections': [
            {'title': 'Comunicación empresarial', 'chapters': [
                {'title': 'Correspondencia y reuniones', 'lessons': [
                    {'title': 'Escribir correos electrónicos formales', 'content_type': 'video', 'duration_seconds': 840, 'is_preview_free': True},
                    {'title': 'Vocabulario de reuniones de negocios', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Presentaciones comerciales', 'content_type': 'video', 'duration_seconds': 900},
                ]},
                {'title': 'Negociación', 'lessons': [
                    {'title': 'Técnicas de negociación en español', 'content_type': 'video', 'duration_seconds': 960},
                    {'title': 'Diferencias culturales hispanoáfrica', 'content_type': 'text', 'duration_seconds': 1200},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Español de Negocios',
            'questions': [
                {
                    'text': 'Comment dit-on "Je suis ravi de faire votre connaissance" en espagnol professionnel ?',
                    'choices': [
                        {'text': '"Encantado/a de conocerle."', 'is_correct': True},
                        {'text': '"¡Hola amigo!"', 'is_correct': False},
                        {'text': '"¿Qué tal?"', 'is_correct': False},
                        {'text': '"Buenos días, tío."', 'is_correct': False},
                    ],
                    'explanation': '"Encantado/a de conocerle" est la formule formelle de présentation en espagnol professionnel.',
                },
            ],
        },
    },

    # ── Leadership ───────────────────────────────────────────────────────────────
    {
        'title': 'Leadership Authentique et Inspirant',
        'subtitle': 'Vision, influence et développement de votre leadership personnel',
        'description': (
            'Développez votre leadership authentique : connaissance de soi, '
            'intelligence émotionnelle, communication inspirante, gestion de l\'adversité '
            'et création d\'une culture de performance durable.'
        ),
        'category': 'Leadership',
        'level': 'intermediate',
        'price': 59000,
        'sections': [
            {'title': 'Leadership personnel', 'chapters': [
                {'title': 'Connaissance de soi', 'lessons': [
                    {'title': 'Forces et angles morts du leader', 'content_type': 'video', 'duration_seconds': 960, 'is_preview_free': True},
                    {'title': 'Intelligence émotionnelle (EQ)', 'content_type': 'video', 'duration_seconds': 1080},
                    {'title': 'Valeurs et leadership authentique', 'content_type': 'video', 'duration_seconds': 840},
                ]},
            ]},
            {'title': 'Influence et culture', 'chapters': [
                {'title': 'Inspirer son équipe', 'lessons': [
                    {'title': 'Communication inspirante — le "Why"', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Créer une culture de haute performance', 'content_type': 'video', 'duration_seconds': 960},
                    {'title': 'Résilience et gestion de l\'adversité', 'content_type': 'video', 'duration_seconds': 780},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Leadership',
            'questions': [
                {
                    'text': 'Selon Simon Sinek, le "Golden Circle" commence par :',
                    'choices': [
                        {'text': 'Le Why (Pourquoi)', 'is_correct': True},
                        {'text': 'Le What (Quoi)', 'is_correct': False},
                        {'text': 'Le How (Comment)', 'is_correct': False},
                        {'text': 'Le Who (Qui)', 'is_correct': False},
                    ],
                    'explanation': 'Sinek affirme que les leaders inspirants commencent toujours par expliquer leur "Pourquoi".',
                },
            ],
        },
    },
    {
        'title': 'Prise de Décision et Pensée Stratégique',
        'subtitle': 'Outils analytiques, biais cognitifs et décision en incertitude',
        'description': (
            'Améliorez la qualité de vos décisions : modèles de pensée stratégique, '
            'identification des biais cognitifs, méthodes de résolution de problèmes '
            '(Design Thinking, Six Sigma), et décision en contexte d\'incertitude.'
        ),
        'category': 'Leadership',
        'level': 'intermediate',
        'price': 49000,
        'sections': [
            {'title': 'Pensée critique', 'chapters': [
                {'title': 'Modèles mentaux', 'lessons': [
                    {'title': 'Les 10 biais cognitifs à connaître', 'content_type': 'video', 'duration_seconds': 1080, 'is_preview_free': True},
                    {'title': 'First Principles Thinking', 'content_type': 'video', 'duration_seconds': 900},
                    {'title': 'Matrice décisionnelle et analyse coûts-bénéfices', 'content_type': 'video', 'duration_seconds': 840},
                ]},
            ]},
            {'title': 'Résolution de problèmes', 'chapters': [
                {'title': 'Méthodes structurées', 'lessons': [
                    {'title': 'Design Thinking en 5 étapes', 'content_type': 'video', 'duration_seconds': 1020},
                    {'title': 'Ishikawa et 5 Pourquoi', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Décider sous incertitude — framework OODA', 'content_type': 'video', 'duration_seconds': 900},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Pensée Stratégique',
            'questions': [
                {
                    'text': 'Le biais de confirmation consiste à :',
                    'choices': [
                        {'text': 'Rechercher des informations qui confirment nos croyances existantes', 'is_correct': True},
                        {'text': 'Surpondérer les événements récents', 'is_correct': False},
                        {'text': 'Attribuer nos succès à nos talents et nos échecs à la chance', 'is_correct': False},
                        {'text': 'Suivre le comportement de la majorité', 'is_correct': False},
                    ],
                    'explanation': 'Le biais de confirmation nous pousse à chercher et interpréter les infos qui renforcent nos opinions.',
                },
            ],
        },
    },
    {
        'title': 'Executive Presence — Affirmer son Leadership au Plus Haut Niveau',
        'subtitle': 'Image, autorité naturelle et influence sans pouvoir formel',
        'description': (
            'Développez votre présence exécutive : langage non-verbal, prise de parole '
            'en comité de direction, gestion de son image professionnelle, influence sans '
            'autorité formelle et gestion des parties prenantes senior.'
        ),
        'category': 'Leadership',
        'level': 'advanced',
        'price': 85000,
        'sections': [
            {'title': 'Présence et impact', 'chapters': [
                {'title': 'Communication exécutive', 'lessons': [
                    {'title': 'Langage corporel du leader', 'content_type': 'video', 'duration_seconds': 960, 'is_preview_free': True},
                    {'title': 'Prise de parole en CODIR/COMEX', 'content_type': 'video', 'duration_seconds': 1080},
                    {'title': 'Storytelling pour dirigeants', 'content_type': 'video', 'duration_seconds': 900},
                ]},
                {'title': 'Influence et réseaux', 'lessons': [
                    {'title': 'Influence sans autorité formelle', 'content_type': 'video', 'duration_seconds': 840},
                    {'title': 'Networking stratégique', 'content_type': 'video', 'duration_seconds': 780},
                    {'title': 'Gestion de son personal branding de dirigeant', 'content_type': 'video', 'duration_seconds': 900},
                ]},
            ]},
        ],
        'quiz': {
            'title': 'Quiz — Executive Presence',
            'questions': [
                {
                    'text': 'L\'executive presence se construit principalement sur :',
                    'choices': [
                        {'text': 'Gravitas (crédibilité), communication et apparence', 'is_correct': True},
                        {'text': 'Le titre hiérarchique', 'is_correct': False},
                        {'text': 'Le nombre d\'années d\'expérience', 'is_correct': False},
                        {'text': 'L\'ancienneté dans l\'entreprise', 'is_correct': False},
                    ],
                    'explanation': 'Selon Sylvia Ann Hewlett, l\'executive presence repose sur la gravitas, la communication et l\'apparence.',
                },
            ],
        },
    },
]


class Command(BaseCommand):
    help = 'Seed B2C course catalog (company=None) across 10 disciplines'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete B2C courses (company=None) then re-create')

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
        from apps.assessments.models import (
            QuestionBank, Question, QuestionChoice, Assessment, AssessmentQuestion,
        )

        reset = options['reset']
        if reset:
            count, _ = Course.objects.filter(company__isnull=True).delete()
            if count:
                self.warn(f'Deleted {count} B2C courses')
            count, _ = Category.objects.filter(
                name__in=[c['name'] for c in B2C_CATEGORIES]
            ).delete()
            if count:
                self.warn(f'Deleted {count} B2C categories')

        # Get trainer user (or first available trainer/superuser)
        trainer = (
            User.objects.filter(email='trainer@lmspro.com').first()
            or User.objects.filter(role='trainer').first()
            or User.objects.filter(is_superuser=True).first()
        )
        if not trainer:
            self.warn('No trainer/superuser found — run seed_demo first!')
            return

        with transaction.atomic():
            # ── 1. Categories ────────────────────────────────────────────────────
            self.log('\n[1] Categories...')
            cat_objects = {}
            for c in B2C_CATEGORIES:
                obj, created = Category.objects.get_or_create(
                    name=c['name'],
                    defaults={'icon': c['icon'], 'is_active': True},
                )
                cat_objects[c['name']] = obj
                if created:
                    self.ok(f'Category: {obj.name}')
                else:
                    self.skip(f'Category: {obj.name}')

            # ── 2. Courses ───────────────────────────────────────────────────────
            self.log('\n[2] Courses (B2C — company=None)...')
            course_count = 0

            for cd in B2C_COURSES:
                cat = cat_objects.get(cd['category'])
                course, created = Course.objects.get_or_create(
                    title=cd['title'],
                    defaults={
                        'company': None,
                        'is_company_internal': False,
                        'category': cat,
                        'instructor': trainer,
                        'subtitle': cd.get('subtitle', ''),
                        'description': cd.get('description', ''),
                        'level': cd.get('level', 'all_levels'),
                        'price': cd.get('price', 0),
                        'is_free': cd.get('is_free', cd.get('price', 1) == 0),
                        'status': 'published',
                        'requirements': cd.get('requirements', []),
                        'what_you_will_learn': cd.get('what_you_will_learn', []),
                        'certificate_enabled': True,
                        'published_at': _past(random.randint(10, 60)),
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
                            embed_url = _yt(lesson_data['title']) if lesson_data.get('content_type') == 'video' else ''
                            lesson, created = Lesson.objects.get_or_create(
                                chapter=chapter, title=lesson_data['title'],
                                defaults={
                                    'order': l_idx,
                                    'content_type': lesson_data.get('content_type', 'video'),
                                    'duration_seconds': lesson_data.get('duration_seconds', 600),
                                    'is_preview_free': lesson_data.get('is_preview_free', False),
                                    'text_content': (
                                        f'Contenu de la leçon : {lesson_data["title"]}.\n\n'
                                        'Ce contenu pédagogique couvre les concepts essentiels '
                                        'abordés dans cette leçon avec des exemples pratiques.'
                                    ) if lesson_data.get('content_type') == 'text' else '',
                                    'external_embed_url': embed_url,
                                },
                            )
                            if not created and lesson_data.get('content_type') == 'video':
                                Lesson.objects.filter(pk=lesson.pk).update(external_embed_url=embed_url)

                # Question Bank + Quiz
                quiz_data = cd.get('quiz')
                if quiz_data:
                    bank, _ = QuestionBank.objects.get_or_create(
                        title=quiz_data['title'],
                        defaults={'company': None, 'created_by': trainer},
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
                            'time_limit_minutes': 30,
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
        self.stdout.write(self.style.SUCCESS('  seed_b2c_courses completed!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'  New courses created : {course_count}')
        self.stdout.write(f'  Total B2C courses   : {Course.objects.filter(company__isnull=True).count()}')
        self.stdout.write(f'  Categories          : {Category.objects.count()}')
        self.stdout.write(self.style.SUCCESS('=' * 60))
