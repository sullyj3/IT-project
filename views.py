from typing import List, Dict
from model import Artefact, ArtefactImage, ArtefactUser
from jinja2 import Template
from flask import render_template

def view_artefacts(artefact_previews: List[Dict]) -> str:
    return render_template('artefacts_template.html', artefact_previews=artefact_previews)

def view_artefact(artefact: Artefact, artefact_images: [ArtefactImage]) -> str:
    with open('views/artefact_view.html', encoding='utf8') as f:
        template = Template(f.read())
    return template.render(artefact=artefact,
                           artefact_images=artefact_images)
