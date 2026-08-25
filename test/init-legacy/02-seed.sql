INSERT INTO tb_region (id, name) VALUES
    (1, 'LESTE'),
    (2, 'OESTE'),
    (3, 'SUL'),
    (4, 'NORTE'),
    (5, 'CENTRO');


INSERT INTO tb_address (id, region_id, cep, city, state) VALUES
    (1, 1, '01001000', 'sao paulo', 'sp'),
    (2, 2, '80010000', 'curitiba', 'pr'),
    (3, 3, '90010000', 'porto alegre', 'rs'),
    (4, 4, '70040000', 'brasilia', 'df');


INSERT INTO tb_user (
    id,
    name,
    email,
    password,
    phone,
    birth_date,
    registration_date,
    is_active,
    is_admin,
    is_manager
) VALUES
    (
        1,
        'Ana Silva',
        'ana.silva@example.com',
        'SENHAFORTE101',
        '11987654001',
        '1990-05-10',
        '2026-01-10',
        TRUE,
        FALSE,
        FALSE
    ),
    (
        2,
        'Joao Menor',
        'joao.menor@example.com',
        'SENHAFORTE102',
        '11987654002',
        '2015-01-01',
        '2026-01-11',
        TRUE,
        FALSE,
        FALSE
    ),
    (
        3,
        'Carlos Duplicado',
        'carlos.duplicado@example.com',
        'SENHAFORTE103',
        '11987654003',
        '1985-03-20',
        '2026-01-12',
        TRUE,
        FALSE,
        FALSE
    ),
    (
        4,
        'Maria Duplicada',
        'maria.duplicada@example.com',
        'SENHAFORTE104',
        '11987654004',
        '1988-07-15',
        '2026-01-13',
        TRUE,
        FALSE,
        FALSE
    ),
    (
        5,
        'Pedro Santos',
        'pedro.santos@example.com',
        'SENHAFORTE105',
        '11987654005',
        '1978-11-23',
        '2026-01-14',
        TRUE,
        TRUE,
        FALSE
    );


INSERT INTO tb_property (
    id,
    name,
    type,
    classification,
    address_id,
    registration_date
) VALUES
    (
        1,
        'casa da ana',
        'CASA',
        'residencial',
        1,
        '2026-01-10'
    ),
    (
        2,
        'apartamento central',
        'APARTAMENTO',
        'residencial',
        1,
        '2026-01-11'
    ),
    (
        3,
        'imovel invalido',
        'SOBRADO',
        'residencial',
        2,
        '2026-01-12'
    ),
    (
        4,
        'casa comercial',
        'CASA',
        'comercial',
        3,
        '2026-01-13'
    );


INSERT INTO tb_user_property (
    id,
    user_id,
    property_id,
    association_date
) VALUES
    (1, 1, 1, '2026-01-10'),
    (2, 3, 2, '2026-01-11'),
    (3, 5, 4, '2026-01-12');


INSERT INTO tb_habit (
    id,
    name,
    description
) VALUES
    (1, 'BANHO LONGO', 'Banhos com duração prolongada'),
    (2, 'LAVAR QUINTAL', 'Lavagem do quintal'),
    (3, 'LAVAR ROUPA', 'Lavagem de roupas'),
    (4, 'REGAR PLANTAS', 'Irrigação das plantas'),
    (5, 'LAVAR CARRO', 'Lavagem de veículos'),
    (6, 'LAVAR LOUÇA', 'Lavagem de louças');


INSERT INTO tb_user_habit (
    id,
    user_id,
    habit_id,
    frequency
) VALUES
    (1, 1, 1, 5),
    (2, 3, 2, 2),
    (3, 5, 5, 1);


INSERT INTO tb_day_of_week (
    id,
    name
) VALUES
    (1, 'SEGUNDA'),
    (2, 'TERÇA'),
    (3, 'QUARTA'),
    (4, 'QUINTA'),
    (5, 'SEXTA'),
    (6, 'SÁBADO'),
    (7, 'DOMINGO');


INSERT INTO tb_user_habit_day (
    id,
    user_habit_id,
    day_of_week_id
) VALUES
    (1, 1, 1),
    (2, 1, 3),
    (3, 2, 6),
    (4, 3, 7);


INSERT INTO tb_last_water_bill (
    id,
    user_id,
    month,
    total_value,
    m3_value
) VALUES
    (1, 1, '2026-07-01', 85.50, 18.30),
    (2, 3, '2026-07-15', 92.40, 20.10),
    (3, 5, '2026-08-01', 110.75, 25.50);