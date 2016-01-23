# coding: utf-8

from datetime import *
from dateutil.relativedelta import relativedelta
from pdam.models import *
from pdam.loader import BankLoader, KontoLoader, RuleLoader, AssetLoader, LedgerLoader
from pdam.deals import *
from django.template import Context, RequestContext
from django.shortcuts import render_to_response, redirect
from django.core.files import File
from django.db import transaction
from django.db.models import Q
from operator import attrgetter
from datalog import Datalog
from django.utils.encoding import smart_unicode
import re
import codecs

def home(request):
    context = Context({})
    return render_to_response('pd_rp_home.html', context, context_instance=RequestContext(request))

def docs(request):
    docs = Pangadokument.objects.all().order_by('import_aeg')
    count = docs.count()
    context = Context({'docs': docs, 'count': count })
    return render_to_response('bankdocs.html', context, context_instance=RequestContext(request))

def docs_action_handler(request):
    template = 'edit_docs.html'
    go_home = False
    form = PangadokumentForm()
    pk = ''
    context = {}
    if request.method == 'POST':
        if request.POST['action'] == 'Update':
            doc = Pangadokument.objects.get(pk=request.POST['pk'])
            form = PangadokumentForm(instance=doc)
            pk = request.POST['pk']
            context = {'form': form, 'pk': pk}
        elif request.POST['action'] == 'Delete':
            doc = Pangadokument.objects.get(pk=request.POST['pk'])
            doc.delete()
            go_home = True
        elif request.POST['action'] == 'View':
            doc = Pangadokument.objects.get(pk=request.POST['pk'])
            form = PangadokumentForm(instance=doc)
            pk = request.POST['pk']
            rows = Pangakirje.objects.all().filter(allikas=doc).order_by('kuupaev', 'reatyyp', 'arhiveerimistunnus')
            #rows = sorted(rows, key=attrgetter('kuupaev'))
            context = {'form': form, 'rows': rows, 'pk': pk}
            template = 'transactions.html'
        elif request.POST['action'] == 'Save':
            pk = request.POST['pk']
            if pk != '':
                doc = Pangadokument.objects.get(pk=pk)
                form = PangadokumentForm(request.POST, instance=doc)
            else:
                form = PangadokumentForm(request.POST)
            if form.is_valid():
                form.save()
                go_home = True
            else:
                context = {'form': form, 'pk': pk}
        elif request.POST['action'] == 'Cancel':
            go_home = True
        elif request.POST['action'] == 'LoadCVS':
            request.encoding = 'utf-8'
            wf = request.FILES['cvs']
            f = File(wf)
            bl = BankLoader()
            pd = bl.make_pd(wf.name)
            bl.read_csv(f, pd)
            go_home = True
    else:
        go_home = True
    if go_home:            
        result = redirect(docs)
    else:
        result = render_to_response(template, context, context_instance=RequestContext(request))
    return result

def kontoplaan(request):
    rows = Konto.objects.all().order_by('kontonumber')
    context = {'rows': rows}
    template = 'kontoplaan.html'
    return render_to_response(template, context, context_instance=RequestContext(request))

def konto_action_handler(request):
    template = 'kontoplaan.html'
    go_home = False
    context = {}
    if request.method == 'POST':
        if request.POST.has_key('action'):
            if request.POST['action'] == u'Loe kontoplaan':
                request.encoding = 'utf-8'
                if request.FILES.has_key('cvs'):
                    wf = request.FILES['cvs']
                    f = File(wf)
                    kl = KontoLoader()
                    kl.import_kontoplaan(f)
                go_home = True
                
            elif request.POST['action'] == u'Kirjuta kontoplaan faili':
                f = codecs.open('kontoplaan.csv', mode="w", encoding="utf8")
                kl = KontoLoader()
                if kl.export_kontoplaan(f):
                    f.close()
                go_home = True
    else:
        go_home = True
    if go_home:            
        result = redirect(kontoplaan)
    else:
        result = render_to_response(template, context, context_instance=RequestContext(request))
    return result

def rules(request):
    rules = Tehingutyyp.objects.all().order_by('kirjeldus')
    count = rules.count()
    context = Context({'rules': rules, 'count': count })
    return render_to_response('rules.html', context, context_instance=RequestContext(request))

def rule_action_handler(request):
    template = 'rule_edit.html'
    go_home = False
    count = 0
    context = {'icount': count}
    if request.method == 'POST' and request.POST.has_key('action'):
        if request.POST['action'] == u'Loe reeglid':
            request.encoding = 'utf-8'
            if request.FILES.has_key('cvs'):
                wf = request.FILES['cvs']
                f = File(wf)
                kl = RuleLoader()
                kl.import_rules(f)
            go_home = True
        elif request.POST['action'] == u'Kirjuta reeglid faili':
            f = codecs.open('rules.csv', mode="w", encoding="utf8")
            kl = RuleLoader()
            if kl.export_rules(f):
                f.close()
            go_home = True
        else:
            form = TehingutyypForm()
            pk = request.POST['pk']
            items = []
            if pk != '':
                doc = Tehingutyyp.objects.get(pk=pk)
                items = Kontokasutus.objects.all().filter(tehingutyyp=doc).order_by('konto')
                count = items.count()
            else:
                count = 0
            context = {'pk': pk, 'items': items, 'icount': count}
            if request.POST['action'] == 'Add':
                pk = ''
                context = {'form': form, 'pk': pk, 'icount': 0}
            elif request.POST['action'] == 'Update':
                form = TehingutyypForm(instance=doc)
                context = {'form': form, 'pk': pk, 'items': items, 'icount': count}
            elif request.POST['action'] == 'Delete':
                items.delete()
                doc.delete()
                go_home = True
            elif request.POST['action'] == 'Save':
                if pk != '':
                    doc = Tehingutyyp.objects.get(pk=pk)
                    form = TehingutyypForm(request.POST, instance=doc)
                else:
                    form = TehingutyypForm(request.POST)
                if form.is_valid():
                    form.save()
                    go_home = True
                else:
                    context = {'form': form, 'pk': pk, 'items': items, 'icount': count}
            elif request.POST['action'] == 'Cancel':
                go_home = True
    else:
        go_home = True
    if go_home:            
        result = redirect(rules)
    else:
        result = render_to_response(template, context, context_instance=RequestContext(request))
    return result

def ritems_action_handler(request):
    template = 'ritems_edit.html'
    go_home = False
    form = KontokasutusForm()
    pk = request.POST['pk']
    context = {}
    if request.method == 'POST':
        if request.POST['action'] == 'Add':
            ipk = ''
            form = KontokasutusForm(initial={'tehingutyyp': Tehingutyyp.objects.get(pk=pk)})
            context = {'form': form, 'pk': pk, 'ipk': ipk}
        elif request.POST['action'] == 'Update':
            ipk = request.POST['ipk']
            doc = Kontokasutus.objects.get(pk=ipk)
            form = KontokasutusForm(instance=doc)
            context = {'form': form, 'pk': pk, 'ipk': ipk}
        elif request.POST['action'] == 'Save':
            ipk = request.POST['ipk']
            if ipk != '':
                print 'Olemasolev kontokasutus'
                doc = Kontokasutus.objects.get(pk=ipk)
                form = KontokasutusForm(request.POST, instance=doc)
            else:
                print 'Uus kontokasutus'
                form = KontokasutusForm(request.POST)
            if form.is_valid():
                form.save()
                go_home = True
            else:
                print 'Form is not valid!',form.errors
                context = {'form': form, 'pk': pk, 'ipk': ipk}
        elif request.POST['action'] == 'Cancel':
            go_home = True
    else:
        go_home = True
    if go_home:            
        result = redirect(rules)
    else:
        result = render_to_response(template, context, context_instance=RequestContext(request))
    return result

def process(request):
    print 'Processing transactions ...'
    LOG = Datalog('process.log')
    docs = Pangadokument.objects.all().order_by('import_aeg')
    for doc in docs:
        LOG.info('Pangadokument: '+doc.failinimi)
        rows = Pangakirje.objects.all().filter(allikas=doc, arvestatud='N').order_by('kuupaev', 'reatyyp', 'arhiveerimistunnus')
        for row in rows:
            LOG.info('Rida: '+row.selgitus)
            rules = Tehingutyyp.objects.all()
            created = 0
            for rule in rules:
                if row.reatyyp == rule.reatyyp and row.tunnus == rule.tunnus and re.search(rule.triger, row.selgitus) and row.arvestatud != 'J':
                    LOG.info('Triger: '+ rule.triger )
                    items = Kontokasutus.objects.all().filter(tehingutyyp=rule).order_by('on_deebet')
                    deals = Deals(LOG)
                    created = deals.create(row, items, rule)
            if created == 0:
                LOG.warning(' > Kandeid ei tehtud')
    context = {'LOG': LOG.log}
    LOG.end()
    result = render_to_response('showlog.html', context, context_instance=RequestContext(request))
    return result

@transaction.atomic
def ledgers(request):
    print '* Ledgers', request.method, request.POST.keys()
    template = 'ledger.html'
    prs = Pearaamat.objects.all().order_by('aasta')
    pr_count = prs.count()
    if pr_count == 0:
        pr = Pearaamat()
        pr.aasta = 2015
        pr.on_avatud = True
        pr.save()
        prs = Pearaamat.objects.all().order_by('aasta')
        pr_count = prs.count()
    if request.POST.has_key(u'year'):
        pr = Pearaamat.objects.get(aasta=request.POST[u'year'])
    else:
        pr = prs.reverse()[:1][0]
    if request.method == u'POST' and request.POST.has_key(u'action'):
        print '* Ledgers/Action: ',request.POST[u'action']
        if request.POST['action'] == u'Loe tehingud':
            request.encoding = 'utf-8'
            if request.FILES.has_key('cvs'):
                wf = request.FILES['cvs']
                f = File(wf)
                kl = LedgerLoader()
                kl.import_ledger(f)
        elif request.POST['action'] == u'Kirjuta tehingud faili':
            f = codecs.open('ledger.csv', mode="w", encoding="utf8")
            kl = LedgerLoader()
            kl.export_ledger(f)
            f = codecs.open('ledgertable.csv', mode="w", encoding="utf8")
            kl.export_ledger_table(f, pr)
        elif request.POST['action'] == u'Tulude-Kulude sulgemine':
            tuluKuluSulgemine(pr)
        elif request.POST['action'] == u'A-tehingute kustutamine':
            deals = Tehing.objects.all().filter(pearaamat=pr, on_manual=False)
            for d in deals:
                pts = Pangakirje.objects.all().filter(tehing=d)
                for pt in pts:
                    pt.arvestatud = 'N'
                    pt.tehing = None 
                    pt.save()
                Kanne.objects.all().filter(tehing=d).delete()
                d.delete()
        elif request.POST['action'] == u'Aasta lõpetamine':
            aastaSulgemine(pr)
        elif request.POST['action'] in ('Algsaldo', 'Cancel'):
            template = 'saldo.html'
            form = AlgsaldoForm()
            items = Algsaldo.objects.all().filter(pearaamat=pr).order_by('konto__kontonumber')
            icount = items.count()
            rp = RP_korras(pr)
            context = {'form': form, 'pk': pr.id, 'items': items, 'icount': icount, 'rp': rp, 'year': pr.aasta}
            return render_to_response(template, context, context_instance=RequestContext(request))
        elif request.POST['action'] == u'SaldoUpdate':
            template = 'saldo.html'
            S = Algsaldo.objects.get(pk=request.POST['ipk'])
            form = AlgsaldoForm(instance=S)
            items = Algsaldo.objects.all().filter(pearaamat=pr).order_by('konto__kontonumber')
            icount = items.count()
            rp = RP_korras(pr)
            context = {'form': form, 'pk': pr.id, 'items': items, 'icount': icount, 'rp': rp, 'year': pr.aasta, 'ipk': S.id}
            return render_to_response(template, context, context_instance=RequestContext(request))
        elif request.POST['action'] == u'Save':
            template = 'saldo.html'
            if request.POST.has_key('ipk') and request.POST['ipk'] != '':
                S = Algsaldo.objects.get(pk=request.POST['ipk'])
                form = AlgsaldoForm(request.POST, instance=S)
            else:
                form = AlgsaldoForm(request.POST)
            if form.is_valid():
                form.save()
            else:
                print 'Form is not valid!',form.errors
            form = AlgsaldoForm()
            items = Algsaldo.objects.all().filter(pearaamat=pr).order_by('konto__kontonumber')
            icount = items.count()
            rp = RP_korras(pr)
            context = {'form': form, 'pk': pr.id, 'items': items, 'icount': icount, 'rp': rp, 'year': pr.aasta}
            return render_to_response(template, context, context_instance=RequestContext(request))
        elif request.POST['action'] == u'Delete':
            T = Tehing.objects.get(pk=request.POST['deal_id'])
            if not T.on_manual:
                pts = Pangakirje.objects.all().filter(tehing=T)
                for pt in pts:
                    pt.arvestatud = 'N'
                    pt.tehing = None 
                    pt.save()
                Kanne.objects.all().filter(tehing=T).delete()
                T.delete()
        elif request.POST['action'] == u'Update':
            T = Tehing.objects.get(pk=request.POST['deal_id'])
            form = TehingForm(instance=T)
            items = Kanne.objects.all().filter(tehing=T).order_by('konto__kontonumber')
            icount = items.count()
            btrs = Pangakirje.objects.all().filter(tehing=T).order_by('kuupaev', 'reatyyp', 'arhiveerimistunnus')
            rp = RP_korras(T)
            context = {'form': form, 'pk': T.id, 'items': items, 'icount': icount, 'rp': rp, 'btrs': btrs}
            return render_to_response('deal.html', context, context_instance=RequestContext(request))
        elif request.POST['action'] == u'Add':
            form = TehingForm()
            rp = {'Aktiva':0, 'Passiva':0, 'Tulud':0, 'Kulud':0, 'RP':0}
            context = {'form': form, 'items': [], 'icount': 0, 'rp': rp, 'btrs': []}
            return render_to_response('deal.html', context, context_instance=RequestContext(request))
        
    deals = Tehing.objects.all().filter(pearaamat=pr).order_by('tehingupaev')
    for d in deals:
        rp = RP_korras(d)
        d.korras = rp['RP'] == 0
        btrs = Pangakirje.objects.all().filter(tehing=d).order_by('kuupaev', 'reatyyp', 'arhiveerimistunnus')
        if len(btrs) > 0:
            d.sisu = d.sisu+': '+btrs[0].selgitus
        d.kandeid = Kanne.objects.all().filter(tehing=d).count()
    algs = Algsaldo.objects.all().filter(pearaamat=pr).order_by('konto')
    context = Context({'prs': prs, 'pr_count': pr_count, 'pr' : pr, 'deals' : deals, 'dc' : deals.count(), 'algs' : algs})

    return render_to_response(template, context, context_instance=RequestContext(request))

def ledger_action_handler(request):
    
    if request.method == 'POST':
        if request.POST['action'] == 'Cancel':
            pass
        elif request.POST['action'] == 'Save':
            pk = request.POST['pk']
            if pk != '':
                deal = Tehing.objects.get(pk=pk)
                form = TehingForm(request.POST, instance=deal)
            else:
                form = TehingForm(request.POST)
            if form.is_valid():
                form.save()
            else:
                print 'Form is not valid!',form.errors
                if deal:
                    items = Kanne.objects.all().filter(tehing=deal)
                else:
                    items = []
                icount = items.count()
                context = {'form': form, 'pk': pk, 'items': items, 'icount': icount}
                return render_to_response('deal.html', context, context_instance=RequestContext(request))
    return redirect(ledgers)

def deal_action_handler(request):
    if request.method == 'POST':
        if request.POST['action'] == 'Cancel':
            pass
        elif request.POST['action'] == 'Save':
            pk = request.POST['pk']
            ipk = request.POST['ipk']
            if ipk != '':
                k = Kanne.objects.get(pk=ipk)
                form = KanneForm(request.POST, instance=k)
            else:
                form = KanneForm(request.POST)
            if form.is_valid():
                form.save()
            else:
                print 'Form is not valid!',form.errors
                context = {'form': form, 'pk': pk, 'ipk': ipk}
                return render_to_response('ditem_edit.html', context, context_instance=RequestContext(request))
        elif request.POST['action'] == 'Update':
            pk = request.POST['pk']
            ipk = request.POST['ipk']
            if ipk != '':
                k = Kanne.objects.get(pk=ipk)
                form = KanneForm(instance=k)
                context = {'form': form, 'pk': pk, 'ipk': ipk, 'info':request.POST['action']}
                return render_to_response('ditem_edit.html', context, context_instance=RequestContext(request))
        elif request.POST['action'] == 'Add':
            pk = request.POST['pk']
            T = Tehing.objects.get(pk=pk)
            kt = Konto.objects.get(pk='11')
            k = Kanne(tehing=T, konto=kt, on_deebet=False, summa=0, on_manual= True)
            form = KanneForm(instance=k)
            context = {'form': form, 'pk': pk, 'ipk': '', 'info':request.POST['action']}
            return render_to_response('ditem_edit.html', context, context_instance=RequestContext(request))
            
    return redirect(ledgers)

def assets(request):
    a = Vara.objects.all().order_by('vp_tyyp', 'nimetus')
    vh = VaraHaldur()
    assets = []
    for i in a:
        if vh.getEndCount(i.id) > 0.0 or vh.getLastDealYear(i.id) == vh.getActivePR().aasta: 
            assets.append(i) 
    count = len(assets)
    stat = []
    statb = vh.statusReport(date(vh.getActivePR().aasta-1, 12, 31))
    stat.append(statb)
    for i in range(0, 11):
        stat.append(vh.statusReport(date(vh.getActivePR().aasta, 1, 31) + relativedelta(months=+i) ))
    state = vh.statusReport(date(vh.getActivePR().aasta, 12, 31))
    stat.append(state)
    context = Context({'assets': assets, 'count': count, 'statb':statb, 'state':state, 'stat':stat })
    return render_to_response('assets.html', context, context_instance=RequestContext(request))

def asset_action_handler(request):
    prs = Pearaamat.objects.all().order_by('aasta')
    if request.POST.has_key('year'):
        pr = Pearaamat.objects.get(aasta=request.POST['year'])
    else:
        pr = prs.reverse()[:1][0]

    template = 'asset_edit.html'
    go_home = False
    count = 0
    context = {'icount': count}
    if request.method == 'POST' and request.POST.has_key('action'):
        if request.POST['action'] == 'Loe varad':
            if request.FILES.has_key('cvs'):
                request.encoding = 'utf-8'
                wf = request.FILES['cvs']
                f = codecs.EncodedFile(File(wf), 'utf8')
                kl = AssetLoader()
                kl.setYear(pr.aasta)
                kl.import_assets(f)
            go_home = True
        elif request.POST['action'] == 'Kirjuta varad faili':
            f = codecs.open('assets.txt', mode="w", encoding="utf8")
            kl = AssetLoader()
            if kl.export_assets(date(pr.aasta, 12, 31), f):
                f.close()
            f = codecs.open('assetdeals.csv', mode="w", encoding="utf8")
            kl = AssetLoader()
            if kl.export_assetdeals(f):
                f.close()
            go_home = True
        elif request.POST['action'] == u'Kustuta tehingud':
            Varatehing.objects.all().delete()
            go_home = True
        elif request.POST['action'] == u'Kustuta varad':
            Vara.objects.all().delete()
            go_home = True
        elif request.POST['action'] == u'Ümberarvutus':
            vh = VaraHaldur()
            vh.analyse()
            vs = Vara.objects.all()
            for v in vs:
                vh.recalc(v.id)
            go_home = True
        else:
            form = VaraForm()
            pk = request.POST['pk']
            if pk != '':
                doc = Vara.objects.get(pk=pk)
                items = Varatehing.objects.all().filter(vara=doc).order_by('vaartuspaev','-tyyp','-kogus')
                count = items.count()
            else:
                count = 0
            context = {'pk': pk, 'items': items, 'icount': count}
            if request.POST['action'] == 'Add':
                pk = ''
                context = {'form': form, 'pk': pk, 'icount': 0}
            elif request.POST['action'] == 'Update':
                form = VaraForm(instance=doc)
                context = {'form': form, 'pk': pk, 'items': items, 'icount': count}
            elif request.POST['action'] == 'Delete':
                items.delete()
                doc.delete()
                go_home = True
            elif request.POST['action'] == 'Save':
                if pk != '':
                    doc = Vara.objects.get(pk=pk)
                    form = VaraForm(request.POST, instance=doc)
                else:
                    form = VaraForm(request.POST)
                if form.is_valid():
                    form.save()
                    go_home = True
                else:
                    context = {'form': form, 'pk': pk, 'items': items, 'icount': count}
            elif request.POST['action'] == 'Cancel':
                go_home = True
    else:
        go_home = True
    if go_home:            
        result = redirect(assets)
    else:
        result = render_to_response(template, context, context_instance=RequestContext(request))
    return result

def assettrans_action_handler(request):
    context = {}
    if request.method == 'POST' and request.POST.has_key('action'):
        if request.POST['action'] == 'Add':
            pk = request.POST['pk']
            v = Vara.objects.get(pk=pk)
            form = VaratehingForm(vara=v)
            context = {'form': form, 'pk': pk, 'ipk': 0}
        elif request.POST['action'] == 'Update':
            pk = request.POST['pk']
            ipk = request.POST['ipk']
            doc=Varatehing.objects.get(pk=ipk)
            form = VaratehingForm(instance=doc)
            context = {'form': form, 'pk': pk, 'ipk': ipk}
        elif request.POST['action'] == 'Delete':
            ipk = request.POST['ipk']
            Varatehing.objects.all().filter(pk=ipk).delete()
        elif request.POST['action'] == 'Save':
            pk = request.POST['pk']
            ipk = request.POST['ipk']
            if ipk != '':
                doc=Varatehing.objects.get(pk=ipk)
                form = VaratehingForm(request.POST, instance=doc)
            else:
                form = VaratehingForm(request.POST)
            if form.is_valid():
                form.save()
            else:
                context = {'form': form, 'pk': pk, 'ipk': ipk}
        elif request.POST['action'] == 'Cancel':
            pass
    if len(context) > 0:
        result = render_to_response('assettrans_edit.html', context, context_instance=RequestContext(request))
    else:
        result = redirect(assets)
    return result 

def findKVT(aasta):
    akpv = date(aasta, 1, 1)
    lkpv = date(aasta, 12, 31)
    vts = Varatehing.objects.all().filter(vaartuspaev__gte=akpv, vaartuspaev__lte=lkpv).order_by('vaartuspaev')
    vtx = []
    for vt in vts:
        cnt = 0
        if vt.tyyp != 'H':
            ks = Kanne.objects.all().filter(Q(konto__kontonumber='117')|Q(konto__kontonumber='118')|
                                        Q(konto__kontonumber='1191')|Q(konto__kontonumber='115')|Q(konto__kontonumber='1132'),
                                        tehing__maksepaev=vt.vaartuspaev, summa=vt.eur_summa)
            cnt = ks.count()
        else:
            vh = VaraHaldur()
            dr = abs(vh.getReservDiff(vt.vara.id, vt.vaartuspaev))
            if dr != 0:
                ks = Kanne.objects.all().filter(Q(konto__kontonumber='117')|Q(konto__kontonumber='118')|
                                        Q(konto__kontonumber='1191')|Q(konto__kontonumber='264'),
                                        tehing__maksepaev=vt.vaartuspaev, summa=dr)
                cnt = ks.count()
            else:
                cnt = -1
        if cnt == 0:
            vtx.append(vt)
    return vtx

def findT4VT(aasta):
    akpv = date(aasta, 1, 1)
    lkpv = date(aasta, 12, 31)
    vts = Varatehing.objects.all().filter(vaartuspaev__gte=akpv, vaartuspaev__lte=lkpv).order_by('vaartuspaev')
    vtx = []
    for vt in vts:
        cnt = 0
        if vt.tyyp != 'H':
            ks = Kanne.objects.all().filter(Q(konto__kontonumber='117')|Q(konto__kontonumber='118')|
                                        Q(konto__kontonumber='1191')|Q(konto__kontonumber='115')|Q(konto__kontonumber='1132'),
                                        tehing__maksepaev=vt.vaartuspaev, summa=vt.eur_summa)
            cnt = ks.count()
        else:
            vh = VaraHaldur()
            dr = abs(vh.getReservDiff(vt.vara.id, vt.vaartuspaev))
            if dr != 0:
                ks = Kanne.objects.all().filter(Q(konto__kontonumber='117')|Q(konto__kontonumber='118')|
                                        Q(konto__kontonumber='1191')|Q(konto__kontonumber='264'),
                                        tehing__maksepaev=vt.vaartuspaev, summa=dr)
                cnt = ks.count()
            else:
                cnt = -1
        if cnt > 0:
            vtx.append(vt)
    return vtx

def reports(request):
    if request.GET.has_key('rt'):
        if request.GET['rt'] == 'kvt':
            prs = Pearaamat.objects.all().order_by('aasta')
            pr_count = prs.count()
            if request.POST.has_key('year'):
                pr = Pearaamat.objects.get(aasta=request.POST['year'])
            else:
                pr = prs.reverse()[:1][0]
            vtx = findKVT(pr.aasta)
            vh = VaraHaldur()
            data = vh.reservMovementReport(pr)
            x = vh.assetReport(pr)
            asst = x[0]
            sums = x[1]
            context = Context({'prs':prs, 'pr_count':pr_count, 'year':pr.aasta, 'vtx':vtx, 'data':data, 'asst':asst, 'sums':sums})
            return render_to_response('reports_kvt.html', context, context_instance=RequestContext(request))
        if request.GET['rt'] == 'bil':
            prs = Pearaamat.objects.all().order_by('aasta')
            pr_count = prs.count()
            if request.POST.has_key('year'):
                pr = Pearaamat.objects.get(aasta=request.POST['year'])
            else:
                pr = prs.reverse()[:1][0]
            vtx = findBIL(pr)
            context = Context({'prs':prs, 'pr_count':pr_count, 'year':pr.aasta, 'vtx':vtx[0], 'tot':vtx[1]})
            return render_to_response('reports_bil.html', context, context_instance=RequestContext(request))
        if request.GET['rt'] == 'kas':
            prs = Pearaamat.objects.all().order_by('aasta')
            pr_count = prs.count()
            if request.POST.has_key('year'):
                pr = Pearaamat.objects.get(aasta=request.POST['year'])
            else:
                pr = prs.reverse()[:1][0]
            vtx = kasumiAruanne(pr)
            context = Context({'prs':prs, 'pr_count':pr_count, 'year':pr.aasta, 'vtx':vtx[0], 'fin':vtx[1], 'tot':vtx[2]})
            return render_to_response('reports_kas.html', context, context_instance=RequestContext(request))
        if request.GET['rt'] == 'rva':
            prs = Pearaamat.objects.all().order_by('aasta')
            pr_count = prs.count()
            if request.POST.has_key('year'):
                pr = Pearaamat.objects.get(aasta=request.POST['year'])
            else:
                pr = prs.reverse()[:1][0]
            rva = rahavoogudeAruanne(pr)
            context = Context({'prs':prs, 'pr_count':pr_count, 'year':pr.aasta, 'rva':rva })
            return render_to_response('reports_rva.html', context, context_instance=RequestContext(request))
    elif request.POST.has_key('action'):
        if request.POST['action'] == u'Kustuta erinevustega tehingud':
            prs = Pearaamat.objects.all().order_by('aasta')
            pr_count = prs.count()
            if request.POST.has_key('year'):
                pr = Pearaamat.objects.get(aasta=request.POST['year'])
            else:
                pr = prs.reverse()[:1][0]
            vtx = findKVT(pr.aasta)
            lkpv = date(pr.aasta, 12, 31)
            vh = VaraHaldur()
            data = vh.reservMovementReport(pr)
            for r in data:
                print r
                if float(r['dk']) != float(r['dv']):
                    print '-- erinevus!'
                    T = Tehing.objects.get(pk=r['t'])
                    if not T.on_manual:
                        pts = Pangakirje.objects.all().filter(tehing=T)
                        for pt in pts:
                            pt.arvestatud = 'N'
                            pt.tehing = None 
                            pt.save()
                        Kanne.objects.all().filter(tehing=T).delete()
                        print '-- kustutan tehingu ', T.sisu
                        vtt = Varatehing.objects.all().filter(tehing_id=T.id)
                        for u in vtt:
                            u.tehing_id = None
                            u.save()
                        T.delete()
        if request.POST['action'] == u'Genereeri ümberhindlused':
            prs = Pearaamat.objects.all().order_by('aasta')
            pr_count = prs.count()
            if request.POST.has_key('year'):
                pr = Pearaamat.objects.get(aasta=request.POST['year'])
            else:
                pr = prs.reverse()[:1][0]
            vtx = findKVT(pr.aasta)
            print '..1 vtx.length = ', len(vtx)
            lkpv = date(pr.aasta, 12, 31)
            vh = VaraHaldur()
            for vt in vtx:
                if vt.tyyp == 'H':
                    dr = vh.getReservDiff(vt.vara.id, lkpv)
                    if dr != 0:
                        tt = Tehingutyyp.objects.get(kirjeldus=u'Käsitsi sisestatud tehing')
                        if vt.vara.vp_tyyp == 'A':
                            l_sisu = u'Aktsia ümberhindamine '
                            l_konto = '117'
                        elif vt.vara.vp_tyyp == 'V':
                            l_sisu = u'Võlakirja ümberhindamine '
                            l_konto = '118'
                        elif vt.vara.vp_tyyp == 'I':
                            l_sisu = u'Alt.investeeringu ümberhindamine '
                            l_konto = '1191'
                        l_sisu = l_sisu + '(' + vt.vara.nimetus + ')'
                        t = Tehing.objects.create(pearaamat=pr, tehingutyyp=tt, sisu=l_sisu, tehingupaev=lkpv, maksepaev=lkpv, on_manual=True)
                        vpk = Konto.objects.get(pk=l_konto)
                        rsk = Konto.objects.get(pk='264')
                        vt.tehing_id = t.id
                        vt.save()
                    else:
                        print '... reserv_diff = 0: ', vt.vara.nimetus
                    if dr > 0:
                        Kanne.objects.create(tehing=t, konto=vpk, on_deebet=True, summa=dr, on_manual=True)
                        Kanne.objects.create(tehing=t, konto=rsk, on_deebet=False, summa=dr, on_manual=True)
                    elif dr < 0:
                        Kanne.objects.create(tehing=t, konto=vpk, on_deebet=False, summa=abs(dr), on_manual=True)
                        Kanne.objects.create(tehing=t, konto=rsk, on_deebet=True, summa=abs(dr), on_manual=True)
                        
            vtx = findT4VT(pr.aasta)
            print '..2 vtx.length = ', len(vtx)
            for vt in vtx:
                if vt.tyyp == 'H':
                    tt = Tehingutyyp.objects.get(kirjeldus=u'Käsitsi sisestatud tehing')
                    if vt.vara.vp_tyyp == 'A':
                        l_sisu = u'Aktsia ümberhindamine '
                        l_konto = '117'
                    elif vt.vara.vp_tyyp == 'V':
                        l_sisu = u'Võlakirja ümberhindamine '
                        l_konto = '118'
                    elif vt.vara.vp_tyyp == 'I':
                        l_sisu = u'Alt.investeeringu ümberhindamine '
                        l_konto = '1191'
                    l_sisu = l_sisu + '(' + vt.vara.nimetus + ')'
                    t = Tehing.objects.all().filter(pearaamat=pr, tehingutyyp=tt, sisu=l_sisu, tehingupaev=lkpv, maksepaev=lkpv, on_manual=True)
                    if len(t) > 0:
                        vt.tehing_id = t[0].id
                        vt.save()
                    else:
                        '... no ', l_sisu
    context = Context({})
    return render_to_response('pd_rp_home.html', context, context_instance=RequestContext(request))
    
