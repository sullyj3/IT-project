from collections import namedtuple

Artefact = namedtuple("Artefact", ("artefact_id",
                                   "owner",
                                   "name",
                                   "description",
                                   "date_stored",
                                   "stored_with",      # string - "user" or "location"
                                   "stored_with_user",
                                   "stored_at_loc"))


# Needed to display the details of the artefact and the family who owns them
ArtefactUser = namedtuple("ArtefactUser", ("artefact_id",
                                           "owner",
                                           "name",
                                           "description",
                                           "date_stored",
                                           "stored_with",
                                           "stored_with_user",
                                           "stored_at_loc", 
                                           "first_name",
                                           "surname"))


User = namedtuple("User", ("user_id",
                           "first_name",
                           "surname"))

Credentials = namedtuple("Credentials", ("email", "password"))

Register = namedtuple("Register", ("first_name",
                                   "surname",
                                   "family_id",
                                   "email",
                                   "location",
                                   "password"))

ArtefactImage = namedtuple("ArtefactImage", ("image_id",
                                             "artefact_id",
                                             "image_url",
                                             "image_description"))

Tag = namedtuple("Tag", ("tag_id", "name"))

example_artefact = Artefact(None, "Spellbook", 1, "old and spooky", None, 'user', 1, None)
