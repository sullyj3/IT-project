CREATE TABLE ITProjectTestTable (
    id        serial PRIMARY KEY,
    someText    text NOT NULL
);

INSERT INTO ITProjectTestTable (someText)
VALUES ('example text 1'), ('lorem ipsum');
