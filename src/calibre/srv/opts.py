#!/usr/bin/env python2
# vim:fileencoding=utf-8
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__ = 'GPL v3'
__copyright__ = '2015, Kovid Goyal <kovid at kovidgoyal.net>'

import errno, os
from itertools import izip_longest
from collections import namedtuple, OrderedDict
from operator import attrgetter
from functools import partial

from calibre.constants import config_dir
from calibre.utils.lock import ExclusiveFile

Option = namedtuple('Option', 'name default longdoc shortdoc choices')


class Choices(frozenset):

    def __new__(cls, *args):
        self = super(Choices, cls).__new__(cls, args)
        self.default = args[0]
        return self


raw_options = (

    _('Path to the SSL certificate file'),
    'ssl_certfile', None,
    None,

    _('Path to the SSL private key file'),
    'ssl_keyfile', None,
    None,

    _('Time (in seconds) after which an idle connection is closed'),
    'timeout', 120.0,
    None,

    _('Time (in seconds) to wait for a response from the server when making queries'),
    'ajax_timeout',  60.0,
    None,

    _('Total time in seconds to wait for clean shutdown'),
    'shutdown_timeout', 5.0,
    None,

    _('Socket pre-allocation, for example, with systemd socket activation'),
    'allow_socket_preallocation', True,
    None,

    _('Max. size of single HTTP header (in KB)'),
    'max_header_line_size', 8.0,
    None,

    _('Max. allowed size for files uploaded to the server (in MB)'),
    'max_request_body_size', 500.0,
    None,

    _('Minimum size for which responses use data compression (in bytes)'),
    'compress_min_size', 1024,
    None,

    _('Number of worker threads used to process requests'),
    'worker_count', 10,
    None,

    _('Maximum number of worker processes'),
    'max_jobs', 0,
    _('Worker processes are launched as needed and used for large jobs such as preparing'
      ' a book for viewing, adding books, converting, etc. Normally, the max.'
      ' number of such processes is based on the number of CPU cores. You can'
      ' control it by this setting.'),

    _('Maximum time for worker processes'),
    'max_job_time', 60,
    _('Maximum amount of time worker processes are allowed to run (in minutes). Set'
      ' to zero for no limit.'),

    _('The port on which to listen for connections'),
    'port', 8080,
    None,

    _('A prefix to prepend to all URLs'),
    'url_prefix', None,
    _('Useful if you wish to run this server behind a reverse proxy. For example use, /calibre as the URL prefix.'),

    _('Number of books to show in a single page'),
    'num_per_page', 50,
    _('The number of books to show in a single page in the browser.'),

    _('Advertise OPDS feeds via BonJour'),
    'use_bonjour', True,
    _('Advertise the OPDS feeds via the BonJour service, so that OPDS based'
    ' reading apps can detect and connect to the server automatically.'),

    _('Maximum number of books in OPDS feeds'),
    'max_opds_items', 30,
    _('The maximum number of books that the server will return in a single'
    ' OPDS acquisition feed.'),

    _('Maximum number of ungrouped items in OPDS feeds'),
    'max_opds_ungrouped_items', 100,
    _('Group items in categories such as author/tags by first letter when'
    ' there are more than this number of items. Set to zero to disable.'),

    _('The interface on which to listen for connections'),
    'listen_on', '0.0.0.0',
    _('The default is to listen on all available interfaces. You can change this to, for'
    ' example, "127.0.0.1" to only listen for connections from the local machine, or'
    ' to "::" to listen to all incoming IPv6 and IPv4 connections.'),

    _('Fallback to auto-detected interface'),
    'fallback_to_detected_interface', True,
    _('If for some reason the server is unable to bind to the interface specified in'
    ' the listen_on option, then it will try to detect an interface that connects'
    ' to the outside world and bind to that.'),

    _('Zero copy file transfers for increased performance'),
    'use_sendfile', True,
    _('This will use zero-copy in-kernel transfers when sending files over the network,'
    ' increasing performance. However, it can cause corrupted file transfers on some'
    ' broken filesystems. If you experience corrupted file transfers, turn it off.'),

    _('Max. log file size (in MB)'),
    'max_log_size', 20,
    _('The maximum size of log files, generated by the server. When the log becomes larger'
    ' than this size, it is automatically rotated. Set to zero to disable log rotation.'),

    _('Log HTTP 404 (Not Found) requests'),
    'log_not_found', True,
    _('Normally, the server logs all HTTP requests for resources that are not found.'
    ' This can generate a lot of log spam, if your server is targeted by bots.'
    ' Use this option to turn it off.'),

    _('Password based authentication to access the server'),
    'auth', False,
    _('Normally, the server is unrestricted, allowing anyone to access it. You can'
    ' restrict access to predefined users with this option.'),

    _('Allow un-authenticated local connections to make changes'),
    'local_write', False,
    _('Normally, if you do not turn on authentication, the server operates in'
      ' read-only mode, so as to not allow anonymous users to make changes to your'
      ' calibre libraries. This option allows anybody connecting from the same'
      ' computer as the server is running on to make changes. This is useful'
      ' if you want to run the server without authentication but still'
      ' use calibredb to make changes to your calibre libraries. Note that'
      ' turning on this option means any program running on the computer'
      ' can make changes to your calibre libraries.'),

    _('Path to user database'),
    'userdb', None,
    _('Path to a file in which to store the user and password information. Normally a'
    ' file in the calibre configuration directory is used.'),

    _('Choose the type of authentication used'), 'auth_mode', Choices('auto', 'basic', 'digest'),
    _('Set the HTTP authentication mode used by the server. Set to "basic" if you are'
    ' putting this server behind an SSL proxy. Otherwise, leave it as "auto", which'
    ' will use "basic" if SSL is configured otherwise it will use "digest".'),

    _('Ban IP addresses that have repeated login failures'), 'ban_for', 0,
    _('Temporarily bans access for IP addresses that have repeated login failures for the'
      ' specified number of minutes. Useful to prevent attempts at guessing passwords. If'
      ' set to zero, no banning is done.'),

    _('Number of login failures for ban'), 'ban_after', 5,
    _('The number of login failures after which an IP address is banned'),

    _('Ignored user-defined metadata fields'),
    'ignored_fields', None,
    _('Comma separated list of user-defined metadata fields that will not be displayed'
      ' by the Content server in the /opds and /mobile views. For example: {}').format(
      'my_rating,my_tags'),

    _('Restrict displayed user-defined fields'),
    'displayed_fields', None,
    _('Comma separated list of user-defined metadata fields that will be displayed'
      ' by the Content server in the /opds and /mobile views. If you specify this'
      ' option, any fields not in this list will not be displayed. For example: {}').format(
      'my_rating,my_tags'),


)
assert len(raw_options) % 4 == 0

options = []


def grouper(n, iterable, fillvalue=None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return izip_longest(*args, fillvalue=fillvalue)


for shortdoc, name, default, doc in grouper(4, raw_options):
    choices = None
    if isinstance(default, Choices):
        choices = sorted(default)
        default = default.default
    options.append(Option(name, default, doc, shortdoc, choices))
options = OrderedDict([(o.name, o) for o in sorted(options, key=attrgetter('name'))])
del raw_options


class Options(object):

    __slots__ = tuple(name for name in options)

    def __init__(self, **kwargs):
        for opt in options.itervalues():
            setattr(self, opt.name, kwargs.get(opt.name, opt.default))


def opt_to_cli_help(opt):
    ans = opt.shortdoc
    if not ans.endswith('.'):
        ans += '.'
    if opt.longdoc:
        ans += '\n\t' + opt.longdoc
    return ans


def bool_callback(option, opt_str, value, parser, *args, **kwargs):
    setattr(parser.values, option.dest, opt_str.startswith('--enable-'))


def boolean_option(add_option, opt):
    name = opt.name.replace('_', '-')
    help = opt_to_cli_help(opt)
    help += '\n' + (_('By default, this option is enabled.') if opt.default else _('By default, this option is disabled.'))
    add_option('--enable-' + name, '--disable-' + name, action='callback', callback=bool_callback, help=help)


def opts_to_parser(usage):
    from calibre.utils.config import OptionParser
    parser =  OptionParser(usage)
    for opt in options.itervalues():
        add_option = partial(parser.add_option, dest=opt.name, help=opt_to_cli_help(opt), default=opt.default)
        if opt.default is True or opt.default is False:
            boolean_option(add_option, opt)
        elif opt.choices:
            name = '--' + opt.name.replace('_', '-')
            add_option(name, choices=opt.choices)
        else:
            name = '--' + opt.name.replace('_', '-')
            otype = 'string'
            if isinstance(opt.default, (int, long, float)):
                otype = type(opt.default).__name__
            add_option(name, type=otype)

    return parser


DEFAULT_CONFIG = os.path.join(config_dir, 'server-config.txt')


def parse_config_file(path=DEFAULT_CONFIG):
    try:
        with ExclusiveFile(path) as f:
            raw = f.read().decode('utf-8')
    except EnvironmentError as err:
        if err.errno != errno.ENOENT:
            raise
        raw = ''
    ans = {}
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith('#'):
            continue
        key, rest = line.partition(' ')[::2]
        opt = options.get(key)
        if opt is None:
            continue
        val = rest
        if isinstance(opt.default, bool):
            val = val.lower() in ('true', 'yes', 'y')
        elif isinstance(opt.default, (int, long, float)):
            try:
                val = type(opt.default)(rest)
            except Exception:
                raise ValueError('The value for %s: %s is not a valid number' % (key, rest))
        elif opt.choices:
            if rest not in opt.choices:
                raise ValueError('The value for %s: %s is not valid' % (key, rest))
        ans[key] = val
    return Options(**ans)


def write_config_file(opts, path=DEFAULT_CONFIG):
    changed = {name:getattr(opts, name) for name in options if getattr(opts, name) != options[name].default}
    lines = []
    for name in sorted(changed):
        o = options[name]
        lines.append('# ' + o.shortdoc)
        if o.longdoc:
            lines.append('# ' + o.longdoc)
        lines.append('%s %s' % (name, changed[name]))
    raw = '\n'.join(lines).encode('utf-8')
    with ExclusiveFile(path) as f:
        f.truncate()
        f.write(raw)


def server_config(refresh=False):
    if refresh or not hasattr(server_config, 'ans'):
        server_config.ans = parse_config_file()
    return server_config.ans


def change_settings(**kwds):
    new_opts = {}
    opts = server_config()
    for name in options:
        if name in kwds:
            new_opts[name] = kwds[name]
        else:
            new_opts[name] = getattr(opts, name)
    new_opts = server_config.ans = Options(**new_opts)
    write_config_file(new_opts)
