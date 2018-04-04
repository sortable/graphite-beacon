from graphite_beacon.alerts import BaseAlert
from graphite_beacon.handlers.slack import SlackHandler

def _configure_reactor(reactor):
    """Add config that every test needs."""
    reactor.options['slack'] = {
        'webhook': 'https://slackhook.example.com'
        }
    return reactor

def _get_alert(reactor):
    return BaseAlert.get(reactor, name='Test', query='*', rules=['normal: == 0'])

def test_no_mentions(reactor):
    """Make sure we still produce messages if there is no special mention config."""
    _configure_reactor(reactor)
    handler = SlackHandler(reactor)
    alert = _get_alert(reactor)
    message = handler.get_message('critical', alert, 42, target=0, ntype='graphite')
    assert message == b'[BEACON] CRITICAL <Test> failed. Current value: 42.0'

def test_warning_mentions(reactor):
    """Make sure appropriate mentions are found in message for warnings."""
    _configure_reactor(reactor)
    reactor.options['slack']['warning_mentions'] = ['U04V385L0', 'U04V385L1', '  ', 'U04V385L0']
    handler = SlackHandler(reactor)
    alert = _get_alert(reactor)
    message = handler.get_message('warning', alert, 42, target=0, ntype='graphite')
    assert message.endswith(b'/cc <U04V385L0>, <U04V385L1>')

def test_critical_mentions(reactor):
    """Make sure appropriate mentions are found in message for criticals."""
    _configure_reactor(reactor)
    reactor.options['slack']['critical_mentions'] = ['U04V385L0', 'U04V385L1', '  ', 'U04V385L0', '!channel']
    handler = SlackHandler(reactor)
    alert = _get_alert(reactor)
    message = handler.get_message('critical', alert, 42, target=0, ntype='graphite')
    assert message.endswith(b'/cc <U04V385L0>, <U04V385L1>, <!channel>')

def test_additional_mentions(reactor):
    """Ensure we can add alert-level mentions as well."""
    _configure_reactor(reactor)
    reactor.options['slack']['critical_mentions'] = ['U04V385L0', 'U04V385L1', '  ', 'U04V385L0']
    handler = SlackHandler(reactor)
    alert = _get_alert(reactor)
    alert.override = {'slack': {'additional_mentions': ['U04V385L4', 'U04V385L5']}}
    message = handler.get_message('critical', alert, 42, target=0, ntype='graphite')
    assert message.endswith(b'/cc <U04V385L0>, <U04V385L1>, <U04V385L4>, <U04V385L5>')

def test_override_level_mentions(reactor):
    """Should be able to override {warning,critical}_mentions per alert."""
    _configure_reactor(reactor)
    slack = reactor.options['slack']
    slack['critical_mentions'] = ['default_critical_user']
    slack['warning_mentions'] = ['default_warning_user']
    handler = SlackHandler(reactor)
    alert = _get_alert(reactor)
    alert.override = {
        'slack': {
            'warning_mentions': ['overridden_warning_user'],
            'critical_mentions': ['overridden_critical_user'],
            'additional_mentions': ['additional_user']
        }
    }
    critical_message = handler.get_message('critical', alert, 42, target=0, ntype='graphite')
    assert critical_message.endswith(b'/cc <overridden_critical_user>, <additional_user>')
    warning_message = handler.get_message('warning', alert, 42, target=0, ntype='graphite')
    assert warning_message.endswith(b'/cc <overridden_warning_user>, <additional_user>')

