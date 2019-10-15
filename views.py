from typing import List
from model import Artefact, ArtefactImage
from jinja2 import Template
from flask import render_template

def view_artefacts(artefacts: List[Artefact]) -> str:
    return render_template('artefacts_template.html', artefacts=artefacts)

def view_artefact(artefact: Artefact, artefact_images: [ArtefactImage]) -> str:
    with open('views/artefact.html', encoding='utf8') as f:
        template = Template(f.read())
    return template.render(artefact=artefact,
                           artefact_images=artefact_images)
