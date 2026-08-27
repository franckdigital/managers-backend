class Roles:
    SUPER_ADMIN            = 'super_admin'
    COMPANY_ADMIN          = 'company_admin'
    TRAINING_CENTER_ADMIN  = 'training_center_admin'
    HR                     = 'hr'
    MANAGER                = 'manager'
    EMPLOYEE               = 'employee'
    TRAINER                = 'trainer'
    STUDENT                = 'student'
    PARTNER                = 'partner'

    CHOICES = [
        (SUPER_ADMIN,           'Super Administrateur'),
        (COMPANY_ADMIN,         'Administrateur Entreprise'),
        (TRAINING_CENTER_ADMIN, 'Admin Centre de Formation'),
        (HR,                    'RH'),
        (MANAGER,               'Manager'),
        (EMPLOYEE,              'Employé'),
        (TRAINER,               'Formateur'),
        (STUDENT,               'Apprenant (B2C)'),
        (PARTNER,               'Partenaire vidéo'),
    ]

    B2B_ROLES  = {COMPANY_ADMIN, TRAINING_CENTER_ADMIN, HR, MANAGER, EMPLOYEE, TRAINER}
    STAFF_ROLES = {SUPER_ADMIN, COMPANY_ADMIN, TRAINING_CENTER_ADMIN, HR, MANAGER, TRAINER}
    # Rôles éligibles comme bénéficiaire du partage de revenus d'un cours vidéo
    # (« l'auteur (admin) ou le partenaire », à l'exclusion du Formateur) — utilisé par le
    # sélecteur de l'éditeur de cours.
    REVENUE_SHARE_ELIGIBLE_ROLES = {SUPER_ADMIN, COMPANY_ADMIN, TRAINING_CENTER_ADMIN, PARTNER}
