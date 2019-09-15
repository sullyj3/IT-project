BEGIN;

CREATE TABLE Family (
    family_id   serial PRIMARY KEY,
    name        varchar(100) NOT NULL
);

CREATE TYPE stored_with AS ENUM('user', 'location');

CREATE TABLE "User" (
    user_id     serial PRIMARY KEY,
    name        varchar(100)                         NOT NULL,
    email		    varchar(50)                          NOT NULL,
    password    char(60)                             NOT NULL,
    location    varchar(200),
    family_id   integer REFERENCES Family(family_id) NOT NULL
);

CREATE TABLE Artefact (
    artefact_id serial PRIMARY KEY,
    owner            integer REFERENCES "User"(user_id) NOT NULL,
    name             varchar(100)                       NOT NULL,
    description      text,
    date_stored      timestamp,
    stored_with      stored_with,
    stored_with_user integer REFERENCES "User"(user_id),
    stored_at_loc    varchar(200)
);

CREATE TABLE ArtefactImage (
    image_id          serial PRIMARY KEY,
    artefact_id       integer REFERENCES Artefact(artefact_id) NOT NULL,
    image_url         varchar(1024)                            NOT NULL,
    image_description varchar(500)
);

CREATE TABLE UserCannotView (
    user_id           integer REFERENCES "User"(user_id)       NOT NULL,
    artefact_id       integer REFERENCES Artefact(artefact_id) NOT NULL,
    date_access_given timestamp                                NOT NULL,
    PRIMARY KEY(user_id, artefact_id)
);

CREATE TABLE Tag (
    tag_id serial PRIMARY KEY,
    name   varchar(50) NOT NULL
);

CREATE TABLE ArtefactTaggedWith (
    artefact_id integer REFERENCES Artefact(artefact_id),
    tag_id      integer REFERENCES Tag(tag_id),
    PRIMARY KEY (artefact_id, tag_id)
);

INSERT INTO Family (name) VALUES ('Sully');

INSERT INTO "User" (name, email, password, family_id)
VALUES ('James', 'sullyj3@gmail.com', 'passwordhashhere', 1);

-- Make this a dry run
ROLLBACK;
