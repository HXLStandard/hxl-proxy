/**
 * Schema to empty and recreate the HXL Proxy database in MySQL.
 *
 * Warning: will delete any existing data.
 * Use this schema only for a fresh installation.
 */

/**
 * Consider uncommenting locally the line below.
 * CREATE DATABASE IF NOT EXISTS hxl;
*/

DROP TABLE IF EXISTS Users;
CREATE TABLE Users (
       user_id VARCHAR(128) PRIMARY KEY,
       email VARCHAR(128) NOT NULL,
       name VARCHAR(128) NOT NULL,
       name_given VARCHAR(64),
       name_family VARCHAR(64),
       last_login DATETIME NOT NULL
) DEFAULT charset=utf8;

DROP TABLE IF EXISTS Recipes;
CREATE TABLE Recipes (
       recipe_id CHAR(6) PRIMARY KEY,
       name VARCHAR(128) NOT NULL,
       passhash char(32) NOT NULL,
       description TEXT,
       cloneable BOOLEAN DEFAULT true,
       stub VARCHAR(64),
       args TEXT NOT NULL,
       date_created DATETIME NOT NULL,
       date_modified DATETIME NOT NULL
) DEFAULT charset=utf8;
