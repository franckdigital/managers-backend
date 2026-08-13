class Roles:
    SUPER_ADMIN            = 'super_admin'
    COMPANY_ADMIN          = 'company_admin'
    TRAINING_CENTER_ADMIN  = 'training_center_admin'
    HR                     = 'hr'
    MANAGER                = 'manager'
    EMPLOYEE               = 'employee'
    TRAINER                = 'trainer'
    STUDENT                = 'student'

    CHOICES = [
        (SUPER_ADMIN,           'Super Administrateur'),
        (COMPANY_ADMIN,         'Administrateur Entreprise'),
        (TRAINING_CENTER_ADMIN, 'Admin Centre de Formation'),
        (HR,                    'RH'),
        (MANAGER,               'Manager'),
        (EMPLOYEE,              'Employé'),
        (TRAINER,               'Formateur'),
        (STUDENT,               'Apprenant (B2C)'),
    ]

    B2B_ROLES  = {COMPANY_ADMIN, TRAINING_CENTER_ADMIN, HR, MANAGER, EMPLOYEE, TRAINER}
    STAFF_ROLES = {SUPER_ADMIN, COMPANY_ADMIN, TRAINING_CENTER_ADMIN, HR, MANAGER, TRAINER}
