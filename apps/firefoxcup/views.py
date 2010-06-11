import httplib
import json
import jingo

from django.http import HttpResponse
from django.utils.http import urlencode
from django.views.decorators.csrf import csrf_exempt

from addons.models import Persona
from . import tags, generic_persona, teams as teams_config
from .models import Stats
from .twitter import search


def index(request):
    tweets = search(lang=request.LANG, limit=15)

    persona_ids = [t['persona_id'] for t in teams_config]
    persona_ids.append(generic_persona)
    personas = {}
    for persona in Persona.objects.filter(persona_id__in=persona_ids):
        personas[persona.persona_id] = persona

    stats = {}
    for stat in Stats.objects.all():
        stats.setdefault(stat.persona_id, []).append(str(stat.popularity))

    teams = []
    for t in teams_config:
        id = t['persona_id']
        if id not in personas:
            continue

        t['persona'] = personas[id]

        if id in stats:
            # we need at least 2 data points
            while len(stats[id]) < 2:
                stats[id].insert(0, '0')
            t['stats'] = ','.join(stats[id])
        else:
            t['stats'] = '0,0'
        teams.append(t)

    # sort by most fans
    teams.sort(key=lambda x: x['persona'].popularity, reverse=True)

    return jingo.render(request, 'firefoxcup/index.html', {
        'tweets': tweets,
        'teams': teams,
        'personas': personas.values(),
    })

@csrf_exempt
def signup(request):
    conn = httplib.HTTPConnection("basket.mozilla.com")
    headers = {"Content-type": "application/x-www-form-urlencoded",
               "Accept": "text-plain"}
    conn.request("POST", "/subscriptions/subscribe/", request.raw_post_data, headers)
    resp = conn.getresponse()
    conn.close()
    return HttpResponse(str(resp.status))
