from django.conf.urls import *
from pdam.views import *

# handler500 = 'djangotoolbox.errorviews.server_error'

urlpatterns = patterns('pdam.views',
    (r'^report/$', reports),
    (r'^assets/do/$', asset_action_handler),
    (r'^assets/$', assets),
    (r'^assettrans/do/$', assettrans_action_handler),
    (r'^dealitems/do/$', deal_action_handler),
    (r'^ledger/do/$', ledger_action_handler),
    (r'^ledger/$', ledgers),
    (r'^proc/$', process),
    (r'^ruleitems/do/$', ritems_action_handler),
    (r'^rule/do/$', rule_action_handler),
    (r'^rule/$', rules),
    (r'^kontod/do/$', konto_action_handler),
    (r'^bank/do/$', docs_action_handler),
    (r'^kontod/$', kontoplaan),
    (r'^bank/$', docs),
    (r'^$', home),
)
