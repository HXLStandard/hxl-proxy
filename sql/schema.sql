drop table if exists Recipes;
drop table if exists Members;

create table Members (
  member serial primary key,
  hid_id varchar(128) unique,
  hid_name_family varchar(128),
  hid_name_given varchar(128),
  hid_email varchar(256) unique,
  hid_active boolean default true,
  hdx_token varchar(64)
);

create table Recipes (
  recipe serial primary key,
  member bigint not null,
  title varchar(128) not null,
  description text,
  source_url varchar(256) not null,
  schema_url varchar(256),
  params text not null,
  foreign key (member) references Members(member)
);

