create table tb_region(
    id serial primary key,
    name varchar(20) not null
);

create table tb_address(
    id serial primary key,
    region_id int references tb_region(id),
    cep varchar(8) not null,
    city varchar(60) not null,
    state varchar(30) not null
);

create table tb_user(
    id serial primary key,
    name varchar(100) not null,
    email varchar(100) unique not null,
    password varchar(255) not null,
    phone varchar(15) unique not null,
    birth_date date not null,
    registration_date date,
    is_active boolean default true,
    is_admin boolean default false,
    is_manager boolean default false
);

alter table tb_user
alter column registration_date set default current_date;

create table tb_device(
    id serial primary key,
    user_id int references tb_user(id),
    name varchar(100) not null,
    type varchar(50) not null,
    registration_date date not null default current_date
);

create table tb_region_rate(
    id serial primary key,
    region_id int references tb_region(id),
    rate numeric(10, 2) not null check(rate >= 0)
);

create table property(
    id serial primary key,
    name varchar(100) not null,
    type varchar(20) not null,
    classification varchar(20) not null,
    address_id int references tb_address(id),
    registration_date date not null default current_date
);
alter table property rename to tb_property;

create table tb_user_property(
    id serial primary key,
    user_id int references tb_user(id),
    property_id int references tb_property(id),
    association_date date not null default current_date
);

create table tb_habit(
    id serial primary key,
    name varchar(30) not null,
    description TEXT
);

create table tb_user_habit(
    id serial primary key,
    user_id int references tb_user(id),
    habit_id int references tb_habit(id),
    frequency int not null check(frequency > 0)
);

create table tb_day_of_week(
    id serial primary key,
    name varchar(20) not null
    
);

create table tb_user_habit_day(
    id serial primary key,
    user_habit_id int references tb_user_habit(id),
    day_of_week_id int references tb_day_of_week(id)
);

create table tb_last_water_bill(
    id serial primary key,
    user_id int references tb_user(id),
    month varchar(20) not null,
    total_value numeric(10, 2) not null,
    m3_value numeric(10, 2) not null
);