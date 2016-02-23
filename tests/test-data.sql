insert into Users (user_id, email, name, name_given, name_family, last_login)
values
('user1', 'user1@example.org', 'User One', 'User', 'One', '2015-11-11 11:00:00'),
('user2', 'user2@example.org', 'User Two', 'User', 'Two', '2016-11-11 11:00:00');

insert into Recipes (recipe_id, passhash, name, description, cloneable, stub, args, date_created, date_modified)
values
('AAAAA', '5f4dcc3b5aa765d61d8327deb882cf99', 'Recipe #1', 'First test recipe', 1, 'recipe1', '{"url":"http://example.org/basic-dataset.csv"}', '2015-11-11 11:00:00', '2015-11-11 11:00:00'),
('BBBBB', '5f4dcc3b5aa765d61d8327deb882cf99', 'Recipe #2', null, 0, null, '{}', '2016-11-11 11:00:00', '2016-11-11 11:00:00');
