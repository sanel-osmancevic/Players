# Pozadinska arhiva: pri svakom osvežavanju beleži SVE igrače u ponudi (i one koji nisu preporučeni, i one koje model
# ne prepoznaje), sa svim granicama svih kladionica i stanjem modela u tom trenutku. Ne prikazuje se; služi za učenje.
#   arhiva/kolo{K}_ponuda.jsonl  — jedan red po igraču i snimku: kvote po kladionicama (Maxbet sa svim alternativnim
#                                  granicama i stepenicima), tržište, projekcije, minuti, status, uloga, sastav, sudije, šanse
#   arhiva/kolo{K}_rezultati.json — stvarni učinak posle utakmica (puni zapisnik), upisuje arhiva_rezultati()
# Kasnije se spajaju po (igrač, tim, utakmica) za proveru i podešavanje modela na mnogo većem uzorku.
import json, os, sys, datetime
from pomocno import citaj, pisi
os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.makedirs('arhiva', exist_ok=True)

POLJA_IG = ['api', 'poz', 'tim', 'protiv', 'teren', 'utakmica', 'termin', 'status', 'napomena', 'utakmice', 'minuti', 'minuti_proj',
            'minuti_sd', 'minuti_trend', 'minuti_pre_sastava', 'starter', 'starter_status', 'nemir_tim', 'tempo', 'zona_faktor',
            'faktor_utakmica', 'total_kladionica', 'sansa_pobede', 'rizik_rasturi', 'faul_40', 'faul_4plus', 'sudije', 'sudije_faul',
            'sastav_zbog', 'povratak', 'rizik_uloge', 'veca_uloga', 'uloga_zbog', 'sutevi_promena', 'iskljuci',
            'pts_proj', 'pts_sd', 'reb_proj', 'reb_sd', 'ast_proj', 'ast_sd', 'pts_proj_sirovo', 'reb_proj_sirovo', 'ast_proj_sirovo',
            'pts_sve', 'reb_sve', 'ast_sve']
POLJA_KV = ['linija', 'kvota_vise', 'kvota_manje', 'trz_vise', 'trz_medijana', 'trz_raskorak', 'trz_knjige', 'trz_knjige_nez',
            'trz_kretanje', 'mb_odstupanje', 'ls_vise', 'ls_n', 'tez_m', 'tez_h', 'tez_t']

def zabelezi(t_snap=None):
    import market as M
    t = t_snap or datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    ig = citaj('igraci2.json')
    kolo = max(int(r.get('kolo') or 0) for r in ig) or None
    kv = citaj('kvote.json') if os.path.exists('kvote.json') else []
    KV = {}
    for x in kv: KV.setdefault(x['igrac'], []).append({k: x.get(k) for k in ['kategorija'] + POLJA_KV})
    raw = citaj('mb_pet_raw2.json') if os.path.exists('mb_pet_raw2.json') else {}
    # sve kladionice, poslednji snimak, po (prezime, tim); plus imena koja model ne prepoznaje
    knj = {b: h[-1][1] for b, h in M.HIST.items() if h}
    sirovo = {}
    for pref, b in (('mb', 'maxbet'), ('sb', 'soccer'), ('mk', 'merkur'), ('md', 'meridian')):
        s = M.snaps(pref)
        if s: sirovo[b] = s[-1]['out']
    out = []; videni = set()
    for r in ig:
        if r.get('status') == 'Ne igra' and not r.get('minuti_proj'): pass
        key = (M.surname_full(r['igrac']), r['tim'])
        kn = {b: ix[key] for b, ix in knj.items() if key in ix}
        mb_sve = next((v for k, v in raw.items() if k.split('|')[0] == r['igrac'] or M.surname_full(k.split('|')[0]) == key[0] and M.tim(k.split('|')[1]) == r['tim']), None)
        if not kn and not mb_sve: continue
        videni.add(key)
        out.append(dict(t=t, kolo=kolo, igrac=r['igrac'], **{k: r.get(k) for k in POLJA_IG}, knjige=kn, maxbet_sve=mb_sve,
                        linije=KV.get(r['igrac'], [])))
    # igrači u ponudi koje model nema (novi, retko igraju, drugačije ime)
    for b, ix in knj.items():
        for key, d in ix.items():
            if key in videni: continue
            videni.add(key)
            out.append(dict(t=t, kolo=kolo, igrac=None, nepoznat=f'{key[0]}|{key[1]}', knjige={bb: knj[bb][key] for bb in knj if key in knj[bb]}))
    fn = f'arhiva/kolo{kolo}_ponuda.jsonl'
    with open(fn, 'a') as f:
        for o in out: f.write(json.dumps(o, ensure_ascii=False) + '\n')
    return fn, len(out)

def arhiva_rezultati(box_file, kolo):
    """box_file: JSON {'p': [[ime, tim, min, pts, reb, ast, fga, fta, faulovi, starter, ...]], 'polja': [...]} ili lista [ime,min,pts,reb,ast]"""
    d = citaj(box_file)
    fn = f'arhiva/kolo{kolo}_rezultati.json'
    sve = citaj(fn) if os.path.exists(fn) else {}
    if isinstance(d, dict):
        pol = d.get('polja') or ['ime', 'tim', 'min', 'pts', 'reb', 'ast', 'fga', 'fta', 'faulovi', 'starter']
        for p in d['p']: sve[p[0] + '|' + str(p[1])] = dict(zip(pol, p))
        if d.get('skor'): sve['_skor_' + os.path.basename(box_file)] = d['skor']
    else:
        for p in d: sve[p[0]] = dict(zip(['ime', 'min', 'pts', 'reb', 'ast'], p))
    pisi(sve, fn, ensure_ascii=False)
    return fn, len(sve)

if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == 'rezultati':
        print('arhiva rezultata:', arhiva_rezultati(sys.argv[2], int(sys.argv[3])))
    else:
        print('arhiva ponude:', zabelezi())
