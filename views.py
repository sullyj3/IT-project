from typing import List
from model import Artefact
from jinja2 import Template

def view_artefacts(artefacts: List[Artefact]) -> str:
    with open('views/artefacts_template.html', encoding='utf8') as f:
        template = Template(f.read())
    return template.render(artefacts=artefacts)
