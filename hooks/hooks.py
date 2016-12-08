#!/usr/bin/python

import sys
import charmhelpers.core.hookenv as hookenv
import charmhelpers.core.host as host
import charmhelpers.fetch as fetch

try:
    import jinja2
except ImportError:
    fetch.apt_install('python-jinja2', fatal=True)
    import jinja2


TEMPLATES_DIR = 'templates'


def render_template(template_name, context, template_dir=TEMPLATES_DIR):
    templates = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_dir)
    )
    template = templates.get_template(template_name)
    return template.render(context)


GMOND = "ganglia-monitor"
GMOND_CONF = "/etc/ganglia/gmond.conf"

RESTART_MAP = {
    GMOND_CONF: [GMOND]
}

hooks = hookenv.Hooks()


def get_principle_unit():
    '''Get the unit id from the principle charm'''
    for rid in hookenv.relation_ids('juju-info'):
        for unit in hookenv.related_units(rid):
            return unit
    return None


def get_service_name():
    '''Get service name from principle charm'''
    p_unit = get_principle_unit()
    if p_unit:
        return p_unit.split('/')[0]
    else:
        return None


@host.restart_on_change(RESTART_MAP)
@hooks.hook('node-relation-changed',
            'node-relation-departed',
            'node-relation-broken',
            'config-changed')
def configure_gmond():
    if (not hookenv.relation_ids('juju-info') or
            not hookenv.relation_ids("node")):
        hookenv.log("Required relations not complete, deferring configuration")
        return

    hookenv.log("Configuring new ganglia node")

    # Configure as head unit and send data to masters
    masters = []
    for _rid in hookenv.relation_ids("node"):
        for _master in hookenv.related_units(_rid):
            masters.append(hookenv.relation_get('private-address',
                                                _master, _rid))
    context = {
        "service_name": get_service_name(),
        "masters": masters,
        "unit_name": get_principle_unit()
    }

    with open(GMOND_CONF, "w") as gmond:
        gmond.write(render_template("gmond.conf", context))


@hooks.hook('install')
def install_hook():
    fetch.add_source(hookenv.config('source'),
                     hookenv.config('key'))
    fetch.apt_install("ganglia-monitor")


@hookenv.hook('node-relation-joined')
def node_joined_hook():
    hookenv.relation_set(service=get_service_name())


if __name__ == '__main__':
    try:
        hooks.execute(sys.argv)
    except hookenv.UnregisteredHookError as e:
        hookenv.log('Unknown hook {} - skipping.'.format(e))
