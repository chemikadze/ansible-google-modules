#!/usr/bin/python

ANSIBLE_METADATA = {'status': ['preview'],
                    'supported_by': 'community',
                    'version': '0.1'}

DOCUMENTATION = '''
---
module: gcs_bucket
short_description: Create or delete bucket
description:
   - Create or delete bucket in GCS, configure IAM and ACLs for bucket if required.
options: {}
author:
    - "Nikolay Sokolov"
'''

EXAMPLES = '''
# Create bucket
ansible localhost -m gcs_bucket -a name=chemikadze
'''

import collections
from ansible.module_utils.basic import AnsibleModule


import google.cloud.exceptions
from google.cloud.storage import bucket
from google.cloud import storage


AclDiff = collections.namedtuple("AclDiff", ["changed", "added", "removed"])


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type='str', required=True),
            state=dict(choices=['get', 'present', 'absent'], default='present'),
            location=dict(type='str', default='US-WEST1'),
            project=dict(type='int', default=None),
            storage_class=dict(choices=bucket.Bucket._STORAGE_CLASSES, default='STANDARD'),
            force=dict(type='bool', default=False),
            acl=dict(type='list', default=[]),
            reset_acl=dict(type='bool', default=False),
            default_acl=dict(type='list', default=[]),
            reset_default_acl=dict(type='bool', default=False),
            iam_policy=dict(type='list', default=[]),
            reset_iam_policy=dict(type='bool', default=False),
        ),
        supports_check_mode=True
    )
    _main(module, **module.params)


def _main(module, name, state, location, project, storage_class, force,
          acl, reset_acl,
          default_acl, reset_default_acl,
          iam_policy, reset_iam_policy):
    storage_client = storage.Client()
    changed = False
    bucket_obj = storage_client.lookup_bucket(name)
    iam_policy_diff = acl_diff = default_acl_diff = AclDiff(False, [], [])
    final_policy = {}
    if state == 'present':
        if not bucket_obj:
            changed = True
            bucket_obj = bucket.Bucket(storage_client, name)
            bucket_obj.location = location
            bucket_obj.storage_class = storage_class

            if not module.check_mode:
                bucket_obj.create(project=project)

        # adjust permissions
        acl_diff = _adjust_acl(module, bucket_obj.acl, acl, reset_acl)
        default_acl_diff = _adjust_acl(module, bucket_obj.default_object_acl, default_acl, reset_default_acl)
        final_policy, iam_policy_diff = _adjust_iam(module, bucket_obj, iam_policy, reset_iam_policy)

    elif state == 'absent':
        if bucket_obj:
            changed = True
            bucket_obj.acl.reload()
            bucket_obj.default_object_acl.reload()
            if not module.check_mode:
                bucket_obj.delete(force)
    elif state == 'get':
        pass
    else:
        module.exit_json(failed=True, error="Unexpected state '%s'" % state)

    changed = any([changed, acl_diff.changed, default_acl_diff.changed, iam_policy_diff.changed])
    result = {
        'changed': changed,
        'bucket': _bucket_repr(bucket_obj, final_policy),
        'changes': {
            'acl': acl_diff._asdict(),
            'default_acl': default_acl_diff._asdict(),
            'iam_policy': iam_policy_diff._asdict(),
        },
        'state': state,
    }
    module.exit_json(**result)


def _bucket_repr(bucket, iam_policy):
    if not bucket:
        return None
    return {
        'name': bucket.name,
        'location': bucket.location,
        'storage_class': bucket.storage_class,
        'project_number': bucket.project_number,
        'acl': list(bucket.acl),
        'default_acl': list(bucket.default_object_acl),
        'iam_policy': _iam_to_map(iam_policy),
    }


def _entity_to_tuple(entity):
    return entity['entity'], entity['role']


def _iam_to_map(policy):
    result = {}
    for k, v in policy.iteritems():
        result[k] = list(v)
    return result


def _adjust_acl(module, acl, updates, reset_acl):
    changed = False

    # adjust ACLs
    if reset_acl:
        acl.reset()
    original_acls = set(map(_entity_to_tuple, acl))
    for update in updates:
        if "revoke" in update:
            acl.get_entity(update["entity"]).roles = set()
        else:
            # this method is changing .acl object state
            acl.entity_from_dict(update)

    if not module.check_mode:
        acl.save()
        acl.reload()

    # save info for report
    added_acls = set()
    removed_acls = set()
    updated_acls = set(map(_entity_to_tuple, acl))
    if original_acls != updated_acls:
        added_acls = updated_acls.difference(original_acls)
        removed_acls = original_acls.difference(updated_acls)
        changed = bool(added_acls or removed_acls)

    return AclDiff(changed, list(added_acls), list(removed_acls))


def _adjust_iam(module, bucket_obj, updates, reset_iam_policy):
    policy = bucket_obj.get_iam_policy()
    changed = False

    original_bindings = set((r, m) for r, ms in policy.iteritems() for m in ms)
    if reset_iam_policy:
        policy.clear()
    for update in updates:
        # update
        member = update["member"]
        role = update.get("role")
        if "revoke" in update:
            if role:
                policy[role].discard(member)
            else:
                for k, v in policy:
                    v.discard(member)
        else:
            policy[role].add(member)
    if not module.check_mode:
        policy = bucket_obj.set_iam_policy(policy)

    updated_bindings = set((r, m) for r, ms in policy.iteritems() for m in ms)
    added_bindings = set()
    removed_bindings = set()
    if updated_bindings != original_bindings:
        added_bindings = updated_bindings.difference(original_bindings)
        removed_bindings = original_bindings.difference(updated_bindings)
        changed = bool(added_bindings or removed_bindings)

    return policy, AclDiff(changed, list(added_bindings), list(removed_bindings))


if __name__ == '__main__':
    main()
