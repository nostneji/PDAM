# coding: utf-8
from django.forms import *
from django.db import models
from django.db.models import Sum

def nvl(x, v):
    return v if x is None else x

def date2str(d):
    return str(d.day)+'.'+str(d.month)+'.'+str(d.year)

class Pangadokument (models.Model):
    import_aeg = models.DateTimeField()
    failinimi = models.FilePathField()
    
    def __str__(self):
        return str(self.failinimi)

class PangadokumentForm (ModelForm):
    class Meta:
        model = Pangadokument

class Konto (models.Model):
    osad = (
        ('A','Aktiva'),
        ('P','Passiva'),
        ('T','Tulud'),
        ('K','Kulud'),    
        )
    kontonumber = models.CharField(max_length=5, primary_key=True)
    nimetus = models.CharField(max_length=255)
    osa = models.CharField(max_length=1, choices=osad)
    pangakonto = models.CharField(max_length=20, blank=True, null=True)
    valuuta = models.CharField(max_length=3)
    class Meta:
        ordering = ['kontonumber']
        
    def __str__(self):
        return self.osa + '.' + self.kontonumber + ':' + self.nimetus

class KontoForm (ModelForm):
    class Meta:
        model = Konto
        
class Tehingutyyp (models.Model):        
    kirjeldus = models.CharField(max_length=100)
    reatyyp = models.SmallIntegerField(blank=True, null=True)
    tunnus = models.CharField(max_length=10, blank=True, null=True)
    triger = models.CharField(max_length=255, blank=True, null=True) # reg exp

    def __str__(self):
        return self.kirjeldus
    
    
class TehingutyypForm (ModelForm):
    class Meta:
        model = Tehingutyyp
        
class Kontokasutus (models.Model):
    tehingutyyp = models.ForeignKey(Tehingutyyp)
    konto = models.ForeignKey(Konto)
    on_deebet = models.BooleanField()
    valem = models.CharField(max_length=255)

'''
  Valemi süntaks:
  
  prefixid: ':' - lokaalne muutuja; '@' - aktiivse kirje väli; '#' - tingimustele vastava kirje väli
  omistus ::- [ '{' tv_exp '}' ] locvar '=' exp . 
  exp ::- add [ ('+'|'-') add ] .
  add ::- term [ ('*'|'/') term ] .
  term ::- var | '(' exp ')' | func | numval | charval .
  var ::- locvar | recvar | qryvar .
  locvar ::- ':' id .
  recvar ::- '@' id .
  qryvar ::- '#' id .
  func ::- '_' id '(' [ params ] ')' .
  params ::- exp { ',' exp } .
  numval ::- intval [ '.' intval ] .
  intval ::- '0'..'9' { '0'..'9' } .
  charval ::- '\'' string '\'' .
  tv_exp ::- exp ('<'|'>'|'='|'&') exp .
'''
        
class KontokasutusForm (ModelForm):
    class Meta:
        model = Kontokasutus
        
class Pearaamat (models.Model):
    aasta = models.SmallIntegerField()
    on_avatud = models.BooleanField()
    
    def __str__(self):
        return str(self.aasta)
    
class Algsaldo (models.Model):
    pearaamat = models.ForeignKey(Pearaamat)
    konto = models.ForeignKey(Konto)
    on_deebet = models.BooleanField()
    summa = models.DecimalField(max_digits=16, decimal_places=2)
    on_manual = models.BooleanField()
    on_fikseeritud = models.BooleanField()

class AlgsaldoForm (ModelForm):
    class Meta:
        model = Algsaldo

class Tehing (models.Model):
    pearaamat = models.ForeignKey(Pearaamat)
    tehingutyyp = models.ForeignKey(Tehingutyyp)
    sisu = models.CharField(max_length=255)
    tehingupaev = models.DateField()
    maksepaev = models.DateField()
    on_manual = models.BooleanField()
    korras = False
    kandeid = 0
    class Meta:
        ordering = ['maksepaev']

    def __str__(self):
        return str(date2str(self.maksepaev)+' '+self.sisu[0:20])
    
class TehingForm (ModelForm):
    class Meta:
        model = Tehing
    
class Kanne (models.Model):
    tehing = models.ForeignKey(Tehing)
    konto = models.ForeignKey(Konto)
    on_deebet = models.BooleanField()
    summa = models.DecimalField(max_digits=16, decimal_places=2)
    on_manual = models.BooleanField()

    def __str__(self):
        return ('D' if self.on_deebet else 'K')+self.konto.kontonumber+':'+str(self.summa)
    
class KanneForm (ModelForm):
    class Meta:
        model = Kanne
        fields = ('tehing', 'konto', 'on_deebet', 'summa', 'on_manual')
        widgets = {
            'tehing': TextInput(attrs={'size': 50,}),
        }

class Pangakirje (models.Model):
    pangakonto = models.CharField(max_length=15)
    reatyyp = models.SmallIntegerField()
    kuupaev = models.DateField()
    partner = models.CharField(max_length=100, blank=True, null=True)
    selgitus = models.CharField(max_length=255, blank=True, null=True)
    summa = models.CharField(max_length=20)
    valuuta = models.CharField(max_length=3)
    deebet = models.CharField(max_length=1)
    arhiveerimistunnus = models.CharField(max_length=100, blank=True, null=True)
    tunnus = models.CharField(max_length=100, blank=True, null=True)
    viitenumber = models.CharField(max_length=20, blank=True, null=True)
    dokument = models.CharField(max_length=100, blank=True, null=True)
    arvestatud = models.CharField(max_length=1, blank=True, null=True)
    allikas = models.ForeignKey(Pangadokument)
    tehing = models.ForeignKey(Tehing, blank=True, null=True)

    def __str__(self):
        return self.pangakonto+';'+str(self.kuupaev)+';'+self.deebet+';'+self.summa+';'+self.valuuta+';'+self.selgitus+';'+self.arvestatud

class PangakirjeForm (ModelForm):
    class Meta:
        model = Pangakirje
 
class Vara (models.Model):
    tyybid = (
        ('A','Aktsia'),
        ('V','Võlakiri'),
        ('I','Alternatiiv'),
        )
    nimetus = models.CharField(max_length=100)
    vp_tyyp = models.CharField(max_length=1, choices=tyybid)
    lyhend = models.CharField(max_length=20)
        
    def __str__(self):
        return self.nimetus+' ('+self.lyhend+')'

class VaraForm (ModelForm):
    class Meta:
        model = Vara
     
class VaraMall (models.Model):
    mall = models.CharField(max_length=255)
    vara = models.ForeignKey(Vara)
    
class Varatehing (models.Model):
    tyybid = (
        ('O','Ost'),
        ('M','Müük'),
        ('H','Ümberhindlus'),
        )
    vara = models.ForeignKey(Vara)
    tyyp = models.CharField(max_length=1, choices=tyybid)
    tehingupaev = models.DateField()
    vaartuspaev = models.DateField()
    kogus = models.DecimalField(max_digits=16, decimal_places=6)
    summa = models.DecimalField(max_digits=16, decimal_places=2)
    valuuta = models.CharField(max_length=3)
    eur_summa = models.DecimalField(max_digits=16, decimal_places=2)
    yldkogus = models.DecimalField(max_digits=16, decimal_places=6)
    soetushind = models.DecimalField(max_digits=16, decimal_places=2)
    turuhind = models.DecimalField(max_digits=16, decimal_places=2)
    reserv = models.DecimalField(max_digits=16, decimal_places=2)
    tehing_id = models.IntegerField(blank=True, null=True)
    
    def __str__(self):
        return self.vara.nimetus+';'+self.tyyp+';'+str(self.vaartuspaev)+';'+str(self.kogus)+';'+str(self.summa)+';'+self.valuuta+';'+str(self.eur_summa)+';'+str(self.yldkogus)+';'+str(self.soetushind)+';'+str(self.turuhind)+';'+str(self.reserv)

class VaratehingForm (ModelForm):
    class Meta:
        model = Varatehing
     
    
