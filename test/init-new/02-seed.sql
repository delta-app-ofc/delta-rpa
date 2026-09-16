INSERT INTO tb_region (id, name) VALUES
    (1, 'LESTE'),
    (2, 'OESTE'),
    (3, 'SUL'),
    (4, 'NORTE'),
    (5, 'CENTRO');


INSERT INTO tb_day_of_week (id, name) VALUES
    (1, 'SEGUNDA'),
    (2, 'TERÇA'),
    (3, 'QUARTA'),
    (4, 'QUINTA'),
    (5, 'SEXTA'),
    (6, 'SÁBADO'),
    (7, 'DOMINGO');

INSERT INTO tb_habit (id, name, description) VALUES
    (1, 'BANHO LONGO', 'Banhos com duração prolongada'),
    (2, 'LAVAR QUINTAL', 'Lavagem do quintal'),
    (3, 'LAVAR ROUPA', 'Lavagem de roupas'),
    (4, 'REGAR PLANTAS', 'Irrigação das plantas'),
    (5, 'LAVAR CARRO', 'Lavagem de veículos'),
    (6, 'LAVAR LOUÇA', 'Lavagem de louças');


INSERT INTO tb_property_classification (id, name, group_name) VALUES
    (1, 'RESIDENCIAL_NORMAL', 'RESIDENCIAL'),
    (2, 'RESIDENCIAL_SOCIAL', 'RESIDENCIAL'),
    (3, 'RESIDENCIAL_FAVELA', 'RESIDENCIAL'),
    (4, 'RESIDENCIAL_ESPECIAL', 'RESIDENCIAL'),
    (5, 'COMERCIAL_NORMAL_INDUSTRIAL', 'COMERCIAL'),
    (6, 'COMERCIAL_ESPECIAL', 'COMERCIAL'),
    (7, 'COMERCIAL_ENTIDADE_ASSISTENCIA_SOCIAL', 'COMERCIAL'),
    (8, 'PUBLICA_COM_CONTRATO', 'COMERCIAL');
