from typing import List, Dict
from model import Artefact, ArtefactImage, ArtefactUser
from jinja2 import Template
from flask import render_template

def view_artefacts(artefact_previews: List[Dict], user_id) -> str:
    return render_template('artefacts_template.html', artefact_previews=artefact_previews, user_id=user_id)

def view_artefact(artefact: Artefact, artefact_images: [ArtefactImage], user_id, artefact_loc, owner) -> str:
    return render_template("artefact_view.html", artefact=artefact, artefact_images=artefact_images, user_id=user_id, artefact_loc=artefact_loc, owner=owner)
