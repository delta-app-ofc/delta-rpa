-- Esquema do banco legado (Primeiro Ano).
-- Reproduz o DDL real do banco de origem, usado apenas no ambiente de testes.

create table tb_user(
    id serial primary key,
    name varchar(100) not null,
    email varchar(100) unique not null,
    password varchar(255) not null check(length(password) >= 8),
    phone varchar(15) unique not null,
    birth_date date not null check(birth_date <= current_date and current_date - birth_date >= 18),
    registration_date date default current_date,
    is_active boolean default true,
    is_admin boolean default false,
    is_manager boolean default false
);

create table tb_last_water_bill(
 id serial primary key,
 user_id int not null references tb_user(id) on delete cascade,
 month date not null CHECK (EXTRACT(DAY FROM month) = 1),
 total_value numeric(10, 2) not null check(total_value >= 0),
 m3_value numeric(10, 2) not null check(m3_value >= 0)
);

create table tb_habit(
    id serial primary key,
    name varchar(30) not null CHECK (upper(name) IN ('BANHO LONGO', 'LAVAR QUINTAL', 'LAVAR ROUPA', 'REGAR PLANTAS', 'LAVAR CARRO', 'LAVAR LOUÇA')),
    description TEXT
);

create table tb_user_habit(
    id serial primary key,
    user_id int not null references tb_user(id) on delete cascade,
    habit_id int not null references tb_habit(id) on delete cascade,
    frequency int not null check(frequency > 0)
);

create table tb_day_of_week(
    id serial primary key,
    name varchar(20) not null check(upper(name) in ('SEGUNDA', 'TERCA', 'QUARTA', 'QUINTA', 'SEXTA', 'SABADO', 'DOMINGO'))
);

create table tb_user_habit_day(
    id serial primary key,
    user_habit_id int not null unique references tb_user_habit(id) on delete cascade,
    day_of_week_id int not null unique references tb_day_of_week(id) on delete cascade
);

create table tb_region(
    id serial primary key,
    name varchar(20) not null
);

create table tb_address(
    id serial primary key,
    region_id int not null references tb_region(id) on delete cascade,
    cep varchar(8) not null check(cep ~ '^[0-9]{8}$'),
    city varchar(60) not null,
    state varchar(30) not null
);

create table tb_property(
    id serial primary key,
    name varchar(100) not null,
    type varchar(20) not null check(upper(type) in ('CASA', 'APARTAMENTO')),
    classification varchar(20) not null CHECK (upper(classification) IN ('RESIDENCIAL', 'COMERCIAL')),
    address_id int not null references tb_address(id) on delete cascade,
    registration_date date not null default current_date
);

create table tb_user_property(
    id serial primary key,
    user_id int not null unique references tb_user(id) on delete cascade,
    property_id int not null unique references tb_property(id) on delete cascade,
    association_date date not null default current_date
);

create table tb_region_rate(
    id serial primary key,
    region_id int not null references tb_region(id) on delete cascade,
    m3_value numeric(10, 2) not null check(m3_value > 0),
    initial_validity date not null default current_date,
    final_validity date
);

create table tb_device (
    id serial primary key,
    device_id int not null,
    property_id int not null references tb_property(id) on delete cascade,
    is_active boolean not null default true,
    installation_date date not null default current_date
);
