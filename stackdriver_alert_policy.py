#!/usr/bin/python

ANSIBLE_METADATA = {'status': ['preview'],
                    'supported_by': 'community',
                    'version': '0.1'}

DOCUMENTATION = '''
---
module: stackdriver_alert_policy
short_description: Manage google stackdriver alert policy
options: {}
author:
    - "Nikolay Sokolov"
'''

EXAMPLES = '''
'''

import re
from collections import namedtuple

from ansible.module_utils.basic import AnsibleModule
from google.cloud import exceptions
from google.cloud import monitoring

PRESENT = "present"
ABSENT = "absent"
STATES = [PRESENT, ABSENT]

COMBINER_TYPES = ['COMBINE_UNSPECIFIED', 'AND', 'OR', 'AND_WITH_MATCHING_RESOURCE']


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type='str', default=None),
            id=dict(type='str', default=None),
            display_name=dict(type='str', default=None),
            state=dict(choices=STATES, default='present'),
            documentation=dict(type='str', default=None),
            user_labels=dict(type='map', default=None),
            conditions=dict(type='list', default=None),
            combiner=dict(choices=COMBINER_TYPES, default=None),
            enabled=dict(type='bool', default=None),
            notification_channels=dict(type='list', default=None),
        ),
        supports_check_mode=True
    )
    _main(module, **module.params)


def _main(module, id, name, state, **kwargs):
    client = monitoring.Client()
    changed = False
    policy = AlertPolicy(client, name)
    if id:
        policy.id = id
    exists = policy.name and policy.exists()
    if exists:
        policy.reload()

    # mutate policy object
    param_names = [
        "display_name",
        "user_labels", "conditions",
        "combiner", "enabled",
        "notification_channels",
    ]
    for param_name in param_names:
        param_value = module.params[param_name]
        if param_value is not None:
            setattr(policy, param_name, param_value)
    documentation = module.params["documentation"]
    if documentation is not None:
        policy.documentation.content = documentation
    if not exists and kwargs["enabled"] is None:
        policy.enabled = True

    # apply changes to policy object
    if module.check_mode:
        pass
    else:
        if exists and state == ABSENT:
            policy.delete()
            changed = True
        elif not exists and state == PRESENT:
            policy.create()
            changed = True
        elif exists and state == PRESENT:
            policy.update()
            changed = True

    result = {
        "changed": changed,
        "alert_policy": _policy_repr(policy),
        "raw_json": policy.raw_json,
        "state": state,
    }
    module.exit_json(**result)


def _policy_repr(policy):
    repr = policy.to_dict()
    repr["id"] = policy.id
    return repr


AlertName = namedtuple("AlertName", "project_id alert_id")


_ALERT_NAME_REGEX = re.compile(r"""projects/([^/]+)/alertPolicies/([^/]+)""")


def _parse_alert_name(name):
    match = _ALERT_NAME_REGEX.match(name)
    if not match:
        raise ValueError("'{}' did not match alert name pattern {}"
                         .format(name, _ALERT_NAME_REGEX))
    return AlertName(match.group(1), match.group(2))


class AlertPolicy(object):

    def __init__(self, client, name):
        """
        :type client: :class:`google.cloud.monitoring.client.Client`
        """
        self.client = client
        self._name = name
        self.display_name = None
        self.documentation = Documentation("")
        self.user_labels = None
        self.conditions = None
        self.combiner = None
        self.enabled = True
        self.notification_channels = None
        self.creation_record = None
        self.mutation_record = None
        self._json = None

    @property
    def name(self):
        return self._name

    @property
    def id(self):
        if self._name:
            return _parse_alert_name(self._name).alert_id
        else:
            return None

    @id.setter
    def id(self, id):
        self._name = "projects/%s/alertPolicies/%s" % (self.client.project, id)

    @property
    def path(self):
        if not self.name:
            raise ValueError('Cannot determine path without alert name')
        return '/' + self.name

    @property
    def raw_json(self):
        return self._json

    def to_dict(self):
        repr = {
            "name": self._name,
            "displayName": self.display_name,
            "documentation": self.documentation.to_dict(),
            "userLabels": self.user_labels,
            "conditions": self.conditions,
            "enabled": self.enabled,
            "notificationChannels": self.notification_channels,
        }
        if self.creation_record:
            repr["creationRecord"] = self.creation_record
        if self.mutation_record:
            repr["mutationRecord"] = self.mutation_record
        if self.combiner:
            repr["combiner"] = self.combiner
        return repr

    def set_properties_from_dict(self, repr):
        self._name = repr["name"]
        self.display_name = repr["displayName"]
        self.documentation.set_properties_from_dict(repr["documentation"])
        self.user_labels = repr.get("userLabels", None)
        self.conditions = repr["conditions"]
        self.enabled = repr["enabled"]
        self.notification_channels = repr.get("notificationChannels", None)
        self.combiner = repr.get("combiner", None)

    def reload(self):
        info = self.client._connection.api_request(
            method='GET', path=self.path)
        self._json = info
        self.set_properties_from_dict(info)

    def create(self):
        path = '/projects/%s/alertPolicies/' % (self.client.project,)
        info = self.client._connection.api_request(
            method='POST', path=path, data=self.to_dict())
        self._json = info
        self.set_properties_from_dict(info)

    def update(self, fields=None):
        update_mask = None
        if fields:
            update_mask = ",".join(fields)
        info = self.client._connection.api_request(
            method='PATCH', path=self.path, data=self.to_dict(), query_params=update_mask)
        self._json = info
        self.set_properties_from_dict(info)

    def delete(self):
        self.client._connection.api_request(
            method='DELETE', path=self.path)

    def exists(self):
        try:
            self.client._connection.api_request(
                method='GET', path=self.path, query_params={'fields': 'name'})
        except exceptions.NotFound:
            return False
        else:
            return True


class Documentation(object):

    def __init__(self, content):
        self.mime_type = "text/markdown"
        self.content = content

    def set_properties_from_dict(self, repr):
        self.mime_type = repr["mimeType"]
        self.content = repr["content"]

    def to_dict(self):
        return {
            "mimeType": self.mime_type,
            "content": self.content,
        }


if __name__ == "__main__":
    main()

# class Condition(object):
#
#     def __init__(self, name, display_name,
#                  condition_threshold=None, condition_absent=None):
#         self.name = name
#         self.display_name = display_name
#         if condition_threshold and condition_absent:
#             raise ValueError("Only threshold or absent should be set")
#         self.condition_threshold = condition_threshold
#         self.condition_absent = condition_absent
#
#     def set_properties_from_dict(self, repr):
#         self.name = repr["name"]
#         self.display_name = repr["displayName"]
#         if "conditionThreshold" in repr:
#             self.condition_threshold = repr["conditionThreshold"]
#         if "conditionAbsent" in repr:
#             self.condition_absent = repr["conditionAbsent"]
#
#     def to_dict(self):
#         repr = {
#             "name": self.name,
#             "displayName": self.display_name,
#         }
#         if self.condition_threshold:
#             repr["conditionThreshold"] = self.condition_threshold
#         if self.condition_absent:
#             repr["conditionAbsent"] = self.condition_absent
#         return repr
#
#
# class MutationRecord(object):
#
#     def __init__(self, mutate_time, mutated_by):
#         self.mutate_time = mutate_time
#         self.mutated_by = mutated_by
#
#     def set_properties_from_dict(self, repr):
#         self.mutate_time = repr["mutateTime"]
#         self.mutated_by = repr["mutatedBy"]
#
#     def to_dict(self):
#         return {
#             "mutateTime": self.mutate_time,
#             "mutatedBy": self.mutated_by,
#         }
