"""Référentiel des 150 KPI LMS PRO Enterprise (100 Employés + 50 Formateurs).

Chaque entrée définit la METADATA d'un indicateur (code, libellé, unité, objectif).
Les VALEURS sont calculées en direct depuis la base par apps.kpi_pro.engine — ce fichier
ne contient aucune donnée mesurée, uniquement le référentiel (objectifs = cibles de gestion,
pas des données constatées).
"""

# op: 'gte' (>=), 'lte' (<=), 'none' (pas de statut calculé — indicateur informatif)
EMPLOYEE_CATEGORIES = [
    {
        'id': 'A', 'label': "Engagement dans la Formation", 'chart': 'bar',
        'intro': "Mesure l'implication réelle de chaque collaborateur sur la plateforme : connexions, "
                 "durée d'activité, participation aux modules et interaction avec les contenus.",
        'kpis': [
            ('KPI 1', 'inscription_rate', "Taux d'inscription aux formations", '%', 'gte', 90),
            ('KPI 2', 'participation_rate', "Taux de participation", '%', 'gte', 80),
            ('KPI 3', 'weekly_connection_rate', "Taux de connexion hebdomadaire", '%', 'gte', 85),
            ('KPI 4', 'avg_time_per_week_hours', "Temps moyen/plateforme par semaine", 'h', 'gte', 3),
            ('KPI 5', 'avg_courses_followed', "Nombre de formations suivies", 'nb', 'gte', 5),
            ('KPI 6', 'avg_paths_completed', "Nombre de parcours terminés", 'nb', 'gte', 3),
            ('KPI 7', 'completion_rate', "Taux de complétion", '%', 'gte', 80),
            ('KPI 8', 'dropout_rate', "Taux d'abandon", '%', 'lte', 10),
            ('KPI 9', 'avg_sessions_per_week', "Sessions par semaine (moy.)", 'nb', 'gte', 4),
            ('KPI 10', 'recent_activity_rate', "Activité récente (actifs ≤ 7 jours)", '%', 'gte', 85),
        ],
    },
    {
        'id': 'B', 'label': "Assiduité", 'chart': 'donut_heatmap',
        'intro': "Présence aux classes virtuelles, ponctualité, respect des échéances et participation aux ateliers.",
        'kpis': [
            ('KPI 11', 'virtual_attendance_rate', "Présence aux classes virtuelles", '%', 'gte', 90),
            ('KPI 12', 'punctuality_rate', "Ponctualité (sessions à l'heure)", '%', 'gte', 85),
            ('KPI 13', 'justified_absences', "Nombre d'absences justifiées", 'nb', 'lte', 5),
            ('KPI 14', 'late_count', "Nombre de retards", 'nb', 'lte', 3),
            ('KPI 15', 'workshop_participation_rate', "Participation aux ateliers", '%', 'gte', 75),
            ('KPI 16', 'forum_participation_rate', "Participation aux forums", '%', 'gte', 60),
            ('KPI 17', 'practical_work_rate', "Participation aux travaux pratiques", '%', 'gte', 80),
            ('KPI 18', 'video_full_watch_rate', "Temps de visionnage vidéos (complet)", '%', 'gte', 85),
            ('KPI 19', 'document_read_rate', "Temps de lecture documents", '%', 'gte', 70),
            ('KPI 20', 'deadline_respect_rate', "Respect des échéances (devoirs)", '%', 'gte', 90),
        ],
    },
    {
        'id': 'C', 'label': "Performance Pédagogique", 'chart': 'line_histogram',
        'intro': "Scores aux examens, taux de réussite, progression mensuelle et annuelle par département.",
        'kpis': [
            ('KPI 21', 'avg_global_score', "Score moyen global", '%', 'gte', 75),
            ('KPI 22', 'best_score', "Meilleur score individuel", '%', 'none', None),
            ('KPI 23', 'worst_score', "Score le plus faible", '%', 'alert_lte', 40),
            ('KPI 24', 'avg_exams_passed', "Nombre d'examens réussis", 'nb', 'none', None),
            ('KPI 25', 'avg_exams_failed', "Nombre d'examens échoués", 'nb', 'lte', 2),
            ('KPI 26', 'exam_success_rate', "Taux de réussite aux examens", '%', 'gte', 80),
            ('KPI 27', 'avg_attempts', "Nombre de tentatives moyen", 'nb', 'lte', 3),
            ('KPI 28', 'avg_days_to_pass', "Temps moyen pour réussir (jours)", 'j', 'lte', 14),
            ('KPI 29', 'score_trend_mom', "Évolution des notes (mois n vs n-1)", 'pts', 'gte', 0),
            ('KPI 30', 'monthly_progress', "Progression mensuelle", '%/mois', 'gte', 2),
            ('KPI 31', 'yearly_progress', "Progression annuelle", '%/an', 'gte', 15),
            ('KPI 32', 'difficulties_detected', "Difficultés détectées (quiz < 50%)", 'nb', 'lte', 3),
            ('KPI 33', 'hardest_modules', "Modules les plus difficiles", 'liste', 'none', None),
            ('KPI 34', 'best_mastered_modules', "Modules les mieux maîtrisés", 'liste', 'none', None),
            ('KPI 35', 'global_mastery_level', "Niveau global de maîtrise", '%', 'gte', 75),
        ],
    },
    {
        'id': 'D', 'label': "Compétences", 'chart': 'radar_heatmap',
        'intro': "Matrice de compétences par poste, skill gap analysis, suivi des certifications et indice de polyvalence.",
        'kpis': [
            ('KPI 36', 'skills_acquired', "Nombre de compétences acquises", 'nb', 'gte', 8),
            ('KPI 37', 'avg_skill_level_pct', "Niveau moyen de compétence", '%', 'gte', 75),
            ('KPI 38', 'critical_skills_mastered', "Compétences critiques maîtrisées", '%', 'gte', 100),
            ('KPI 39', 'skills_gap_count', "Compétences manquantes (gap)", 'nb', 'lte', 0),
            ('KPI 40', 'skill_gap_global', "Skill Gap global (écart requis/actuel)", '%', 'lte', 15),
            ('KPI 41', 'expired_skills', "Compétences expirées (> 2 ans)", 'nb', 'lte', 0),
            ('KPI 42', 'certified_skills', "Compétences certifiées officiellement", 'nb', 'gte', 3),
            ('KPI 43', 'skill_progress_6m', "Progression des compétences (6 mois)", 'pts', 'gte', 10),
            ('KPI 44', 'job_coverage_rate', "Couverture compétences du poste", '%', 'gte', 100),
            ('KPI 45', 'versatility_index', "Indice de polyvalence", 'nb postes', 'gte', 2),
            ('KPI 46', 'technical_level', "Niveau technique", '%', 'gte', 80),
            ('KPI 47', 'business_level', "Niveau métier", '%', 'gte', 80),
            ('KPI 48', 'behavioral_level', "Niveau comportemental", '%', 'gte', 75),
            ('KPI 49', 'digital_level', "Niveau numérique / digital", '%', 'gte', 70),
            ('KPI 50', 'igc_index', "Indice global de compétences (IGC)", '%', 'gte', 78),
        ],
    },
    {
        'id': 'E', 'label': "Développement Professionnel", 'chart': 'bar',
        'intro': "Suivi des plans de développement individuels, certifications, heures de formation et perspectives d'évolution.",
        'kpis': [
            ('KPI 51', 'dev_objectives_reached', "Objectifs de développement atteints", '%', 'gte', 100),
            ('KPI 52', 'dev_objectives_late', "Objectifs en retard", 'nb', 'lte', 0),
            ('KPI 53', 'pdi_completion', "PDI (Plan Dev. Individuel) réalisé", '%', 'gte', 80),
            ('KPI 54', 'official_certifications', "Certifications officielles obtenues", 'nb', 'gte', 2),
            ('KPI 55', 'training_hours_done', "Heures de formation réalisées", 'h', 'gte', 40),
            ('KPI 56', 'training_hours_left', "Heures de formation restantes", 'h', 'lte', 5),
            ('KPI 57', 'recommended_trainings_done', "Formations recommandées terminées", '%', 'gte', 75),
            ('KPI 58', 'mandatory_trainings_done', "Formations obligatoires terminées", '%', 'gte', 100),
            ('KPI 59', 'promotion_eligibility', "Éligibilité à une promotion", 'Score', 'gte', 80),
            ('KPI 60', 'mobility_readiness', "Préparation à la mobilité interne", '%', 'gte', 70),
        ],
    },
    {
        'id': 'F', 'label': "Performance Opérationnelle", 'chart': 'bar_roi',
        'intro': "Corrélation entre les formations suivies et les résultats métier mesurables : productivité, qualité, ROI.",
        'kpis': [
            ('KPI 61', 'productivity_before', "Productivité avant formation", '%', 'none', None),
            ('KPI 62', 'productivity_after', "Productivité après formation", '%', 'gte_delta', 15),
            ('KPI 63', 'quality_evolution', "Évolution de la qualité (erreurs)", '%', 'gte_delta', 10),
            ('KPI 64', 'error_reduction', "Réduction des erreurs opérationnelles", '%', 'lte', -20),
            ('KPI 65', 'processing_time_reduction', "Temps de traitement (tâches clés)", '%', 'lte', -15),
            ('KPI 66', 'procedure_respect', "Respect des procédures", '%', 'gte', 95),
            ('KPI 67', 'internal_satisfaction', "Satisfaction client interne/externe", '%', 'gte', 85),
            ('KPI 68', 'post_training_incidents', "Nombre d'incidents post-formation", 'nb', 'lte', 0),
            ('KPI 69', 'sla_respect', "Respect des SLA", '%', 'gte', 98),
            ('KPI 70', 'innovations_proposed', "Innovations proposées", 'nb', 'gte', 1),
            ('KPI 71', 'problem_resolution_rate', "Taux de résolution de problèmes", '%', 'gte', 80),
            ('KPI 72', 'business_goals_reached', "Atteinte des objectifs métier", '%', 'gte', 100),
            ('KPI 73', 'strategic_projects_contrib', "Contribution aux projets stratégiques", '%', 'gte', 70),
            ('KPI 74', 'global_performance_score', "Score de performance globale", '%', 'gte', 80),
            ('KPI 75', 'training_roi', "ROI individuel de la formation", '%', 'gte', 500),
        ],
    },
    {
        'id': 'G', 'label': "Soft Skills", 'chart': 'radar',
        'intro': "Compétences comportementales évaluées via les campagnes 360° : leadership, communication, adaptabilité...",
        'kpis': [
            ('KPI 76', 'leadership', "Leadership", '%', 'gte', 70),
            ('KPI 77', 'communication', "Communication", '%', 'gte', 75),
            ('KPI 78', 'teamwork', "Travail d'équipe", '%', 'gte', 80),
            ('KPI 79', 'adaptability', "Adaptabilité", '%', 'gte', 70),
            ('KPI 80', 'time_management', "Gestion du temps", '%', 'gte', 75),
            ('KPI 81', 'stress_management', "Gestion du stress", '%', 'gte', 65),
            ('KPI 82', 'creativity', "Créativité & Innovation", '%', 'gte', 60),
            ('KPI 83', 'initiative', "Esprit d'initiative", '%', 'gte', 70),
            ('KPI 84', 'decision_making', "Prise de décision", '%', 'gte', 72),
            ('KPI 85', 'emotional_intelligence', "Intelligence émotionnelle", '%', 'gte', 70),
        ],
    },
    {
        'id': 'H', 'label': "Évaluation 360°", 'chart': 'radar_multi',
        'intro': "Synthèse des évaluations croisées (auto, manager, RH, pairs) et potentiel de succession.",
        'kpis': [
            ('KPI 86', 'eval_self', "Auto-évaluation", '%', 'none', None),
            ('KPI 87', 'eval_manager', "Évaluation du manager", '%', 'none', None),
            ('KPI 88', 'eval_hr', "Évaluation RH", '%', 'none', None),
            ('KPI 89', 'eval_peers', "Évaluation des collègues", '%', 'none', None),
            ('KPI 90', 'eval_internal_clients', "Évaluation clients internes", '%', 'none', None),
            ('KPI 91', 'eval_trainers', "Évaluation des formateurs", '%', 'none', None),
            ('KPI 92', 'eval_progress', "Progression depuis dernière éval.", 'pts', 'gte', 0),
            ('KPI 93', 'leadership_potential', "Potentiel de leadership", '%', 'gte', 70),
            ('KPI 94', 'succession_index', "Indice de succession", '%', 'gte', 60),
            ('KPI 95', 'global_360_score', "Score global 360°", '%', 'gte', 78),
        ],
    },
    {
        'id': 'I', 'label': "IA & Analytique", 'chart': 'scatter_donut',
        'intro': "Prédictions générées à partir des signaux réels d'activité : risque d'abandon, probabilité d'échec, "
                 "potentiel d'évolution et indice composite de performance d'apprentissage (LPI).",
        'kpis': [
            ('KPI 96', 'dropout_risk_ai', "Risque d'abandon (IA)", '%', 'alert_gte', 65),
            ('KPI 97', 'failure_probability_ai', "Probabilité d'échec (IA)", '%', 'alert_gte', 50),
            ('KPI 98', 'evolution_potential_ai', "Potentiel d'évolution (IA)", '%', 'gte', 70),
            ('KPI 99', 'ai_recommendation', "Recommandation IA de formation", 'liste', 'none', None),
            ('KPI 100', 'lpi_index', "Learning Performance Index (LPI)", '%', 'gte', 80),
        ],
    },
]

TRAINER_CATEGORIES = [
    {
        'id': 'A', 'label': "Préparation Pédagogique", 'chart': 'bar',
        'intro': "Qualité et fraîcheur des supports de cours, structuration pédagogique et diversité des ressources.",
        'kpis': [
            ('KPI F1', 'content_quality', "Qualité des supports pédagogiques", '%', 'gte', 80),
            ('KPI F2', 'content_freshness', "Actualisation des contenus (≤ 6 mois)", '%', 'gte', 100),
            ('KPI F3', 'course_structuring', "Structuration des cours", '%', 'gte', 85),
            ('KPI F4', 'objectives_respect', "Respect des objectifs pédagogiques", '%', 'gte', 100),
            ('KPI F5', 'resource_diversity', "Pertinence et diversité des ressources", '%', 'gte', 80),
        ],
    },
    {
        'id': 'B', 'label': "Animation des Formations", 'chart': 'bar',
        'intro': "Qualité de l'animation en direct : clarté, maîtrise, dynamisme, interactivité et adaptation au public.",
        'kpis': [
            ('KPI F6', 'clarity', "Clarté des explications (notes apprenants)", '%', 'gte', 80),
            ('KPI F7', 'subject_mastery', "Maîtrise du sujet (éval. expert)", '%', 'gte', 90),
            ('KPI F8', 'communication_quality', "Qualité de la communication", '%', 'gte', 80),
            ('KPI F9', 'audience_engagement', "Capacité à captiver l'auditoire", '%', 'gte', 75),
            ('KPI F10', 'time_management', "Gestion du temps (respect planning)", '%', 'gte', 90),
            ('KPI F11', 'question_reactivity_hours', "Gestion des questions (réactivité)", 'min', 'lte', 4),
            ('KPI F12', 'dynamism', "Dynamisme et énergie perçue", '%', 'gte', 78),
            ('KPI F13', 'interactivity', "Interactivité avec les apprenants", '%', 'gte', 70),
            ('KPI F14', 'practical_demo_quality', "Qualité des démonstrations pratiques", '%', 'gte', 85),
            ('KPI F15', 'level_adaptation', "Adaptation au niveau des apprenants", '%', 'gte', 80),
        ],
    },
    {
        'id': 'C', 'label': "Satisfaction des Apprenants", 'chart': 'bar',
        'intro': "Perception des apprenants : satisfaction, recommandation (NPS), disponibilité et fidélisation.",
        'kpis': [
            ('KPI F16', 'avg_satisfaction', "Note moyenne de satisfaction", '%', 'gte', 85),
            ('KPI F17', 'nps', "NPS (Net Promoter Score)", 'pts', 'gte', 30),
            ('KPI F18', 're_enrollment_rate', "Taux de réinscription (cours suivants)", '%', 'gte', 60),
            ('KPI F19', 'positive_comments_rate', "% Commentaires positifs", '%', 'gte', 80),
            ('KPI F20', 'avg_response_time_hours', "Temps moyen réponse aux questions", 'h', 'lte', 4),
            ('KPI F21', 'perceived_availability', "Disponibilité perçue", '%', 'gte', 80),
            ('KPI F22', 'answer_quality', "Qualité des réponses (éval. pairs)", '%', 'gte', 85),
            ('KPI F23', 'personalized_support', "Accompagnement personnalisé", '%', 'gte', 70),
            ('KPI F24', 'global_satisfaction', "Satisfaction globale (Q-sort)", '%', 'gte', 88),
            ('KPI F25', 'learner_loyalty', "Fidélisation des apprenants (retour)", '%', 'gte', 50),
        ],
    },
    {
        'id': 'D', 'label': "Performance & Production de Contenu", 'chart': 'bar',
        'intro': "Résultats mesurables des apprenants (réussite, progression, impact) et volume de contenu produit.",
        'kpis': [
            ('KPI F26', 'learner_success_rate', "Taux de réussite des apprenants", '%', 'gte', 78),
            ('KPI F27', 'learner_progress_pts', "Progression moyenne des apprenants", 'pts', 'gte', 10),
            ('KPI F28', 'completion_rate', "Taux de complétion des formations", '%', 'gte', 80),
            ('KPI F29', 'dropout_rate', "Taux d'abandon", '%', 'lte', 15),
            ('KPI F30', 'eval_difficulty_balance', "Difficulté équilibrée des éval. (score moy.)", '%', 'range', (60, 80)),
            ('KPI F31', 'theory_practice_ratio', "Équilibre théorie / pratique", 'ratio', 'ratio', (40, 60)),
            ('KPI F32', 'learner_certifications', "Certifications obtenues par les apprenants", 'nb', 'gte', 2),
            ('KPI F33', 'pedagogical_goals_reached', "Atteinte des objectifs pédagogiques", '%', 'gte', 90),
            ('KPI F34', 'final_level_reached', "Niveau moyen acquis en fin de formation", '%', 'gte', 75),
            ('KPI F35', 'impact_90d', "Impact mesuré 90j après formation", '%', 'gte', 70),
            ('KPI F36', 'courses_published_year', "Formations publiées dans l'année", 'nb', 'gte', 4),
            ('KPI F37', 'modules_created', "Modules / chapitres créés", 'nb', 'gte', 20),
            ('KPI F38', 'quizzes_created', "Quiz et évaluations créés", 'nb', 'gte', 30),
            ('KPI F39', 'content_update_frequency', "Fréquence de mise à jour des contenus", 'mois', 'lte', 6),
            ('KPI F40', 'content_reuse_rate', "Taux de réutilisation des contenus", '%', 'gte', 40),
        ],
    },
    {
        'id': 'F', 'label': "Innovation & Professionnalisme", 'chart': 'bar',
        'intro': "Usage de l'IA et de la gamification, méthodes pédagogiques innovantes et respect des engagements.",
        'kpis': [
            ('KPI F41', 'ai_usage', "Utilisation de l'IA dans la pédagogie", '%', 'gte', 50),
            ('KPI F42', 'gamification_usage', "Gamification intégrée", '%', 'gte', 60),
            ('KPI F43', 'case_studies_per_course', "Études de cas réels utilisées", 'nb/form.', 'gte', 2),
            ('KPI F44', 'simulations_per_course', "Simulations et exercices pratiques", 'nb/form.', 'gte', 3),
            ('KPI F45', 'pedagogical_innovation', "Innovation des méthodes pédagogiques", 'score', 'gte', 70),
            ('KPI F46', 'deadline_respect', "Respect des délais (livrables)", '%', 'gte', 100),
            ('KPI F47', 'schedule_respect', "Respect du calendrier de formation", '%', 'gte', 95),
            ('KPI F48', 'contractual_respect', "Respect des engagements contractuels", '%', 'gte', 100),
            ('KPI F49', 'hr_collaboration', "Collaboration RH et managers", '%', 'gte', 85),
            ('KPI F50', 'tpi_score', "TPI — Trainer Performance Index", 'pts', 'gte', 80),
        ],
    },
]

EMPLOYEE_KPI_DESCRIPTIONS = {
    # A — Engagement
    'inscription_rate': "Part des employés inscrits à au moins une formation, parmi l'effectif total du périmètre.",
    'participation_rate': "Part des employés ayant ouvert un cours ou une leçon au cours des 30 derniers jours.",
    'weekly_connection_rate': "Part des employés connectés à la plateforme au cours des 7 derniers jours.",
    'avg_time_per_week_hours': "Temps moyen passé sur la plateforme par semaine, sur les 4 dernières semaines.",
    'avg_courses_followed': "Nombre moyen de formations suivies (inscriptions) par employé.",
    'avg_paths_completed': "Nombre moyen de parcours d'apprentissage menés jusqu'à leur terme par employé.",
    'completion_rate': "Part des inscriptions menées jusqu'à 100% de progression, sur l'ensemble des inscriptions du périmètre.",
    'dropout_rate': "Part des inscriptions abandonnées avant la fin, sur l'ensemble des inscriptions du périmètre.",
    'avg_sessions_per_week': "Fréquence moyenne d'interaction avec la plateforme (ouvertures de cours/leçons) par semaine.",
    'recent_activity_rate': "Part des employés ayant une activité de formation enregistrée dans les 7 derniers jours.",
    # B — Assiduité
    'virtual_attendance_rate': "Part des classes virtuelles suivies en intégralité (≥ 70% de la durée programmée).",
    'punctuality_rate': "Part des connexions aux classes virtuelles effectuées dans les 5 minutes suivant l'heure prévue.",
    'justified_absences': "Estimation du nombre moyen d'absences aux classes virtuelles considérées comme justifiées.",
    'late_count': "Nombre moyen de connexions tardives (plus de 5 minutes de retard) aux classes virtuelles.",
    'workshop_participation_rate': "Part des employés actifs sur la plateforme (ateliers/travaux dirigés) dans les 30 derniers jours.",
    'forum_participation_rate': "Part des employés ayant publié au moins un message sur les forums de discussion.",
    'practical_work_rate': "Part des devoirs pratiques (travaux à rendre) soumis ou corrigés parmi ceux assignés.",
    'video_full_watch_rate': "Part des vidéos de formation visionnées à plus de 90% de leur durée.",
    'document_read_rate': "Part des leçons pour lesquelles le support documentaire associé a été consulté.",
    'deadline_respect_rate': "Part des formations terminées avant ou à la date d'échéance fixée.",
    # C — Performance pédagogique
    'avg_global_score': "Score moyen obtenu à l'ensemble des évaluations notées (quiz, examens).",
    'best_score': "Meilleur score individuel obtenu par un employé du périmètre, toutes évaluations confondues.",
    'worst_score': "Score le plus faible enregistré — un score sous le seuil d'alerte signale une difficulté à traiter en priorité.",
    'avg_exams_passed': "Nombre moyen d'évaluations réussies (score ≥ seuil de passage) par employé.",
    'avg_exams_failed': "Nombre moyen d'évaluations échouées par employé.",
    'exam_success_rate': "Part des tentatives d'évaluation soldées par une réussite, sur l'ensemble des tentatives notées.",
    'avg_attempts': "Nombre moyen de tentatives nécessaires par évaluation avant validation.",
    'avg_days_to_pass': "Délai moyen, en jours, entre la première tentative et la tentative réussie sur une même évaluation.",
    'score_trend_mom': "Écart entre le score moyen du dernier mois et celui du mois précédent (tendance à court terme).",
    'monthly_progress': "Évolution du score moyen d'un mois sur l'autre, en points de pourcentage.",
    'yearly_progress': "Évolution du score moyen par rapport à la même période il y a un an.",
    'difficulties_detected': "Nombre de formations dont le score moyen des évaluations est inférieur à 50%.",
    'hardest_modules': "Formations présentant le score moyen le plus faible sur le périmètre — signal des contenus à renforcer.",
    'best_mastered_modules': "Formations présentant le score moyen le plus élevé sur le périmètre.",
    'global_mastery_level': "Niveau de maîtrise global, équivalent au score moyen sur l'ensemble des évaluations.",
    # D — Compétences
    'skills_acquired': "Nombre moyen de compétences enregistrées avec un niveau supérieur à 0, par employé.",
    'avg_skill_level_pct': "Niveau moyen de compétence (échelle 0–5 convertie en pourcentage) sur l'ensemble du référentiel.",
    'critical_skills_mastered': "Part des compétences jugées critiques pour le poste (niveau requis ≥ 4) effectivement maîtrisées.",
    'skills_gap_count': "Nombre moyen de compétences pour lesquelles le niveau requis par une fiche de poste n'est pas atteint.",
    'skill_gap_global': "Écart global, en %, entre le niveau de compétence requis par les fiches de poste et le niveau réel constaté.",
    'expired_skills': "Nombre moyen de compétences dont la dernière évaluation date de plus de 2 ans.",
    'certified_skills': "Nombre moyen de certifications actives (non révoquées) obtenues par employé.",
    'skill_progress_6m': "Progression estimée du niveau de compétence moyen sur les 6 derniers mois.",
    'job_coverage_rate': "Part des compétences critiques du poste effectivement couvertes par l'employé.",
    'versatility_index': "Nombre de fiches de poste différentes pour lesquelles l'employé couvre au moins une compétence acquise.",
    'technical_level': "Niveau moyen sur les compétences classées « Outils & Technologies » du référentiel.",
    'business_level': "Niveau moyen sur les compétences classées « Techniques Métier » du référentiel.",
    'behavioral_level': "Niveau moyen sur les compétences comportementales (management, communication, transversales).",
    'digital_level': "Niveau moyen sur les compétences numériques et outils digitaux.",
    'igc_index': "Indice composite combinant niveau de compétence moyen, maîtrise des compétences critiques et écart de compétences.",
    # E — Développement professionnel
    'dev_objectives_reached': "Part des objectifs de développement individuel marqués comme atteints.",
    'dev_objectives_late': "Nombre moyen d'objectifs de développement dont la date cible est dépassée sans être atteints.",
    'pdi_completion': "Part des plans de développement individuel (PDI) clôturés avec le statut « terminé ».",
    'official_certifications': "Nombre moyen de certifications officielles actives obtenues par employé.",
    'training_hours_done': "Nombre d'heures de formation effectivement suivies sur la plateforme (30 derniers jours).",
    'training_hours_left': "Écart entre l'objectif annuel de 40h de formation et les heures déjà réalisées.",
    'recommended_trainings_done': "Part des formations recommandées par l'IA qui ont été suivies jusqu'à leur terme.",
    'mandatory_trainings_done': "Part des formations obligatoires (affectées par l'entreprise) menées à terme.",
    'promotion_eligibility': "Score composite (scores, compétences, objectifs atteints) utilisé comme indicateur d'éligibilité à une promotion.",
    'mobility_readiness': "Part des fiches de poste de l'entreprise pour lesquelles l'employé couvre déjà les compétences requises.",
    # F — Performance opérationnelle
    'productivity_before': "Score moyen obtenu sur la première moitié des évaluations suivies (référence avant montée en compétence).",
    'productivity_after': "Score moyen obtenu sur la deuxième moitié des évaluations suivies (après montée en compétence).",
    'quality_evolution': "Écart entre la productivité après et avant formation — un écart positif traduit une amélioration réelle.",
    'error_reduction': "Estimation de la réduction des erreurs opérationnelles, dérivée de l'évolution de la qualité mesurée.",
    'processing_time_reduction': "Estimation de la réduction du temps de traitement des tâches clés, dérivée de la tendance des scores.",
    'procedure_respect': "Part des formations terminées dans les délais impartis — utilisé comme proxy du respect des procédures.",
    'internal_satisfaction': "Satisfaction moyenne exprimée dans les avis (5 étoiles) laissés par l'employé sur les formations suivies.",
    'post_training_incidents': "Nombre moyen d'alertes de difficulté d'apprentissage enregistrées pour l'employé.",
    'sla_respect': "Estimation du respect des délais contractuels, basée sur le respect des échéances de formation.",
    'innovations_proposed': "Nombre moyen de contributions marquées comme « solution » sur les forums de la communauté.",
    'problem_resolution_rate': "Part des évaluations réussies parmi l'ensemble des tentatives — proxy de la capacité à résoudre les difficultés.",
    'business_goals_reached': "Part des objectifs de développement individuel atteints — utilisé comme proxy des objectifs métier.",
    'strategic_projects_contrib': "Estimation de la contribution aux projets stratégiques, dérivée de la polyvalence de compétences.",
    'global_performance_score': "Indice composite combinant score moyen, taux de complétion et niveau de compétence.",
    'training_roi': "Retour sur investissement estimé de la formation, basé sur le taux de complétion et le score moyen obtenus.",
    # G — Soft skills (issus des campagnes d'évaluation 360°)
    'leadership': "Capacité à mobiliser et orienter une équipe, évaluée lors des campagnes 360°.",
    'communication': "Clarté et efficacité de la communication, évaluée lors des campagnes 360°.",
    'teamwork': "Qualité de la coopération avec les collègues, évaluée lors des campagnes 360°.",
    'adaptability': "Capacité à s'adapter au changement, évaluée lors des campagnes 360°.",
    'time_management': "Respect des délais et organisation du temps de travail, évalués lors des campagnes 360° (ou à défaut, respect des échéances de formation).",
    'stress_management': "Capacité à gérer la pression, estimée à partir de l'adaptabilité et du respect des délais.",
    'creativity': "Qualité et originalité du travail produit, évaluées lors des campagnes 360°.",
    'initiative': "Prise d'initiative dans le travail quotidien, évaluée lors des campagnes 360°.",
    'decision_making': "Capacité à prendre des décisions pertinentes, estimée à partir de l'orientation client et des compétences métier.",
    'emotional_intelligence': "Capacité relationnelle et de coopération, estimée à partir de la communication et du travail d'équipe.",
    # H — Évaluation 360°
    'eval_self': "Score moyen de l'auto-évaluation soumise par l'employé lors des campagnes 360°.",
    'eval_manager': "Score moyen attribué par le manager lors des campagnes d'évaluation 360°.",
    'eval_hr': "Score moyen attribué par les RH lors des campagnes d'évaluation 360°.",
    'eval_peers': "Score moyen attribué par les collègues (évaluation par les pairs) lors des campagnes 360°.",
    'eval_internal_clients': "Score attribué par les clients internes — non disponible : aucun type d'évaluateur dédié dans le référentiel actuel.",
    'eval_trainers': "Score moyen de l'évaluation finale consolidée lors des campagnes 360°.",
    'eval_progress': "Écart entre le score 360° actuel et celui enregistré il y a plus d'un an.",
    'leadership_potential': "Potentiel de leadership estimé à partir des compétences métier et de la prise d'initiative.",
    'succession_index': "Indice de préparation à la succession, combinant score 360° global et polyvalence de compétences.",
    'global_360_score': "Score moyen consolidé de l'ensemble des sources d'évaluation 360° disponibles.",
    # I — IA & Analytique
    'dropout_risk_ai': "Score de risque de décrochage, calculé à partir de la participation, du taux de complétion et de l'inactivité récente.",
    'failure_probability_ai': "Probabilité d'échec aux évaluations, calculée à partir du taux de réussite et du score moyen.",
    'evolution_potential_ai': "Potentiel d'évolution estimé, combinant indice de compétences, score 360° et score moyen aux évaluations.",
    'ai_recommendation': "Formation la mieux notée par le moteur de recommandation IA pour cet employé, parmi celles non encore suivies.",
    'lpi_index': "Learning Performance Index — indice composite pondéré (engagement, compétence, performance, assiduité, résultats, certification).",
}

TRAINER_KPI_DESCRIPTIONS = {
    # A — Préparation pédagogique
    'content_quality': "Part des formations disposant d'une image de présentation soignée (proxy de la qualité des supports).",
    'content_freshness': "Part des formations mises à jour au cours des 6 derniers mois.",
    'course_structuring': "Part des formations comportant au moins deux sections structurées.",
    'objectives_respect': "Part des formations dont les objectifs pédagogiques (« ce que vous allez apprendre ») sont renseignés.",
    'resource_diversity': "Part des formations proposant au moins une ressource complémentaire téléchargeable.",
    # B — Animation
    'clarity': "Clarté perçue des explications — dérivée de la note moyenne des avis, ou des notations directes des apprenants.",
    'subject_mastery': "Maîtrise du sujet — dérivée du taux de réussite des apprenants aux évaluations du formateur.",
    'communication_quality': "Qualité de la communication perçue par les apprenants.",
    'audience_engagement': "Capacité à capter l'attention — dérivée du taux de complétion des formations du formateur.",
    'time_management': "Respect du planning des sessions en direct (durée effective vs durée programmée).",
    'dynamism': "Dynamisme et énergie perçus par les apprenants.",
    'interactivity': "Niveau d'interactivité avec les apprenants — dérivé de l'activité sur les forums liés aux formations.",
    'practical_demo_quality': "Qualité perçue des démonstrations pratiques.",
    'level_adaptation': "Capacité à adapter le contenu au niveau des apprenants — dérivée du taux de rétention (inverse du décrochage).",
    # C — Satisfaction
    'avg_satisfaction': "Note moyenne de satisfaction sur les avis laissés sur les formations du formateur.",
    'nps': "Net Promoter Score — écart entre la part de notes 5 étoiles (promoteurs) et de notes ≤ 3 (détracteurs).",
    're_enrollment_rate': "Part des apprenants ayant suivi plus d'une formation de ce formateur (fidélisation).",
    'positive_comments_rate': "Part des avis notés 4 étoiles ou plus.",
    'avg_response_time_hours': "Délai moyen de réponse aux questions posées lors des classes virtuelles.",
    'perceived_availability': "Disponibilité perçue, estimée à partir de la rapidité de réponse aux questions.",
    'answer_quality': "Part des questions posées en classe virtuelle ayant reçu une réponse.",
    'personalized_support': "Niveau d'accompagnement individualisé, estimé à partir du volume de réponses apportées.",
    'global_satisfaction': "Satisfaction globale, équivalente à la note moyenne des avis.",
    'learner_loyalty': "Part des apprenants revenus suivre plusieurs formations du même formateur.",
    # D — Performance & production de contenu
    'learner_success_rate': "Part des tentatives d'évaluation réussies sur les formations du formateur.",
    'learner_progress_pts': "Progression moyenne des apprenants au-delà du seuil de passage (60%).",
    'completion_rate': "Part des inscriptions menées à 100% sur les formations du formateur.",
    'dropout_rate': "Part des inscriptions abandonnées sur les formations du formateur.",
    'eval_difficulty_balance': "Part des scores obtenus se situant dans une plage de difficulté équilibrée (60–80%).",
    'theory_practice_ratio': "Répartition entre évaluations théoriques (quiz) et pratiques (devoirs) sur les formations du formateur.",
    'learner_certifications': "Nombre moyen de certificats délivrés par formation.",
    'pedagogical_goals_reached': "Part des formations dont les objectifs pédagogiques annoncés sont renseignés.",
    'final_level_reached': "Niveau moyen atteint par les apprenants aux évaluations notées.",
    'impact_90d': "Impact mesuré après la formation — approximé par le taux de complétion global.",
    'courses_published_year': "Nombre de formations publiées par le formateur au cours de l'année en cours.",
    'modules_created': "Nombre total de chapitres créés dans les formations du formateur.",
    'quizzes_created': "Nombre total de quiz et devoirs créés dans les formations du formateur.",
    'content_update_frequency': "Délai moyen, en mois, depuis la dernière mise à jour des formations du formateur.",
    'content_reuse_rate': "Estimation du taux de réutilisation des contenus, basée sur la structuration des sections.",
    # F-G — Innovation & professionnalisme
    'ai_usage': "Utilisation d'outils de génération de quiz par IA sur les formations du formateur.",
    'gamification_usage': "Part des formations associées à un badge de récompense (gamification).",
    'case_studies_per_course': "Nombre moyen de devoirs pratiques (études de cas) par formation.",
    'simulations_per_course': "Nombre moyen de quiz/simulations par formation.",
    'pedagogical_innovation': "Indice composite d'innovation pédagogique (usage de l'IA, gamification, interactivité).",
    'deadline_respect': "Part des formations effectivement publiées (livrées) parmi celles créées.",
    'schedule_respect': "Part des classes virtuelles dont la session s'est déroulée sans dépassement du calendrier prévu.",
    'contractual_respect': "Respect des engagements contractuels — non tracé finement, valeur de référence par défaut.",
    'hr_collaboration': "Niveau de collaboration avec les RH/managers, estimé à partir du renseignement des objectifs pédagogiques.",
    'tpi_score': "Trainer Performance Index — score composite pondéré des 7 dimensions clés de performance du formateur.",
}

# Sous-ensemble des 50 KPI Formateurs directement perceptibles par un apprenant
# (les autres — formations publiées, quiz créés, usage IA, respect des délais
# contractuels… — sont objectifs et déjà calculés depuis les données réelles de
# cours/sessions ; on ne demande pas à un apprenant de "noter" un nombre de quiz créés).
RATABLE_TRAINER_KPIS = [
    ('content_quality', "Qualité des supports pédagogiques"),
    ('course_structuring', "Structuration du cours"),
    ('objectives_respect', "Le cours a respecté ses objectifs annoncés"),
    ('resource_diversity', "Diversité et pertinence des ressources"),
    ('clarity', "Clarté des explications"),
    ('subject_mastery', "Maîtrise du sujet"),
    ('communication_quality', "Qualité de la communication"),
    ('audience_engagement', "Capacité à capter l'attention"),
    ('time_management', "Gestion du temps (respect du planning)"),
    ('dynamism', "Dynamisme et énergie"),
    ('interactivity', "Interactivité avec les apprenants"),
    ('practical_demo_quality', "Qualité des démonstrations pratiques"),
    ('level_adaptation', "Adaptation à votre niveau"),
    ('avg_satisfaction', "Satisfaction générale"),
    ('perceived_availability', "Disponibilité perçue"),
    ('answer_quality', "Qualité des réponses apportées"),
    ('personalized_support', "Accompagnement personnalisé"),
    ('global_satisfaction', "Satisfaction globale"),
    ('eval_difficulty_balance', "Niveau de difficulté des évaluations approprié"),
    ('theory_practice_ratio', "Bon équilibre théorie / pratique"),
    ('pedagogical_innovation', "Méthodes pédagogiques innovantes"),
]

TPI_WEIGHTS = [
    ('avg_satisfaction', "Satisfaction des apprenants", 0.25),
    ('learner_success_rate', "Réussite des apprenants", 0.20),
    ('completion_rate', "Taux de complétion", 0.15),
    ('content_quality', "Qualité des contenus", 0.15),
    ('interactivity', "Engagement des apprenants", 0.10),
    ('pedagogical_innovation', "Innovation pédagogique", 0.10),
    ('deadline_respect', "Respect des délais", 0.05),
]

LPI_WEIGHTS = [
    ('engagement_score', "Engagement", 0.20),
    ('skill_score', "Compétence", 0.20),
    ('performance_score', "Performance", 0.20),
    ('attendance_score', "Assiduité", 0.15),
    ('results_score', "Résultats", 0.15),
    ('certification_score', "Certification", 0.10),
]

BUDGET_BREAKDOWN_SHARES = [
    ('Main d\'œuvre Formateurs', 0.35),
    ('Contenus externes', 0.22),
    ('Hébergement & Licences', 0.18),
    ('Certifications', 0.12),
    ('Classes Virtuelles', 0.08),
    ('Animation & Ateliers', 0.05),
]


def status_for(op, target, value):
    """Compute a traffic-light status ('green'|'orange'|'red'|None) for a KPI value vs its objective."""
    if value is None or op == 'none':
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    if op == 'gte':
        target = float(target)
        if value >= target:
            return 'green'
        if value >= target * 0.8:
            return 'orange'
        return 'red'
    if op == 'lte':
        target = float(target)
        if value <= target:
            return 'green'
        if value <= target * 1.2:
            return 'orange'
        return 'red'
    if op == 'alert_lte':
        target = float(target)
        return 'red' if value < target else 'green'
    if op == 'alert_gte':
        target = float(target)
        if value > target:
            return 'red'
        if value > target * 0.7:
            return 'orange'
        return 'green'
    if op == 'gte_delta':
        # value already expressed as the delta (points gained)
        target = float(target)
        if value >= target:
            return 'green'
        if value >= target * 0.5:
            return 'orange'
        return 'red'
    if op == 'range':
        lo, hi = target
        return 'green' if lo <= value <= hi else 'orange'
    if op == 'ratio':
        # target is (theory, practice) reference split — informative only
        return None
    return None


def build_kpi_rows(categories, values, descriptions=None):
    """Merge a catalog (EMPLOYEE_CATEGORIES or TRAINER_CATEGORIES) with a computed `values` dict,
    returning categories annotated with value/status/description for each KPI — ready for the frontend tables."""
    descriptions = descriptions or {}
    result = []
    for cat in categories:
        rows = []
        for code, key, label, unit, op, target in cat['kpis']:
            value = values.get(key)
            rows.append({
                'code': code, 'key': key, 'label': label, 'unit': unit,
                'objective': _format_objective(op, target, unit),
                'value': value,
                'status': status_for(op, target, value),
                'description': descriptions.get(key, ''),
            })
        result.append({
            'id': cat['id'], 'label': cat['label'], 'chart': cat['chart'],
            'intro': cat.get('intro', ''), 'kpis': rows,
        })
    return result


def _format_objective(op, target, unit):
    if op == 'none' or target is None:
        return '—'
    if op == 'gte':
        return f'≥ {target}{"%" if unit == "%" else ""}'.replace('%%', '%') if unit == '%' else f'≥ {target}'
    if op == 'lte':
        return f'≤ {target}{"%" if unit == "%" else ""}'.replace('%%', '%') if unit == '%' else f'≤ {target}'
    if op == 'alert_lte':
        return f'Alerte < {target}'
    if op == 'alert_gte':
        return f'Alerte > {target}%'
    if op == 'gte_delta':
        return f'+{target} pts'
    if op == 'range':
        lo, hi = target
        return f'{lo}–{hi}%'
    if op == 'ratio':
        lo, hi = target
        return f'{lo}/{hi}'
    return '—'
