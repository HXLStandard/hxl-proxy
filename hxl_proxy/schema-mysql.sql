/**
 * Schema to empty and recreate the HXL Proxy database in MySQL.
 *
 * Warning: will delete any existing data.
 * Use this schema only for a fresh installation.
 */
 
drop table if exists Users;
create table Users (
       user_id varchar(128) primary key,
       email varchar(128) not null,
       name varchar(128) not null,
       name_given varchar(64),
       name_family varchar(64),
       last_login datetime not null
) default charset=utf8;

drop table if exists Recipes;
create table Recipes (
       recipe_id char(6) primary key,
       name varchar(128) not null,
       passhash char(32) not null,
       description text,
       cloneable boolean default true,
       stub varchar(64),
       args text not null,
       date_created datetime not null,
       date_modified datetime not null
) default charset=utf8;
