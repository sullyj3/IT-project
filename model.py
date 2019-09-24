from collections import namedtuple

Artefact = namedtuple("Artefact", ("artefact_id",
                                   "name",
                                   "owner",
                                   "description",
                                   "date_stored",
                                   "stored_with",
                                   "stored_with_user",
                                   "stored_at_loc"))

Credentials = namedtuple("Credentials", ("email", "password"))

Register = namedtuple("Register", ("first_name",
                                   "surname",
                                   "family_id",
                                   "email",
                                   "location",
                                   "password"))

example_artefact = Artefact(None, "Spellbook", 1, "old and spooky", None, 'user', 1, None)
