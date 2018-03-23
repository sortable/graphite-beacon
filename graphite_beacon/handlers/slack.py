import json

from tornado import httpclient as hc
from tornado import gen

from graphite_beacon.handlers import LOGGER, AbstractHandler
from graphite_beacon.template import TEMPLATES


def _nub(xs):
    """Return new list containing unique elements of xs, retaining
    order."""
    seen = set()
    result = []
    for x in xs:
        if x not in seen:
            result.append(x)
            seen.add(x)
    return result


def _ensure_prefix(s):
    """Ensure s starts with '@'."""
    if not s.startswith('@'):
        s = '@' + s
    return s


class SlackHandler(AbstractHandler):

    name = 'slack'

    # Default options
    defaults = {
        'webhook': None,
        'channel': None,
        'username': 'graphite-beacon',
        'mentions_critical': [],
        'mentions_warning': [],
        'additional_mentions': []
    }

    emoji = {
        'critical': ':exclamation:',
        'warning': ':warning:',
        'normal': ':white_check_mark:',
    }

    @staticmethod
    def _make_channel_name(channel):
        if channel and not channel.startswith(('#', '@')):
            channel = '#' + channel
        return channel

    def init_handler(self):
        self.webhook = self.options.get('webhook')
        assert self.webhook, 'Slack webhook is not defined.'

        self.channel = self._make_channel_name(self.options.get('channel'))
        self.username = self.options.get('username')
        self.client = hc.AsyncHTTPClient()

    def get_message(
            self, level, alert, value,
            target=None,
            ntype=None,
            rule=None,
            mentions=None):
        msg_type = 'slack' if ntype == 'graphite' else 'short'
        mentions = ', '.join(self.get_mentions(level, alert))
        tmpl = TEMPLATES[ntype][msg_type]
        return tmpl.generate(
            level=level, reactor=self.reactor, alert=alert, mentions=mentions, value=value, target=target).strip()

    def get_mentions(self, level, alert):
        """Return a list of @-mentions to use in the slack message."""
        level_mentions = level + '_mentions'
        mentions = self.options.get(level_mentions, [])
        if alert.override and self.name in alert.override:
            overrides = alert.override[self.name]
            mentions = overrides.get(level_mentions, mentions)
            mentions += overrides.get('additional_mentions', [])
        mentions = [username.strip() for username in mentions]
        mentions = [_ensure_prefix(username) for username in mentions if username]
        mentions = _nub(mentions)
        return mentions

    @gen.coroutine
    def notify(self, level, alert, *args, **kwargs):
        LOGGER.debug("Handler (%s) %s", self.name, level)

        channel = self.channel
        username = self.username
        if alert.override and self.name in alert.override:
            override = alert.override[self.name]
            channel = self._make_channel_name(override.get('channel', channel))
            username = override.get('username', username)

        message = self.get_message(level, alert, *args, **kwargs)
        data = dict()
        data['username'] = username
        data['text'] = message
        data['icon_emoji'] = self.emoji.get(level, ':warning:')
        if channel:
            data['channel'] = channel

        body = json.dumps(data)
        yield self.client.fetch(
            self.webhook,
            method='POST',
            headers={'Content-Type': 'application/json'},
            body=body
        )
